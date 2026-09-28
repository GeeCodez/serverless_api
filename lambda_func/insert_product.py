"""Create catalog products owned by the authenticated Cognito user."""

import json
import logging
import uuid

from lambda_func import products_db
from lambda_func.image_storage import get_authenticated_user_id
from lambda_func.utils import create_response, create_error_response
from lambda_func.product_schema import validate_product_data, sanitize_string

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Validate product input and persist its owner for later image authorization."""
    user_id = get_authenticated_user_id(event)
    if not user_id:
        return create_response(401, {"error": "Authentication is required."})

    body = event.get("body") or ""
    try:
        try:
            raw_data = json.loads(body)
        except json.JSONDecodeError as e:
            return create_response(400, {"error": f"Invalid JSON: {str(e)}"})

        if "id" in raw_data:
            return create_response(400, {"error": "Product id is not allowed"})

        # Validates and cleans input via centralized schema function
        validated_data = validate_product_data(raw_data)

        product_id = str(uuid.uuid4())
        validated_data["id"] = product_id
        validated_data['title'] = sanitize_string(validated_data['title'])
        validated_data['description'] = sanitize_string(validated_data['description'])
        validated_data["owner_sub"] = user_id

        inserted = products_db.insert_product(validated_data, user_id)

        return create_response(201, products_db.to_public_product(inserted))
    except Exception as error:
        LOGGER.exception("Product creation failed")
        return create_error_response(error)