import boto3
import json
from datetime import datetime, timezone
from typing import Dict, List

def create_event_buses():
    """Create custom event buses for different business domains."""
    eventbridge = boto3.client('events')
    
    # Create order processing event bus
    order_bus = eventbridge.create_event_bus(
        Name='online-store-orders'
    )
    
    # Create inventory management event bus
    inventory_bus = eventbridge.create_event_bus(
        Name='online-store-inventory'
    )
    
    # Create customer management event bus
    customer_bus = eventbridge.create_event_bus(
        Name='online-store-customers'
    )
    
    return {
        'order_bus_arn': order_bus['EventBusArn'],
        'inventory_bus_arn': inventory_bus['EventBusArn'],
        'customer_bus_arn': customer_bus['EventBusArn']
    }

def publish_order_event(order_data: Dict, event_bus_name: str):
    """Publish order-related events to EventBridge."""
    eventbridge = boto3.client('events')
    
    # Create event entry
    event_entry = {
        'Source': 'store.orders',
        'DetailType': 'Order Placed',
        'Detail': json.dumps({
            'orderId': order_data['order_id'],
            'customerId': order_data['customer_id'],
            'orderAmount': order_data['total_amount'],
            'items': order_data['items'],
            'timestamp': order_data['timestamp'],
            'customerTier': order_data.get('customer_tier', 'regular'),
            'orderType': order_data.get('order_type', 'standard'),
            'shippingAddress': order_data.get('shipping_address', {}),
            'paymentMethod': order_data.get('payment_method', 'credit_card')
        }),
        'EventBusName': event_bus_name
    }
    
    # Publish event
    response = eventbridge.put_events(
        Entries=[event_entry]
    )
    
    if response['FailedEntryCount'] > 0:
        raise EventPublishError(f"Failed to publish event: {response['Entries'][0]['ErrorMessage']}")
    
    return response['Entries'][0]['EventId']

class EventPublishError(Exception):
    """Custom exception for event publishing failures."""
    pass

def publish_inventory_event(product_data: Dict, event_type: str, event_bus_name: str):
    """Publish inventory-related events to EventBridge."""
    eventbridge = boto3.client('events')
    
    event_entry = {
        'Source': 'store.inventory',
        'DetailType': event_type,  # 'Inventory Updated', 'Stock Low', 'Product Added'
        'Detail': json.dumps({
            'productId': product_data['id'],
            'productName': product_data['title'],
            'category': product_data['category'],
            'currentStock': product_data['inventory_count'],
            'reorderLevel': product_data.get('reorder_level', 10),
            'price': product_data['price'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'changeReason': product_data.get('change_reason', 'manual_update')
        }),
        'EventBusName': event_bus_name
    }
    
    response = eventbridge.put_events(
        Entries=[event_entry]
    )
    
    return response['Entries'][0]['EventId']