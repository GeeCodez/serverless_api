from lambda_func import products_db
from lambda_func.utils import create_response, create_error_response

def handler(event, context):
    try:
        products_db.get_health_endpoint()
        return create_response(200, {"status": "healthy"})
    except Exception as e:
        return create_error_response(e)