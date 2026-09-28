"""Set harmless local defaults before importing Lambda modules in unit tests."""

import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "TestProductsTable")
os.environ.setdefault("IMAGES_BUCKET_NAME", "test-product-images")
os.environ.setdefault("ALLOWED_ORIGIN", "https://store.example.test")
