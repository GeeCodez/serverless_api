"""Test authenticated, size-bounded presigned product image uploads."""

import json
from unittest.mock import patch

from lambda_func.upload_image import handler


def make_event(body=None, user_id="user-123"):
    """Build an API Gateway event with a Cognito principal and product route parameter."""
    return {
        "pathParameters": {"id": "product-123"},
        "requestContext": {"authorizer": {"claims": {"sub": user_id}}},
        "body": json.dumps(body or {"content_type": "image/jpeg", "file_size": 1024}),
    }


def test_owner_receives_constrained_upload_form():
    """The owner gets a short-lived form and the product stores pending image state."""
    with (
        patch("lambda_func.upload_image.products_db.get_product", return_value={"owner_sub": "user-123"}),
        patch("lambda_func.upload_image.products_db.reserve_product_image") as reserve,
        patch(
            "lambda_func.upload_image.s3_client.generate_presigned_post",
            return_value={"url": "https://s3.example.test", "fields": {"key": "private-key"}},
        ) as sign,
    ):
        response = handler(make_event(), None)

    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["upload_method"] == "POST"
    assert body["expires_in"] == 300
    sign.assert_called_once()
    assert ["content-length-range", 1024, 1024] in sign.call_args.kwargs["Conditions"]
    reserve.assert_called_once()
    assert reserve.call_args.args[0] == "product-123"


def test_non_owner_cannot_request_upload():
    """A valid login alone cannot authorize changes to another user's product."""
    with patch(
        "lambda_func.upload_image.products_db.get_product",
        return_value={"owner_sub": "different-user"},
    ), patch("lambda_func.upload_image.s3_client.generate_presigned_post") as sign:
        response = handler(make_event(), None)

    assert response["statusCode"] == 403
    sign.assert_not_called()


def test_upload_rejects_oversize_payload_before_signing():
    """The API rejects oversized upload requests before creating any S3 capability."""
    with patch("lambda_func.upload_image.s3_client.generate_presigned_post") as sign:
        response = handler(make_event({"content_type": "image/jpeg", "file_size": 99_000_000}), None)

    assert response["statusCode"] == 400
    sign.assert_not_called()


def test_upload_requires_cognito_identity():
    """Direct invocations without the API's Cognito subject cannot mint upload links."""
    response = handler(make_event(user_id=None), None)

    assert response["statusCode"] == 401
