from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError
from decimal import Decimal
from lambda_func.utils import ValidationError
import html

VALID_CATEGORIES = ["Electronics", "Audio", "Computers", "Accessories", "Home", "Uncategorized"]

class ProductInput(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="Product title")
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2, description="Product price")
    category: str = Field(min_length=1, max_length=100, description="Product category")
    description: str = Field(default="", max_length=200, description="Product description")
    version: int = Field(default=1, description="Product version")
    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value):
        if value not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of {VALID_CATEGORIES}")
        return value
    
    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError("Price must be a positive number")
        return value
    
def validate_product_data(data: dict) -> dict:
    """Parses and validates incoming dictionary against ProductInput schema."""
    try:
        return ProductInput(**data).model_dump()
    except PydanticValidationError as e:
        errors = {}
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors[field] = err["msg"]
        raise ValidationError("Validation failed for input payload", errors=errors)
    
def sanitize_string(text):
    if not isinstance(text, str):
        return text
    return html.escape(text.strip())