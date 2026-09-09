from decimal import Decimal

import pytest
from pydantic import ValidationError

from lambda_func.product_schema import ProductInput


def valid_product():
    return {
        "title": "Wireless Headphones",
        "price": Decimal("199.99"),
        "category": "Electronics",
        "description": "High-quality wireless headphones",
    }


def test_valid_product_is_accepted():
    product = ProductInput(**valid_product())

    assert product.title == "Wireless Headphones"
    assert product.price == Decimal("199.99")
    assert product.category == "Electronics"


def test_missing_required_field_is_rejected():
    data = valid_product()
    del data["title"]

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_empty_title_is_rejected():
    data = valid_product()
    data["title"] = ""

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_zero_price_is_rejected():
    data = valid_product()
    data["price"] = 0

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_negative_price_is_rejected():
    data = valid_product()
    data["price"] = -10

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_invalid_category_is_rejected():
    data = valid_product()
    data["category"] = "Clothing"

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_description_defaults_to_empty_string():
    data = valid_product()
    del data["description"]

    product = ProductInput(**data)

    assert product.description == ""


def test_version_defaults_to_one():
    product = ProductInput(**valid_product())

    assert product.version == 1


def test_description_over_200_characters_is_rejected():
    data = valid_product()
    data["description"] = "a" * 201

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_category_over_100_characters_is_rejected():
    data = valid_product()
    data["category"] = "a" * 101

    with pytest.raises(ValidationError):
        ProductInput(**data)


def test_price_with_more_than_two_decimal_places_is_rejected():
    data = valid_product()
    data["price"] = Decimal("199.999")

    with pytest.raises(ValidationError):
        ProductInput(**data)