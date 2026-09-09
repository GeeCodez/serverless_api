import os
import json
import pytest

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["TABLE_NAME"] = "TestProductsTable"

# class APIGatewayEventFactory:
#     """Factory for creating API Gateway HTTP events for Lambda handlers."""
    
#     @staticmethod
#     def create_event(http_method, path_params=None, query_params=None, body=None, user_arn="arn:aws:iam::123456789012:user/TestUser"):
#         return {
#             "httpMethod": http_method,
#             "pathParameters": path_params,
#             "queryStringParameters": query_params,
#             "headers": {"Content-Type": "application/json"},
#             "body": json.dumps(body) if isinstance(body, dict) else body,
#             "requestContext": {
#                 "identity": {
#                     "userArn": user_arn
#                 }
#             }
#         }

# @pytest.fixture
# def event_factory():
#     return APIGatewayEventFactory