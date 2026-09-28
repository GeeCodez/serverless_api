"""DynamoDB access layer for products and their associated image metadata."""

import os, time, random, boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from lambda_func.utils import ValidationError, TransientError

TABLE_NAME = os.environ.get('TABLE_NAME')

if not TABLE_NAME:
    raise ValueError("TABLE_NAME environment variable is required")

table = boto3.resource('dynamodb').Table(TABLE_NAME)

def retry_on_transient_error(max_attempts=3, base_delay=0.5):
    """Decorator to retry database operations on transient AWS failures with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    # List of AWS transient/throttle error codes eligible for retry
                    transient_codes = [
                        "ProvisionedThroughputExceededException",
                        "RequestLimitExceeded",
                        "InternalServerError",
                        "ServiceUnavailable"
                    ]
                    if error_code in transient_codes:
                        attempts += 1
                        if attempts == max_attempts:
                            raise TransientError(f"Database operation failed after {max_attempts} retries due to temporary service issues.")
                        # Exponential backoff with jitter
                        sleep_time = (base_delay * (2 ** (attempts - 1))) + random.uniform(0, 0.1)
                        time.sleep(sleep_time)
                    else:
                        raise
        return wrapper
    return decorator

@retry_on_transient_error()
def get_product(product_id):
    response = table.get_item(Key={'id': product_id})
    return response.get('Item')

@retry_on_transient_error()
def get_health_endpoint():
    return table.get_item(Key={'id': 'health_check_endpoint'})

@retry_on_transient_error()
def get_all_products(limit=100, last_evaluated_key=None):
    kwargs = {'Limit': limit}
    if last_evaluated_key:
        kwargs['ExclusiveStartKey'] = last_evaluated_key
    
    response = table.scan(**kwargs)
    return {
        'items': response.get('Items', []),
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }

@retry_on_transient_error()
def get_products_by_category(category):
    response = table.query(
        IndexName='category-index',
        KeyConditionExpression=Key('category').eq(category)
    )
    return response.get('Items', [])

@retry_on_transient_error()
def insert_product(item, user_arn="unknown"):
    """Insert one product, recording its immutable owner and an empty image map."""
    timestamp = datetime.now(timezone.utc).isoformat()
    item["created_at"] = timestamp
    item["created_by"] = user_arn
    item["owner_sub"] = user_arn
    item["updated_at"] = timestamp
    item["updated_by"] = user_arn
    item["images"] = {}

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(id)"
        )
        return item
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValidationError(f"Product with id {item.get('id')} already exists.")
        raise

@retry_on_transient_error()
def update_product(product_id, fields, user_arn="unknown"):
    """Update editable product fields using optimistic version checking."""
    timestamp = datetime.now(timezone.utc).isoformat()
    expected_version = fields.get("version")
    new_version = expected_version + 1

    update_expression = """SET category = :category,
        title = :title,
        description = :description,
        price = :price,
        updated_at = :updated_at,
        updated_by = :updated_by,
        version = :new_version"""

    expression_attribute_values = {
        ":category": fields["category"],
        ":title": fields["title"],
        ":description": fields["description"],
        ":price": fields["price"],
        ":updated_at": timestamp,
        ":new_version": new_version,
        ":updated_by": user_arn,
        ":expected_version": expected_version
    }

    try:
        response = table.update_item(
            Key={"id": product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(id) AND version = :expected_version",
            ReturnValues="ALL_NEW"
        )
        return response["Attributes"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValidationError(f"Product with id {product_id} does not exist or was modified concurrently. Refresh and try again.")
        raise

@retry_on_transient_error()
def reserve_product_image(product_id, image_id, image_metadata):
    """Create a pending image record once, initializing the nested map for older products."""
    table.update_item(
        Key={"id": product_id},
        UpdateExpression="SET #images = if_not_exists(#images, :empty_map)",
        ConditionExpression="attribute_exists(#id)",
        ExpressionAttributeNames={"#id": "id", "#images": "images"},
        ExpressionAttributeValues={":empty_map": {}},
    )
    try:
        table.update_item(
            Key={"id": product_id},
            UpdateExpression="SET #images.#image_id = :image",
            ConditionExpression="attribute_not_exists(#images.#image_id)",
            ExpressionAttributeNames={"#images": "images", "#image_id": image_id},
            ExpressionAttributeValues={":image": image_metadata},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValidationError("An image with this identifier already exists.") from error
        raise

@retry_on_transient_error()
def update_product_image(product_id, image_id, updates):
    """Apply a small set of status fields to an existing product image record."""
    expression_names = {
        "#images": "images",
        "#image_id": image_id,
    }
    expression_values = {}
    assignments = []
    for index, (field_name, value) in enumerate(updates.items()):
        name_token = f"#field_{index}"
        value_token = f":value_{index}"
        expression_names[name_token] = field_name
        expression_values[value_token] = value
        assignments.append(f"#images.#image_id.{name_token} = {value_token}")

    table.update_item(
        Key={"id": product_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ConditionExpression="attribute_exists(#images.#image_id)",
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )

def to_public_product(product):
    """Remove ownership and S3 internals before returning product data to API clients."""
    public_product = {
        key: value
        for key, value in product.items()
        if key not in {"owner_sub", "created_by", "updated_by", "images"}
    }
    public_product["images"] = [
        {
            "image_id": image_id,
            "status": image.get("status"),
            "content_type": image.get("content_type"),
            "created_at": image.get("created_at"),
            "processed_at": image.get("processed_at"),
        }
        for image_id, image in product.get("images", {}).items()
    ]
    return public_product