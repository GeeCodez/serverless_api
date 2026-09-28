"""Test short-lived downloads and archive restoration for processed images."""

import json
from unittest.mock import patch

from lambda_func.download_image import handler


def make_event():
    """Build the public image-download URL route event."""
    return {"pathParameters": {"id": "product-123", "image_id": "image-123"}}


def test_ready_image_returns_short_lived_presigned_url():
    """Ready products expose only a temporary link to the processed object."""
    product = {"images": {"image-123": {"status": "READY", "processed_key": "products/processed/product-123/image-123.webp"}}}
    with patch("lambda_func.download_image.products_db.get_product", return_value=product), patch(
        "lambda_func.download_image.s3_client.head_object", return_value={"StorageClass": "STANDARD"}
    ), patch(
        "lambda_func.download_image.s3_client.generate_presigned_url", return_value="https://signed.example.test"
    ) as sign:
        response = handler(make_event(), None)

    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["download_url"] == "https://signed.example.test"
    assert body["expires_in"] == 300
    assert sign.call_args.args[0] == "get_object"


def test_archived_image_requests_restore_instead_of_returning_broken_url():
    """Glacier objects start retrieval and report 202 until S3 makes them readable."""
    product = {"images": {"image-123": {"status": "READY", "processed_key": "products/processed/image.webp"}}}
    with patch("lambda_func.download_image.products_db.get_product", return_value=product), patch(
        "lambda_func.download_image.s3_client.head_object", return_value={"StorageClass": "GLACIER"}
    ), patch("lambda_func.download_image.s3_client.restore_object") as restore:
        response = handler(make_event(), None)

    assert response["statusCode"] == 202
    assert json.loads(response["body"])["status"] == "RESTORE_REQUESTED"
    restore.assert_called_once()


def test_unprocessed_image_is_not_downloadable():
    """Pending images stay hidden until the asynchronous processor marks them ready."""
    product = {"images": {"image-123": {"status": "PENDING_UPLOAD"}}}
    with patch("lambda_func.download_image.products_db.get_product", return_value=product), patch(
        "lambda_func.download_image.s3_client.head_object"
    ) as head:
        response = handler(make_event(), None)

    assert response["statusCode"] == 404
    head.assert_not_called()
