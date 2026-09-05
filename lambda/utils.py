import json

# Dummy in-memory database for testing operations
PRODUCTS_DB = {
    "prod_123": {"id": "prod_123", "name": "Wireless Headphones", "price": 199.99, "category": "Electronics"},
    "prod_456": {"id": "prod_456", "name": "USB-C Cable", "price": 12.99, "category": "Electronics"}
}

def create_response(status_code, body=None):
    """Formats standardized HTTP response for API Gateway Lambda Proxy Integration."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(body) if body is not None else ""
    }