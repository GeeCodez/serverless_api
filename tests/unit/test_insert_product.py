import json
import uuid
import unittest
from unittest.mock import patch

from lambda_func.insert_product import handler


class TestInsertProduct(unittest.TestCase):

    def setUp(self):
        self.valid_product = {
            "title": "Wireless Headphones",
            "price": 199.99,
            "category": "Electronics",
            "description": "High-quality wireless headphones"
        }

        self.user_arn = "arn:aws:iam::123456789012:user/test-user"

        self.valid_event = {
            "body": json.dumps(self.valid_product),
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": self.user_arn
                    }
                }
            }
        }

    @patch("lambda_func.insert_product.products_db.insert_product")
    def test_insert_product_success(self, mock_insert_product):
        mock_insert_product.side_effect = lambda product, user_arn: product

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 201)

        body = json.loads(response["body"])

        self.assertIn("id", body)
        uuid.UUID(body["id"])

        self.assertEqual(body["title"], "Wireless Headphones")
        self.assertEqual(body["category"], "Electronics")

        mock_insert_product.assert_called_once()

        inserted_product, user_arn = mock_insert_product.call_args.args

        self.assertEqual(user_arn, self.user_arn)
        self.assertIn("id", inserted_product)

    @patch("lambda_func.insert_product.products_db.insert_product")
    def test_product_id_is_not_allowed(self, mock_insert_product):
        product = self.valid_product.copy()
        product["id"] = "product-123"

        event = self.valid_event.copy()
        event["body"] = json.dumps(product)

        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])

        self.assertEqual(body["error"], "Product id is not allowed")
        mock_insert_product.assert_not_called()

    @patch("lambda_func.insert_product.products_db.insert_product")
    def test_invalid_json(self, mock_insert_product):
        event = self.valid_event.copy()
        event["body"] = "{invalid json"

        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])

        self.assertIn("Invalid JSON", body["error"])
        mock_insert_product.assert_not_called()

    @patch("lambda_func.insert_product.products_db.insert_product")
    def test_duplicate_product(self, mock_insert_product):
        mock_insert_product.side_effect = ValueError(
            "Product with id product-123 already exists"
        )

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 409)

        body = json.loads(response["body"])

        self.assertIn("already exists", body["error"])

    @patch("lambda_func.insert_product.products_db.insert_product")
    def test_unexpected_database_error(self, mock_insert_product):
        mock_insert_product.side_effect = Exception(
            "Database connection failed"
        )

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 500)

        body = json.loads(response["body"])

        self.assertIn("Internal server error", body["error"])
        self.assertEqual(body["error"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("Database connection failed", response["body"])


if __name__ == "__main__":
    unittest.main()