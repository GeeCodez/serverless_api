from lambda_func.utils import create_response, create_error_response
from lambda_func import products_db, cache
import json


def handler(event, context):
    """Return paginated products or products filtered by category."""
    try:
        query_params = event.get("queryStringParameters") or {}
        category = query_params.get("category")
        limit = int(query_params.get("limit", 50))
        last_key = query_params.get("last_key")

        if category:
            cache_key = f"products:category:{category}"

            # Check cache first
            cached_products = cache.get(cache_key)

            if cached_products:
                return create_response(200, json.loads(cached_products))

            products = [
                products_db.to_public_product(product)
                for product in products_db.get_products_by_category(category)
            ]

            # Store search results for 30 minutes
            cache.set(
                cache_key,
                json.dumps(products, default=str),
                ttl=1800,
            )

        else:
            products = products_db.get_all_products(limit, last_key)
            products["items"] = [
                products_db.to_public_product(item)
                for item in products["items"]
            ]

        return create_response(200, products)

    except Exception as error:
        return create_error_response(error)