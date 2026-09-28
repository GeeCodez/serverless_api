import os
import json
import boto3
from botocore.config import Config

# Pin SigV4 explicitly so links are signed consistently in every supported Region.
s3_client = boto3.client(
    "s3",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
UPLOAD_URL_TTL_SECONDS = 3600
DOWNLOAD_URL_TTL_SECONDS = 3600
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_bucket_name():
    """Read the deployment-selected bucket name rather than hard-coding an AWS resource."""
    return os.environ.get("IMAGES_BUCKET_NAME")


def get_authenticated_user_id(event):
    """Return the Cognito subject injected by API Gateway, or None for unauthenticated calls."""
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    return claims.get("sub")


def parse_json_body(event):
    """Parse an API Gateway JSON body and reject malformed or non-object payloads."""
    body = event.get("body") or "{}"
    if isinstance(body, dict):
        return body
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object.")
    return parsed


def public_product_owner_matches(product, user_id):
    """Check the immutable owner attribute before issuing an upload capability."""
    return bool(user_id and product and product.get("owner_sub") == user_id)
