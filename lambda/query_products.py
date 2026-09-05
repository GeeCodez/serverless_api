from utils import create_response, PRODUCTS_DB

def handler(event, context):
    try:
        query_params = event.get("queryStringParameters") or {}
        category = query_params.get("category")
        
        products = list(PRODUCTS_DB.values())
        if category:
            products = [product for product in products if product.get("category") == category]
            
        return create_response(200,products)
    
    except Exception as e:
        print(f"Error occurred: {e}")
        return create_response(500, {"error": "Internal server error"})