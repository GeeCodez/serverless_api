import os
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def products_db():
    with mock_aws():
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["TABLE_NAME"] = "TestProductsTable"

        dynamodb = boto3.resource(
            "dynamodb",
            region_name="us-east-1"
        )

        table = dynamodb.create_table(
            TableName="TestProductsTable",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "category-index",
                    "KeySchema": [
                        {"AttributeName": "category", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        import lambda_func.products_db as module
        module.table = table

        yield module


@pytest.fixture
def product():
    return {
        "id": "product-1",
        "title": "Wireless Headphones",
        "category": "Electronics",
        "price": Decimal("199.99"),
        "description": "High-quality headphones",
        "version": 1
    }


class TestProductsDB:

    def test_insert_product(self, products_db, product):
        result = products_db.insert_product(
            product,
            user_arn="test-user"
        )

        assert result["id"] == "product-1"
        assert result["created_by"] == "test-user"
        assert result["updated_by"] == "test-user"
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_product(self, products_db, product):
        products_db.table.put_item(Item=product)

        result = products_db.get_product("product-1")

        assert result["id"] == "product-1"
        assert result["title"] == "Wireless Headphones"

    def test_get_missing_product(self, products_db):
        result = products_db.get_product("does-not-exist")

        assert result is None

    def test_get_all_products(self, products_db, product):
        products_db.table.put_item(Item=product)

        second_product = product.copy()
        second_product["id"] = "product-2"
        products_db.table.put_item(Item=second_product)

        result = products_db.get_all_products()

        assert len(result) == 2

    def test_get_products_by_category(self, products_db, product):
        products_db.table.put_item(Item=product)

        result = products_db.get_products_by_category("Electronics")

        assert len(result) == 1
        assert result[0]["category"] == "Electronics"

    def test_duplicate_product_is_rejected(
        self,
        products_db,
        product
    ):
        products_db.insert_product(product)

        with pytest.raises(ValueError, match="already exists"):
            products_db.insert_product(product)

    def test_update_product(self, products_db, product):
        products_db.table.put_item(Item=product)

        fields = {
            "category": "Electronics",
            "title": "Updated Headphones",
            "description": "Updated description",
            "price": Decimal("249.99"),
            "version": 1
        }

        result = products_db.update_product(
            "product-1",
            fields,
            "test-user"
        )

        assert result["title"] == "Updated Headphones"
        assert result["price"] == Decimal("249.99")
        assert result["version"] == 2
        assert result["updated_by"] == "test-user"

    def test_update_increments_version(
        self,
        products_db,
        product
    ):
        products_db.table.put_item(Item=product)

        fields = {
            "category": "Electronics",
            "title": product["title"],
            "description": product["description"],
            "price": product["price"],
            "version": 1
        }

        result = products_db.update_product(
            "product-1",
            fields
        )

        assert result["version"] == 2

    def test_update_missing_product_is_rejected(
        self,
        products_db,
        product
    ):
        with pytest.raises(
            ValueError,
            match="does not exist or was already modified"
        ):
            products_db.update_product(
                "does-not-exist",
                product
            )

    def test_stale_version_is_rejected(
        self,
        products_db,
        product
    ):
        products_db.table.put_item(Item=product)

        fields = {
            "category": "Electronics",
            "title": "Updated",
            "description": "Updated",
            "price": Decimal("299.99"),
            "version": 99
        }

        with pytest.raises(
            ValueError,
            match="does not exist or was already modified"
        ):
            products_db.update_product(
                "product-1",
                fields
            )