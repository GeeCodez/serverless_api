import boto3, json 
from datetime import datetime,timedelta
from typing import str, Dict

def create_advanced_event_patterns():
    """Create advanced event patterns for complex routing scenarios."""
    
    # Pattern for premium customer orders
    premium_customer_pattern = {
        'source': ['store.orders'],
        'detail-type': ['Order Placed'],
        'detail': {
            'customerTier': ['premium', 'vip'],
            'orderAmount': [{'numeric': ['>=', 500]}]
        }
    }
    
    # Pattern for express shipping orders
    express_shipping_pattern = {
        'source': ['store.orders'],
        'detail-type': ['Order Placed'],
        'detail': {
            'orderType': ['express', 'same_day'],
            'shippingAddress': {
                'state': ['WA', 'OR', 'CA']  # West Coast only
            }
        }
    }
    
    # Pattern for inventory critical alerts
    critical_inventory_pattern = {
        'source': ['store.inventory'],
        'detail-type': ['Stock Low', 'Out of Stock'],
        'detail': {
            'category': ['Electronics', 'Best Sellers'],
            'currentStock': [{'numeric': ['<=', 5]}]
        }
    }
    
    # Pattern for customer lifecycle events
    customer_lifecycle_pattern = {
        'source': ['store.customers'],
        'detail-type': ['Customer Registered', 'Customer Updated', 'Customer Churned'],
        'detail': {
            'customerTier': [{'exists': True}],
            'timestamp': [{'exists': True}]
        }
    }
    
    return {
        'premium_customer': premium_customer_pattern,
        'express_shipping': express_shipping_pattern,
        'critical_inventory': critical_inventory_pattern,
        'customer_lifecycle': customer_lifecycle_pattern
    }

def create_content_based_routing_rule(pattern_name: str, event_pattern: Dict, target_arn: str, event_bus_name: str):
    """Create EventBridge rule with content-based routing."""
    eventbridge = boto3.client('events')
    
    rule = eventbridge.put_rule(
        Name=f'content-routing-{pattern_name}',
        EventPattern=json.dumps(event_pattern),
        State='ENABLED',
        Description=f'Content-based routing for {pattern_name}',
        EventBusName=event_bus_name
    )
    
    # Add target with input transformation
    eventbridge.put_targets(
        Rule=f'content-routing-{pattern_name}',
        EventBusName=event_bus_name,
        Targets=[
            {
                'Id': '1',
                'Arn': target_arn,
                'InputTransformer': {
                    'InputPathsMap': {
                        'source': '$.source',
                        'detailType': '$.detail-type',
                        'timestamp': '$.time',
                        'eventDetail': '$.detail'
                    },
                    'InputTemplate': json.dumps({
                        'routingPattern': pattern_name,
                        'eventSource': '<source>',
                        'eventType': '<detailType>',
                        'eventTime': '<timestamp>',
                        'eventData': '<eventDetail>'
                    })
                }
            }
        ]
    )
    
    return rule['RuleArn']