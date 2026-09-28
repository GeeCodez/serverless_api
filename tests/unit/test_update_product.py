import json
import unittest
from unittest.mock import patch
from decimal import Decimal
from lambda_func.update_product import handler


class TestUpdateProduct(unittest.TestCase):

    def setUp(self):
        self.product_id = "product-123"

        self.update_data = {
            "title": "Updated Wireless Headphones",
            "price": 249.99,
            "category": "Electronics",
            "description": "Updated description",
            "version": 1
        }

        self.user_arn = "arn:aws:iam::123456789012:user/test-user"
        
        self.valid_event = {
            "pathParameters": {
                "id": self.product_id
            },
            "body": json.dumps(self.update_data),
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": self.user_arn
                    }
                }
            }
        }

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product")
    def test_update_product_success(self, mock_get_product, mock_update_product):
        mock_get_product.return_value = {"owner_sub": self.user_arn}
        mock_update_product.return_value = {
            "id": self.product_id,
            "title": "Updated Wireless Headphones",
            "price": 249.99,
            "category": "Electronics",
            "description": "Updated description",
            "version": 2
        }

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(body["id"], self.product_id)
        self.assertEqual(body["version"], 2)
        
        expected_data = self.update_data.copy()
        expected_data["price"] = Decimal("249.99")

        mock_update_product.assert_called_once_with(
            self.product_id,
            expected_data,
            self.user_arn
        )

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product")
    def test_product_id_is_required(self, mock_get_product, mock_update_product):
        event = self.valid_event.copy()
        event["pathParameters"] = None

        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])

        self.assertEqual(body["error"], "Product id is required")
        mock_update_product.assert_not_called()

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product")
    def test_invalid_json(self, mock_get_product, mock_update_product):
        mock_get_product.return_value = {"owner_sub": self.user_arn}
        event = self.valid_event.copy()
        event["body"] = "{invalid json"

        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])

        self.assertIn("Invalid JSON", body["error"])
        mock_update_product.assert_not_called()

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product", return_value=None)
    def test_product_not_found(self, mock_get_product, mock_update_product):
        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 404)

        body = json.loads(response["body"])

        self.assertEqual(body["error"], "Product not found.")
        mock_update_product.assert_not_called()

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product")
    def test_update_conflict(self, mock_get_product, mock_update_product):
        mock_get_product.return_value = {"owner_sub": self.user_arn}
        mock_update_product.side_effect = ValueError(
            "Product was already modified by another process. Refresh and try again."
        )

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 409)

        body = json.loads(response["body"])

        self.assertIn("already modified", body["error"])

    @patch("lambda_func.update_product.products_db.update_product")
    @patch("lambda_func.update_product.products_db.get_product")
    def test_unexpected_database_error(self, mock_get_product, mock_update_product):
        mock_get_product.return_value = {"owner_sub": self.user_arn}
        mock_update_product.side_effect = Exception(
            "Database connection failed"
        )

        response = handler(self.valid_event, None)

        self.assertEqual(response["statusCode"], 500)

        body = json.loads(response["body"])

        self.assertEqual(body["error"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("Database connection failed", response["body"])


if __name__ == "__main__":
    unittest.main()