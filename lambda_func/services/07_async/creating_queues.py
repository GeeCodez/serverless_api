import boto3
import json
from datetime import datetime, timezone

def create_order_processing_queue():
    """Create SQS queue for background order processing."""
    sqs = boto3.client('sqs')
    
    # Create main order processing queue
    queue_response = sqs.create_queue(
        QueueName='order-processing-queue',
        Attributes={
            'VisibilityTimeoutSeconds': '300',  # 5 minutes for processing
            'MessageRetentionPeriod': '1209600',  # 14 days
            'ReceiveMessageWaitTimeSeconds': '20',  # Long polling
            'RedrivePolicy': json.dumps({
                'deadLetterTargetArn': 'arn:aws:sqs:region:account:order-processing-dlq',
                'maxReceiveCount': 3
            })
        }
    )
    
    # Create dead letter queue for failed messages
    dlq_response = sqs.create_queue(
        QueueName='order-processing-dlq',
        Attributes={
            'MessageRetentionPeriod': '1209600',  # 14 days for investigation
            'VisibilityTimeoutSeconds': '60'
        }
    )
    
    return queue_response['QueueUrl'], dlq_response['QueueUrl']

def send_order_to_queue(order_data, queue_url):
    """Send order data to SQS queue for background processing."""
    sqs = boto3.client('sqs')
    
    message_body = {
        'order_id': order_data['order_id'],
        'customer_id': order_data['customer_id'],
        'items': order_data['items'],
        'total_amount': order_data['total_amount'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'processing_steps': [
            'validate_inventory',
            'process_payment',
            'create_shipping_label',
            'send_confirmation'
        ]
    }
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body),
        MessageAttributes={
            'order_priority': {
                'StringValue': order_data.get('priority', 'standard'),
                'DataType': 'String'
            },
            'customer_tier': {
                'StringValue': order_data.get('customer_tier', 'regular'),
                'DataType': 'String'
            }
        }
    )
    
    return response['MessageId']


# handling multistep workflow for order processing
import json
import boto3
import logging
from typing import Dict, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """Process order messages from SQS queue."""
    sqs = boto3.client('sqs')
    
    # Process each message in the batch
    for record in event['Records']:
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            order_id = message_body['order_id']
            
            logger.info(f"Processing order {order_id}")
            
            # Process order through defined steps
            processing_result = process_order_workflow(message_body)
            
            if processing_result['success']:
                logger.info(f"Order {order_id} processed successfully")
                # Message automatically deleted from queue on successful return
            else:
                # Raise exception to trigger retry mechanism
                raise OrderProcessingError(f"Failed to process order {order_id}: {processing_result['error']}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Message will be retried based on queue configuration
            raise e
    
    return {'statusCode': 200, 'body': 'Orders processed successfully'}

def process_order_workflow(order_data: Dict) -> Dict:
    """Execute order processing workflow steps."""
    try:
        # Step 1: Validate inventory
        inventory_result = validate_inventory(order_data['items'])
        if not inventory_result['available']:
            return {'success': False, 'error': 'Insufficient inventory'}
        
        # Step 2: Process payment
        payment_result = process_payment(
            order_data['customer_id'],
            order_data['total_amount']
        )
        if not payment_result['success']:
            return {'success': False, 'error': 'Payment processing failed'}
        
        # Step 3: Create shipping label
        shipping_result = create_shipping_label(order_data)
        if not shipping_result['success']:
            # Refund payment before failing
            refund_payment(payment_result['transaction_id'])
            return {'success': False, 'error': 'Shipping label creation failed'}
        
        # Step 4: Update order status
        update_order_status(order_data['order_id'], 'processing')
        
        return {
            'success': True,
            'payment_id': payment_result['transaction_id'],
            'shipping_label': shipping_result['label_url']
        }
        
    except Exception as e:
        logger.error(f"Order workflow error: {str(e)}")
        return {'success': False, 'error': str(e)}

def validate_inventory(items: List[Dict]) -> Dict:
    """Check product availability for order items."""
    dynamodb = boto3.resource('dynamodb')
    products_table = dynamodb.Table('Products')
    
    for item in items:
        response = products_table.get_item(
            Key={'id': item['id']}
        )
        
        if 'Item' not in response:
            return {'available': False, 'reason': f"Product {item['id']} not found"}
        
        product = response['Item']
        if product['inventory_count'] < item['quantity']:
            return {
                'available': False,
                'reason': f"Insufficient inventory for {item['id']}"
            }
    
    return {'available': True}

class OrderProcessingError(Exception):
    """Custom exception for order processing failures."""
    pass