from lambda_func.utils import create_response
from lambda_func import products_db

def handler(event, context):
    try:
        query_params = event.get("queryStringParameters") or {}
        category = query_params.get("category")

        if category:
            products = products_db.get_products_by_category(category)
        else:
            products = products_db.get_all_products()

        return create_response(200, products)
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {"error": "Internal server error"})