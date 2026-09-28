from lambda_func.utils import create_response, create_error_response
from lambda_func import products_db, cache
import json


def handler(event, context):
    """Return product fields and public image processing status by product ID."""
    try:
        path_params = event.get("pathParameters") or {}
        product_id = path_params.get("id")

        if not product_id:
            return create_response(400, {"error": "Product ID is required"})

        cache_key = f"product:{product_id}"

        cached_product = cache.get(cache_key)

        if cached_product:
            return create_response(200, json.loads(cached_product))

        product = products_db.get_product(product_id)

        if not product:
            return create_response(404, {"error": "Product not found"})

        public_product = products_db.to_public_product(product)

        cache.set(
            cache_key,
            json.dumps(public_product, default=str),
            ttl=3600,
        )

        return create_response(200, public_product)

    except Exception as error:
        return create_error_response(error)