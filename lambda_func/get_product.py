from lambda_func.utils import create_response
from lambda_func import products_db

def handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        product_id = path_params.get("id")
        
        if not product_id:
            return create_response(400, {"error": "Product ID is required"})
        
        product = products_db.get_product(product_id)
        if not product:
            return create_response(404, {"error": "Product not found"})
        
        return create_response(200, product)
    except Exception as e:
        return create_response(500, {"error": str(e)})