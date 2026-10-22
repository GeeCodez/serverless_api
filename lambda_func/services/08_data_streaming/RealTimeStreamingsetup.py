import boto3

firehose = boto3.client('firehose')

response = firehose.create_delivery_stream(
    DeliveryStreamName='customer-activity-stream',
    DeliveryStreamType='DirectPut',
    S3DestinationConfiguration={
        'RoleARN': 'arn:aws:iam::111122223333:role/firehose-delivery-role',
        'BucketARN': 'arn:aws:s3:::amzn-s3-demo-bucket',
        'Prefix': 'customer-activity/',
        'BufferingHints': {
            'SizeInMBs': 5,
            'IntervalInSeconds': 300
        },
        'CompressionFormat': 'GZIP'
    }
)


# creating and sending events
import json
import boto3
from datetime import datetime, timezone

firehose = boto3.client('firehose')

def send_customer_activity(event_type, user_id, product_id=None):
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'session_id': 'session_123'
    }
    
    if product_id:
        record['id'] = product_id
    
    response = firehose.put_record(
        DeliveryStreamName='customer-activity-stream',
        Record={
            # Add newline to help with processing after delivery to S3
            'Data': json.dumps(record) + '\n'
        }
    )
    
    return response

# Send product view event
send_customer_activity('product_view', 'user_456', 'prod_123')

# Send cart addition event
send_customer_activity('cart_add', 'user_456', 'prod_123')

## batch processing

def send_batch_activities(events):
    records = []
    
    for event in events:
        record_data = {
            'timestamp': event['timestamp'],
            'event_type': event['event_type'],
            'user_id': event['user_id']
        }
        
        records.append({
            'Data': json.dumps(record_data) + '\n'
        })
    
    response = firehose.put_record_batch(
        DeliveryStreamName='customer-activity-stream',
        Records=records
    )
    
    # Check for failed records
    if response['FailedPutCount'] > 0:
        print(f"Failed to send {response['FailedPutCount']} records")
        for idx, result in enumerate(response['RequestResponses']):
            if 'ErrorCode' in result:
                print(f"Record {idx} failed: {result['ErrorMessage']}")
    
    return response

# Add error handling to ExtendedS3DestinationConfiguration
# 'ErrorOutputPrefix': 'errors/',
# 'ProcessingConfiguration': {
#     'Enabled': True,
#     'Processors': [
#         {
#             'Type': 'Lambda',
#             'Parameters': [
#                 {
#                     'ParameterName': 'LambdaArn',
#                     'ParameterValue': 'arn:aws:lambda:us-east-1:111122223333:function:transform-activity'
#                 }
#             ]
#         }
#     ]
# }