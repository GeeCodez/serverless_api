import json, uuid, products_db
from utils import create_response
from product_schema import ProductInput
from pydantic import ValidationError

def handler(event, context):
    body = event.get("body") or ""
    try:
        raw_data = json.loads(body)

        if "id" in raw_data:
            return create_response(400, {"error": "Product id is not allowed"})

        product_input = ProductInput(**raw_data)
        validated_data = product_input.model_dump()

        product_id = str(uuid.uuid4())
        validated_data["id"] = product_id

        user_arn = event.get("requestContext", {}).get("identity", {}).get("userArn", "unknown")
        inserted = products_db.insert_product(validated_data, user_arn)

        return create_response(201, inserted)
    except json.JSONDecodeError as e:
        return create_response(400, {"error": f"Invalid JSON: {str(e)}"})
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return create_response(400, {"error": f"Validation failed: {', '.join(errors)}"})
    except ValueError as e:
        return create_response(409, {"error": str(e)})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return create_response(500, {"error": f"Internal server error - {str(e)}"})