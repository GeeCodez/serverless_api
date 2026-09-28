import logging

from botocore.exceptions import BotoCoreError, ClientError

from lambda_func import products_db
from lambda_func.image_storage import (
    DOWNLOAD_URL_TTL_SECONDS,
    get_bucket_name,
    s3_client,
)
from lambda_func.utils import create_response

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Return a signed GET URL only after the product image is marked ready."""
    product_id = (event.get("pathParameters") or {}).get("id")
    image_id = (event.get("pathParameters") or {}).get("image_id")
    if not product_id or not image_id:
        return create_response(400, {"error": "Product id and image id are required."})

    bucket_name = get_bucket_name()
    if not bucket_name:
        LOGGER.error("IMAGES_BUCKET_NAME is not configured")
        return create_response(503, {"error": "Image downloads are temporarily unavailable."})

    try:
        product = products_db.get_product(product_id)
        image = (product or {}).get("images", {}).get(image_id)
        if not image or image.get("status") != "READY":
            return create_response(404, {"error": "Processed image not found."})

        object_key = image["processed_key"]
        object_head = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        if object_head.get("StorageClass") in {"GLACIER", "DEEP_ARCHIVE"}:
            restore_status = object_head.get("Restore", "")
            if 'ongoing-request="true"' in restore_status:
                return create_response(202, {"status": "RESTORE_IN_PROGRESS"})
            if 'ongoing-request="false"' not in restore_status:
                try:
                    s3_client.restore_object(
                        Bucket=bucket_name,
                        Key=object_key,
                        RestoreRequest={
                            "Days": 1,
                            "GlacierJobParameters": {"Tier": "Standard"},
                        },
                    )
                except ClientError as error:
                    if error.response["Error"]["Code"] != "RestoreAlreadyInProgress":
                        raise
                return create_response(202, {"status": "RESTORE_REQUESTED"})

        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "ResponseContentType": "image/webp",
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=DOWNLOAD_URL_TTL_SECONDS,
        )
        return create_response(
            200,
            {"download_url": download_url, "expires_in": DOWNLOAD_URL_TTL_SECONDS},
        )
    except (ClientError, BotoCoreError):
        LOGGER.exception("Could not create product image download capability")
        return create_response(503, {"error": "Image downloads are temporarily unavailable."})
    except Exception:
        LOGGER.exception("Unexpected image download URL failure")
        return create_response(500, {"error": "Unable to create image download."})
