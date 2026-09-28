import json
import logging
import uuid
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError

from lambda_func import products_db
from lambda_func.image_storage import (
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_BYTES,
    UPLOAD_URL_TTL_SECONDS,
    get_authenticated_user_id,
    get_bucket_name,
    parse_json_body,
    public_product_owner_matches,
    s3_client,
)
from lambda_func.utils import create_response

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Authorize product ownership, reserve metadata, and return a bounded S3 POST."""
    user_id = get_authenticated_user_id(event)
    if not user_id:
        return create_response(401, {"error": "Authentication is required."})

    bucket_name = get_bucket_name()
    if not bucket_name:
        LOGGER.error("IMAGES_BUCKET_NAME is not configured")
        return create_response(503, {"error": "Image upload is temporarily unavailable."})

    product_id = (event.get("pathParameters") or {}).get("id")
    if not product_id:
        return create_response(400, {"error": "Product id is required."})

    try:
        body = parse_json_body(event)
        content_type = body.get("content_type")
        file_size = body.get("file_size")
    except (json.JSONDecodeError, ValueError):
        return create_response(400, {"error": "Request body must be valid JSON."})

    if content_type not in ALLOWED_IMAGE_TYPES:
        return create_response(400, {"error": "Unsupported image content type."})
    if type(file_size) is not int or not 1 <= file_size <= MAX_IMAGE_BYTES:
        return create_response(400, {"error": f"file_size must be between 1 and {MAX_IMAGE_BYTES} bytes."})

    try:
        product = products_db.get_product(product_id)
        if not product:
            return create_response(404, {"error": "Product not found."})
        if not public_product_owner_matches(product, user_id):
            return create_response(403, {"error": "You cannot add images to this product."})

        image_id = str(uuid.uuid4())
        object_key = f"products/uploads/{product_id}/{image_id}"
        # The policy binds both content type and exact byte count before S3 accepts the form.
        upload_form = s3_client.generate_presigned_post(
            Bucket=bucket_name,
            Key=object_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", file_size, file_size],
            ],
            ExpiresIn=UPLOAD_URL_TTL_SECONDS,
        )
        products_db.reserve_product_image(
            product_id,
            image_id,
            {
                "status": "PENDING_UPLOAD",
                "original_key": object_key,
                "content_type": content_type,
                "size_bytes": file_size,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return create_response(
            200,
            {
                "image_id": image_id,
                "upload_method": "POST",
                "upload_url": upload_form["url"],
                "upload_fields": upload_form["fields"],
                "expires_in": UPLOAD_URL_TTL_SECONDS,
                "max_bytes": MAX_IMAGE_BYTES,
            },
        )
    except (ClientError, BotoCoreError):
        LOGGER.exception("Could not create product image upload capability")
        return create_response(503, {"error": "Image upload is temporarily unavailable."})
    except Exception:
        LOGGER.exception("Unexpected image upload URL failure")
        return create_response(500, {"error": "Unable to create image upload."})