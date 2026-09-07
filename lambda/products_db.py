import os
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

TABLE_NAME=os.environ.get('TABLE_NAME', 'Products')
table=boto3.resource('dynamodb').Table(TABLE_NAME)

def get_product(product_id):
    response=table.get_item(Key={'id': product_id})
    return response.get('Item')

def get_all_products():
    response=table.scan()
    return response.get('Items', [])

def get_products_by_category(category):
    response=table.query(
        IndexName='category-index',
        KeyConditionExpression=Key('category').eq(category)
    )
    return response.get('Items', [])

def insert_product(item, user_arn="unknown"):
    timestamp = datetime.now().isoformat() + "Z"
    item["created_at"] = timestamp
    item["created_by"] = user_arn
    item["updated_at"] = timestamp
    item["updated_by"] = user_arn

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(id)"
        )
        return item
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(f"Product with id {item['id']} already exists")
        raise

def update_product(product_id, fields, user_arn="unknown"):
    timestamp = datetime.now().isoformat() + "Z"
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
            raise ValueError(f"Product with id {product_id} does not exist or was already modified by another process. Refresh and try again.")
        raise