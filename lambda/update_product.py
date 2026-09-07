import json
import products_db
from utils import create_response
from product_schema import ProductInput
from pydantic import ValidationError

def handler(event, context):
    try:
        body = event.get("body") or ""
        product_id = (event.get("pathParameters") or {}).get("id")

        if not product_id:
            return create_response(400, {"error": "Product id is required"})

        raw_data = json.loads(body)
        product_input = ProductInput(**raw_data)
        validated_data = product_input.model_dump()

        user_arn = event.get("requestContext", {}).get("identity", {}).get("userArn", "unknown")
        updated = products_db.update_product(product_id, validated_data, user_arn)

        return create_response(200, updated)
    except json.JSONDecodeError as e:
        return create_response(400, {"error": f"Invalid JSON: {str(e)}"})
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return create_response(400, {"error": f"Validation failed: {', '.join(errors)}"})
    except ValueError as e:
        status_code = 404 if "does not exist" in str(e) else 409
        return create_response(status_code, {"error": str(e)})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {"error": f"Internal server error - {str(e)}"})