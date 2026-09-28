import json
from unittest.mock import patch

from lambda_func.get_product import handler


class TestGetProducts:

    def test_get_product_success(self):
        product = {
            "id": "product-1",
            "title": "Wireless Headphones",
            "price": 199.99,
            "images": []
        }

        with patch(
            "lambda_func.get_product.products_db.get_product",
            return_value=product
        ) as mock_get:

            response = handler(
                {"pathParameters": {"id": "product-1"}},
                None
            )

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == product
        mock_get.assert_called_once_with("product-1")

    def test_missing_product_id(self):
        response = handler(
            {"pathParameters": {}},
            None
        )

        assert response["statusCode"] == 400
        assert json.loads(response["body"]) == {
            "error": "Product ID is required"
        }

    def test_product_not_found(self):
        with patch(
            "lambda_func.get_product.products_db.get_product",
            return_value=None
        ):

            response = handler(
                {"pathParameters": {"id": "does-not-exist"}},
                None
            )

        assert response["statusCode"] == 404
        assert json.loads(response["body"]) == {
            "error": "Product not found"
        }

    def test_database_error(self):
        with patch(
            "lambda_func.get_product.products_db.get_product",
            side_effect=Exception("Database connection failed")
        ):

            response = handler(
                {"pathParameters": {"id": "product-1"}},
                None
            )

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later."
        }