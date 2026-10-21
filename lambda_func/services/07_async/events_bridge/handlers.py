import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def inventory_processor_handler(event, context):
    """Process inventory-related events from EventBridge."""
    dynamodb = boto3.resource('dynamodb')
    products_table = dynamodb.Table('Products')
    
    try:
        event_type = event['detail-type']
        event_detail = event['detail']
        
        logger.info(f"Processing {event_type} event")
        
        if event_type == 'Order Placed':
            # Update inventory for ordered items
            for item in event_detail['items']:
                products_table.update_item(
                    Key={'id': item['productId']},
                    UpdateExpression='ADD inventory_count :qty',
                    ExpressionAttributeValues={':qty': -item['quantity']}
                )
        
        return {'statusCode': 200, 'body': 'Event processed'}
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise e

def notification_processor_handler(event, context):
    """Process notification events and send messages."""
    sns = boto3.client('sns')
    
    try:
        event_type = event['detail-type']
        event_detail = event['detail']
        
        if event_type == 'Order Placed':
            sns.publish(
                TopicArn=os.environ['ORDER_TOPIC_ARN'],
                Message=json.dumps(event_detail),
                Subject='Order Confirmation'
            )
        
        return {'statusCode': 200, 'body': 'Notifications sent'}
        
    except Exception as e:
        logger.error(f"Error sending notifications: {str(e)}")
        raise e

def analytics_processor_handler(event, context):
    """Process events for analytics."""
    dynamodb = boto3.resource('dynamodb')
    analytics_table = dynamodb.Table('AnalyticsEvents')
    
    try:
        analytics_table.put_item(Item={
            'event_id': context.aws_request_id,
            'event_type': event['detail-type'],
            'event_time': event['time'],
            'event_detail': json.dumps(event['detail'])
        })
        
        return {'statusCode': 200, 'body': 'Analytics processed'}
        
    except Exception as e:
        logger.error(f"Error processing analytics: {str(e)}")
        raise e