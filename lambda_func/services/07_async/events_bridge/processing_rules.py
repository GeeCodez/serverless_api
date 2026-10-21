import boto3
import json
from datetime import datetime, timezone
from typing import Dict

# creating rules that route events to the appropriate services.

def create_order_processing_rules(event_bus_name: str):
    """Create EventBridge rules for order processing workflows."""
    eventbridge = boto3.client('events')
    
    # Rule for inventory updates on order placement
    inventory_rule = eventbridge.put_rule(
        Name='order-inventory-update',
        EventPattern=json.dumps({
            'source': ['store.orders'],
            'detail-type': ['Order Placed'],
            'detail': {
                'orderType': ['standard', 'express']
            }
        }),
        State='ENABLED',
        Description='Route order events to inventory service',
        EventBusName=event_bus_name
    )
    
    # Add Lambda target for inventory processing
    eventbridge.put_targets(
        Rule='order-inventory-update',
        EventBusName=event_bus_name,
        Targets=[
            {
                'Id': '1',
                'Arn': 'arn:aws:lambda:region:account:function:inventory-processor',
                'InputTransformer': {
                    'InputPathsMap': {
                        'orderId': '$.detail.orderId',
                        'items': '$.detail.items'
                    },
                    'InputTemplate': '{"orderId": "<orderId>", "items": <items>}'
                }
            }
        ]
    )
    
    # Rule for customer notifications
    notification_rule = eventbridge.put_rule(
        Name='order-customer-notification',
        EventPattern=json.dumps({
            'source': ['store.orders'],
            'detail-type': ['Order Placed', 'Order Shipped', 'Order Delivered'],
            'detail': {
                'customerId': [{'exists': True}]
            }
        }),
        State='ENABLED',
        Description='Route order events to notification service',
        EventBusName=event_bus_name
    )
    
    # Add SNS target for notifications
    eventbridge.put_targets(
        Rule='order-customer-notification',
        EventBusName=event_bus_name,
        Targets=[
            {
                'Id': '1',
                'Arn': 'arn:aws:sns:region:account:customer-notifications',
                'InputTransformer': {
                    'InputPathsMap': {
                        'customerId': '$.detail.customerId',
                        'orderId': '$.detail.orderId',
                        'eventType': '$.detail-type'
                    },
                    'InputTemplate': '{"customerId": "<customerId>", "orderId": "<orderId>", "eventType": "<eventType>"}'
                }
            }
        ]
    )
    
    # Rule for analytics processing
    analytics_rule = eventbridge.put_rule(
        Name='order-analytics-processing',
        EventPattern=json.dumps({
            'source': ['store.orders', 'store.inventory', 'store.customers'],
            'detail-type': ['Order Placed', 'Inventory Updated', 'Customer Registered']
        }),
        State='ENABLED',
        Description='Route events to analytics service',
        EventBusName=event_bus_name
    )
    
    # Add SQS target for analytics processing
    eventbridge.put_targets(
        Rule='order-analytics-processing',
        EventBusName=event_bus_name,
        Targets=[
            {
                'Id': '1',
                'Arn': 'arn:aws:sqs:region:account:analytics-processing-queue.fifo',  # Message groups require a FIFO queue
                'SqsParameters': {
                    'MessageGroupId': 'analytics-events'
                }
            }
        ]
    )
    
    return {
        'inventory_rule_arn': inventory_rule['RuleArn'],
        'notification_rule_arn': notification_rule['RuleArn'],
        'analytics_rule_arn': analytics_rule['RuleArn']
    }

def create_inventory_alert_rules(event_bus_name: str):
    """Create rules for inventory management alerts."""
    eventbridge = boto3.client('events')
    
    # Rule for low stock alerts
    low_stock_rule = eventbridge.put_rule(
        Name='inventory-low-stock-alert',
        EventPattern=json.dumps({
            'source': ['store.inventory'],
            'detail-type': ['Stock Low'],
            'detail': {
                'currentStock': [{'numeric': ['<=', 10]}]
            }
        }),
        State='ENABLED',
        Description='Alert when inventory is low',
        EventBusName=event_bus_name
    )
    
    # Add multiple targets for low stock alerts
    eventbridge.put_targets(
        Rule='inventory-low-stock-alert',
        EventBusName=event_bus_name,
        Targets=[
            {
                'Id': '1',
                'Arn': 'arn:aws:sns:region:account:inventory-alerts',
                'InputTransformer': {
                    'InputPathsMap': {
                        'productName': '$.detail.productName',
                        'currentStock': '$.detail.currentStock',
                        'reorderLevel': '$.detail.reorderLevel'
                    },
                    'InputTemplate': '{"alertType": "low_stock", "productName": "<productName>", "currentStock": <currentStock>, "reorderLevel": <reorderLevel>}'
                }
            },
            {
                'Id': '2',
                'Arn': 'arn:aws:lambda:region:account:function:auto-reorder-processor',
                'InputTransformer': {
                    'InputPathsMap': {
                        'productId': '$.detail.productId',
                        'currentStock': '$.detail.currentStock'
                    },
                    'InputTemplate': '{"productId": "<productId>", "currentStock": <currentStock>, "action": "evaluate_reorder"}'
                }
            }
        ]
    )
    
    return low_stock_rule['RuleArn']