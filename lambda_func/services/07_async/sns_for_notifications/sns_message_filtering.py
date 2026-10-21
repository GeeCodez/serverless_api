import json, boto3

def setup_filtered_subscriptions(topic_arn: str):
    """Set up SNS subscriptions with message filtering."""
    sns = boto3.client('sns')
    
    # Subscribe premium customers with filter
    premium_sub = sns.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint='premium@example.com'
    )
    
    sns.set_subscription_attributes(
        SubscriptionArn=premium_sub['SubscriptionArn'],
        AttributeName='FilterPolicy',
        AttributeValue=json.dumps({
            'customer_tier': ['premium', 'vip']
        })
    )
    
    # Subscribe to urgent notifications only
    urgent_sub = sns.subscribe(
        TopicArn=topic_arn,
        Protocol='sms',
        Endpoint='+1234567890'
    )
    
    sns.set_subscription_attributes(
        SubscriptionArn=urgent_sub['SubscriptionArn'],
        AttributeName='FilterPolicy',
        AttributeValue=json.dumps({
            'order_type': ['express', 'same_day']
        })
    )

def send_inventory_alert(product_data: Dict, topic_arn: str):
    """Send inventory alert when stock levels are low."""
    sns = boto3.client('sns')
    
    # Build the alert message for each protocol
    alert_message = {
        'default': f"Low stock: {product_data['title']} "
                   f"({product_data['inventory_count']} remaining)",
        'email': f"Inventory alert for {product_data['title']}: "
                 f"{product_data['inventory_count']} units remaining. "
                 f"Reorder level: {product_data.get('reorder_level', 10)}."
    }

    message_attributes = {
        'alert_type': {
            'DataType': 'String',
            'StringValue': 'inventory_low'
        },
        'product_category': {
            'DataType': 'String',
            'StringValue': product_data['category']
        },
        'urgency': {
            'DataType': 'String',
            'StringValue': 'high' if product_data['inventory_count'] == 0 else 'medium'
        }
    }
    
    response = sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(alert_message),
        MessageStructure='json',
        Subject=f"Inventory Alert: {product_data['title']}",
        MessageAttributes=message_attributes
    )
    
    return response['MessageId']