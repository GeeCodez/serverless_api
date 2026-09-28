import io , logging, os, warning
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
from PIL import Image, ImageOps, UnidentifiedImageError
from botocore.config import Config

from lambda_func import products_db
from lambda_func.image_storage import MAX_IMAGE_BYTES

LOGGER = logging.getLogger(__name__)
BUCKET_NAME = os.environ.get("IMAGES_BUCKET_NAME")
MAX_IMAGE_PIXELS = 25_000_000
THUMBNAIL_SIZE = (512, 512)

# Decompression-bomb checks prevent tiny uploads from expanding into unsafe memory use.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
warnings.simplefilter("error", Image.DecompressionBombWarning)
s3_client = boto3.client(
    "s3",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def _mark_failed(product_id, image_id, failure_code):
    """Store a stable, non-sensitive failure code for clients and operators."""
    products_db.update_product_image(
        product_id,
        image_id,
        {"status": "FAILED", "failure_code": failure_code},
    )


def _create_webp_thumbnail(image_bytes):
    """Decode once, normalize camera orientation, resize, and encode a compact WebP."""
    with Image.open(io.BytesIO(image_bytes)) as source:
        source.verify()
    with Image.open(io.BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.convert("RGBA" if "A" in image.getbands() else "RGB").save(
            output,
            format="WEBP",
            quality=82,
            method=6,
        )
        return output.getvalue(), image.width, image.height


def _process_record(record):
    """Process one S3 creation record; deterministic keys make retries idempotent."""
    bucket_name = record["s3"]["bucket"]["name"]
    object_key = unquote_plus(record["s3"]["object"]["key"])
    key_parts = object_key.split("/")
    if len(key_parts) != 4 or key_parts[:2] != ["products", "uploads"]:
        LOGGER.warning("Ignoring S3 event outside the expected image key layout")
        return

    product_id, image_id = key_parts[2:]
    product = products_db.get_product(product_id)
    image_record = (product or {}).get("images", {}).get(image_id)
    if not image_record or image_record.get("original_key") != object_key:
        LOGGER.warning("Ignoring S3 event without a matching reserved product image")
        return
    if image_record.get("status") == "READY":
        return

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        image_bytes = response["Body"].read()
        # The stream is consumed once; all later validation works on the buffered bytes.
        if len(image_bytes) != image_record["size_bytes"] or len(image_bytes) > MAX_IMAGE_BYTES:
            _mark_failed(product_id, image_id, "INVALID_SIZE")
            return
        if response.get("ContentType") != image_record["content_type"]:
            _mark_failed(product_id, image_id, "INVALID_CONTENT_TYPE")
            return
        try:
            thumbnail, width, height = _create_webp_thumbnail(image_bytes)
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError):
            _mark_failed(product_id, image_id, "INVALID_IMAGE")
            return

        processed_key = f"products/processed/{product_id}/{image_id}.webp"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=processed_key,
            Body=thumbnail,
            ContentType="image/webp",
            CacheControl="private, max-age=300",
            Metadata={"product-id": product_id, "image-id": image_id},
        )
        products_db.update_product_image(
            product_id,
            image_id,
            {
                "status": "READY",
                "processed_key": processed_key,
                "width": width,
                "height": height,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        # Raising lets Lambda retry transient S3 or DynamoDB failures and finally use the DLQ.
        LOGGER.exception("Image processing failed for product %s image %s", product_id, image_id)
        raise


def handler(event, context):
    """Process every S3 ObjectCreated record and let infrastructure retry failures."""
    if not BUCKET_NAME:
        raise RuntimeError("IMAGES_BUCKET_NAME is not configured")
    for record in event.get("Records", []):
        if record.get("s3", {}).get("bucket", {}).get("name") != BUCKET_NAME:
            LOGGER.error("Received an S3 event from an unexpected bucket")
            continue
        _process_record(record)
    return {"statusCode": 200, "body": "Image processing completed."}
