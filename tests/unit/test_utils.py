import pytest
from decimal import Decimal

from lambda_func.utils import decimal_serializer, create_response


def test_decimal_serializer_converts_decimal_to_float():
    result = decimal_serializer(Decimal("199.99"))

    assert result == 199.99
    assert isinstance(result, float)


def test_decimal_serializer_raises_type_error_for_unsupported_object():
    with pytest.raises(TypeError):
        decimal_serializer(object())


def test_create_response_returns_correct_status_code():
    response = create_response(200, {"message": "Success"})

    assert response["statusCode"] == 200


def test_create_response_contains_correct_headers():
    response = create_response(200, {"message": "Success"})

    assert response["headers"]["Content-Type"] == "application/json"
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_create_response_serializes_body_to_json():
    response = create_response(200, {"message": "Success"})

    assert response["body"] == '{"message": "Success"}'


def test_create_response_serializes_decimal():
    response = create_response(
        200,
        {"price": Decimal("199.99")}
    )

    assert response["body"] == '{"price": 199.99}'


def test_create_response_with_no_body_returns_empty_string():
    response = create_response(204)

    assert response["body"] == ""