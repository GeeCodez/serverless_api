def send_order_confirmation(order_data: Dict, topic_arn: str):
    """Send order confirmation notification to customers."""
    sns = boto3.client('sns')
    
    # Create notification message
    message = {
        'default': f"Order {order_data['order_id']} confirmed. Total: ${order_data['total_amount']:.2f}",
        'email': create_email_message(order_data),
        'sms': create_sms_message(order_data)
    }
    
    # Message attributes for filtering
    message_attributes = {
        'order_type': {
            'DataType': 'String',
            'StringValue': order_data.get('order_type', 'standard')
        },
        'customer_tier': {
            'DataType': 'String',
            'StringValue': order_data.get('customer_tier', 'regular')
        },
        'notification_preference': {
            'DataType': 'String',
            'StringValue': order_data.get('notification_preference', 'all')
        }
    }
    
    response = sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
        MessageStructure='json',
        Subject=f"Order Confirmation - {order_data['order_id']}",
        MessageAttributes=message_attributes
    )
    
    return response['MessageId']

def create_email_message(order_data: Dict) -> str:
    """Create formatted email message for order confirmation."""
    items_list = '\n'.join([
        f"- {item['title']} (Qty: {item['quantity']}) - ${item['price']:.2f}"
        for item in order_data['items']
    ])
    
    email_template = f"""
    Dear {order_data['customer_name']},
    
    Thank you for your order! Here are the details:
    
    Order ID: {order_data['order_id']}
    Order Date: {order_data['order_date']}
    
    Items Ordered:
    {items_list}
    
    Total Amount: ${order_data['total_amount']:.2f}
    
    Estimated Delivery: {order_data.get('estimated_delivery', 'TBD')}
    
    You can track your order at: https://store.example.com/orders/{order_data['order_id']}
    
    Thank you for shopping with us!
    """
    
    return email_template.strip()

def create_sms_message(order_data: Dict) -> str:
    """Create concise SMS message for order confirmation."""
    return f"Order {order_data['order_id']} confirmed! Total: ${order_data['total_amount']:.2f}. Track at: https://store.example.com/track/{order_data['order_id']}"