import json
import logging

from lambda_func import products_db, cache
from lambda_func.image_storage import get_authenticated_user_id
from lambda_func.utils import create_response, create_error_response
from lambda_func.product_schema import validate_product_data

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Enforce immutable product ownership before validating and applying an update."""
    user_id = get_authenticated_user_id(event)
    if not user_id:
        return create_response(401, {"error": "Authentication is required."})

    try:
        body = event.get("body") or ""
        product_id = (event.get("pathParameters") or {}).get("id")

        if not product_id:
            return create_response(400, {"error": "Product id is required"})

        product = products_db.get_product(product_id)
        if not product:
            return create_response(404, {"error": "Product not found."})
        if product.get("owner_sub") != user_id:
            return create_response(403, {"error": "You cannot update this product."})

        try:
            raw_data = json.loads(body)
        except json.JSONDecodeError as e:
            return create_response(400, {"error": f"Invalid JSON: {str(e)}"})

        # Validates payload and raises custom ValidationError if schema fails
        validated_data = validate_product_data(raw_data)

        updated = products_db.update_product(product_id, validated_data, user_id)
        # invalidate cache after updating a product
        cache.delete(f"product:{product_id}")
        return create_response(200, products_db.to_public_product(updated))
    except Exception as error:
        LOGGER.exception("Product update failed")
        return create_error_response(error)