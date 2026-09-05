import json
import uuid
from utils import create_response, PRODUCTS_DB

def handler(event, context):
    try:
        if not event.get("body"):
            return create_response(400, {"error": "Missing request body"})

        body = json.loads(event["body"])
        if "name" not in body or "price" not in body:
            return create_response(400, {"error": "Fields 'name' and 'price' are required"})

        new_id = f"prod_{uuid.uuid4().hex[:6]}"
        new_product = {
            "id": new_id,
            "name": body["name"],
            "price": body["price"],
            "category": body.get("category", "Uncategorized")
        }

        PRODUCTS_DB[new_id] = new_product
        return create_response(201, new_product)
    
    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON format"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {"error": "Internal server error"})