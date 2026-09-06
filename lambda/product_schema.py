from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

VALID_CATEGORIES=["Electronics", "Audio", "Computers", "Accessories","Home", "Uncategorized"]

class ProductInput(BaseModel):
    title: str =Field(min_length=1, max_length=100, description="Product title")
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2, description="Product price")
    category: str = Field(min_length=1, max_length=100, description="Product category")
    description: str = Field(default="", max_length=100, description="Product description")
    
    
    @field_validator("category")
    def category_must_be_valid(cls, value):
        if value not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of {VALID_CATEGORIES}")
        return value
    
    @field_validator("price")
    def price_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError("Price must be a positive number")
        return value