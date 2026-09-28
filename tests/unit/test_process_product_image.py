"""Test S3 event processing, deterministic derivatives, and image safety checks."""

import io
from unittest.mock import patch

from PIL import Image

from lambda_func import process_product_image


def make_jpeg():
    """Create a small valid in-memory JPEG fixture without adding binary test assets."""
    image_buffer = io.BytesIO()
    Image.new("RGB", (1024, 768), color="navy").save(image_buffer, format="JPEG")
    return image_buffer.getvalue()


def make_event():
    """Build the S3 ObjectCreated envelope for one reserved original image."""
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-product-images"},
                    "object": {"key": "products/uploads/product-123/image-123"},
                }
            }
        ]
    }


def test_upload_event_creates_webp_and_marks_product_ready(monkeypatch):
    """The processor reads once, writes a deterministic derivative, and updates DynamoDB."""
    raw_image = make_jpeg()
    monkeypatch.setattr(process_product_image, "BUCKET_NAME", "test-product-images")
    product = {
        "images": {
            "image-123": {
                "status": "PENDING_UPLOAD",
                "original_key": "products/uploads/product-123/image-123",
                "content_type": "image/jpeg",
                "size_bytes": len(raw_image),
            }
        }
    }
    with patch("lambda_func.process_product_image.products_db.get_product", return_value=product), patch(
        "lambda_func.process_product_image.s3_client.get_object",
        return_value={"Body": io.BytesIO(raw_image), "ContentType": "image/jpeg"},
    ), patch("lambda_func.process_product_image.s3_client.put_object") as put_object, patch(
        "lambda_func.process_product_image.products_db.update_product_image"
    ) as update_image:
        result = process_product_image.handler(make_event(), None)

    assert result["statusCode"] == 200
    assert put_object.call_args.kwargs["Key"] == "products/processed/product-123/image-123.webp"
    assert put_object.call_args.kwargs["ContentType"] == "image/webp"
    with Image.open(io.BytesIO(put_object.call_args.kwargs["Body"])) as derivative:
        assert derivative.format == "WEBP"
        assert derivative.size == (512, 384)
    assert update_image.call_args.args[2]["status"] == "READY"


def test_duplicate_ready_event_is_idempotent(monkeypatch):
    """An S3 retry after a completed update does not re-read or rewrite the derivative."""
    monkeypatch.setattr(process_product_image, "BUCKET_NAME", "test-product-images")
    product = {
        "images": {
            "image-123": {
                "status": "READY",
                "original_key": "products/uploads/product-123/image-123",
            }
        }
    }
    with patch("lambda_func.process_product_image.products_db.get_product", return_value=product), patch(
        "lambda_func.process_product_image.s3_client.get_object"
    ) as get_object:
        process_product_image.handler(make_event(), None)

    get_object.assert_not_called()
