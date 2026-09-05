import json
from utils import create_response, PRODUCTS_DB

def handler(event, context):
    try:
        path_params=event.get("pathParameters", {})
        product_id = path_params.get("id")
        if not product_id or product_id not in PRODUCTS_DB:
            return create_response(404, {"error": "Product not found"})
        
        if not event.get("body"):
            return create_response(400, {"error": "Missing request body"})
        body = json.loads(event["body"])
        product = PRODUCTS_DB[product_id]
        
        product["name"] = body.get("name", product["name"])
        product["price"] = body.get("price", product["price"])
        product["category"] = body.get("category", product["category"])

        return create_response(200, product)
    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON format"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {"error": "Internal server error"})