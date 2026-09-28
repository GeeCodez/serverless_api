"""Handle browser CORS preflight requests for API Gateway routes."""

from lambda_func.utils import create_response

def handler(event, context):
    """Return an empty preflight response using the configured single-origin policy."""
    return create_response(200)