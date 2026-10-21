import json
import boto3
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def order_processor_handler(event, context):
    """Main order processing Lambda triggered by SQS messages."""
    sns = boto3.client('sns')
    
    # Environment variables for topic ARNs
    customer_topic_arn = os.environ['CUSTOMER_NOTIFICATION_TOPIC']
    system_topic_arn = os.environ['SYSTEM_ALERT_TOPIC']
    
    for record in event['Records']:
        try:
            # Parse order message
            order_data = json.loads(record['body'])
            order_id = order_data['order_id']
            
            logger.info(f"Processing order {order_id}")
            
            # Execute order processing workflow
            processing_result = execute_order_workflow(order_data)
            
            if processing_result['success']:
                # Send customer confirmation
                send_order_confirmation(order_data, customer_topic_arn)
                
                # Update order status
                update_order_status(order_id, 'confirmed')
                
                logger.info(f"Order {order_id} processed successfully")
            else:
                # Send failure notification
                send_processing_failure_alert(order_data, processing_result['error'], system_topic_arn)
                
                # Update order status
                update_order_status(order_id, 'failed')
                
                # Re-raise to trigger SQS retry mechanism
                raise OrderProcessingError(f"Order {order_id} processing failed: {processing_result['error']}")
                
        except Exception as e:
            logger.error(f"Error processing order: {str(e)}")
            
            # Send system alert for processing errors
            send_system_alert({
                'error_type': 'order_processing_error',
                'error_message': str(e),
                'order_id': order_data.get('order_id', 'unknown')
            }, system_topic_arn)
            
            raise e
    
    return {'statusCode': 200, 'body': 'Orders processed successfully'}

def inventory_monitor_handler(event, context):
    """Monitor inventory levels and send alerts when stock is low."""
    dynamodb = boto3.resource('dynamodb')
    sns = boto3.client('sns')
    
    products_table = dynamodb.Table('Products')
    inventory_topic_arn = os.environ['INVENTORY_ALERT_TOPIC']
    
    # Scan for products with low inventory
    response = products_table.scan(
        FilterExpression='inventory_count <= reorder_level'
    )
    
    low_stock_products = response['Items']
    
    for product in low_stock_products:
        # Send inventory alert
        alert_sent = send_inventory_alert(product, inventory_topic_arn)
        
        if alert_sent:
            # Update product with alert timestamp
            products_table.update_item(
                Key={'id': product['id']},
                UpdateExpression='SET last_inventory_alert = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
    
    return {
        'statusCode': 200,
        'body': f'Processed {len(low_stock_products)} low stock alerts'
    }

def notification_dispatcher_handler(event, context):
    """Dispatch notifications based on SNS messages."""
    for record in event['Records']:
        # Parse SNS message
        sns_message = json.loads(record['Sns']['Message'])
        message_attributes = record['Sns']['MessageAttributes']
        
        # Determine notification type and route accordingly
        notification_type = message_attributes.get('notification_type', {}).get('Value', 'general')
        
        if notification_type == 'order_confirmation':
            send_order_email(sns_message)
            send_order_sms(sns_message)
        elif notification_type == 'inventory_alert':
            send_inventory_email(sns_message)
            create_reorder_task(sns_message)
        elif notification_type == 'system_alert':
            send_admin_notification(sns_message)
            log_system_event(sns_message)
    
    return {'statusCode': 200, 'body': 'Notifications dispatched'}



# This function reads the topic ARNs from Lambda environment variables — an unset variable raises KeyError at invoke. Set them on the function, copying the ARNs from the create_topic output shown earlier:

# Code

# aws lambda update-function-configuration \
#     --function-name <your-function-name> \
#     --environment "Variables={CUSTOMER_NOTIFICATION_TOPIC=<topic-arn>,SYSTEM_ALERT_TOPIC=<topic-arn>,INVENTORY_ALERT_TOPIC=<topic-arn>}"