import json
from unittest.mock import patch

from lambda_func.query_products import handler


class TestQueryProducts:

    def test_get_all_products(self):
        products = [
            {"id": "product-1", "title": "Headphones"},
            {"id": "product-2", "title": "Laptop"}
        ]

        with patch(
            "lambda_func.query_products.products_db.get_all_products",
            return_value=products
        ) as mock_get_all:

            response = handler(
                {"queryStringParameters": None},
                None
            )

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == products
        mock_get_all.assert_called_once_with()

    def test_get_products_by_category(self):
        products = [
            {
                "id": "product-1",
                "title": "Headphones",
                "category": "Electronics"
            }
        ]

        with patch(
            "lambda_func.query_products.products_db.get_products_by_category",
            return_value=products
        ) as mock_query:

            response = handler(
                {
                    "queryStringParameters": {
                        "category": "Electronics"
                    }
                },
                None
            )

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == products
        mock_query.assert_called_once_with("Electronics")

    def test_empty_query_parameters(self):
        products = [
            {"id": "product-1", "title": "Headphones"}
        ]

        with patch(
            "lambda_func.query_products.products_db.get_all_products",
            return_value=products
        ):

            response = handler(
                {},
                None
            )

        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == products

    def test_database_error(self):
        with patch(
            "lambda_func.query_products.products_db.get_all_products",
            side_effect=Exception("Database unavailable")
        ):

            response = handler({}, None)

        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {
            "error": "Internal server error"
        }