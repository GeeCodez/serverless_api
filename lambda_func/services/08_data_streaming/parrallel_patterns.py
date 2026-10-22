# Stream for Amazon S3 as a data lake
import boto3
firehose=boto3.client('firehose')

firehose.create_delivery_stream(
    DeliveryStreamName='activity-to-datalake',
    DeliveryStreamType='DirectPut',
    S3DestinationConfiguration={
        'RoleARN': 'arn:aws:iam::111122223333:role/firehose-delivery-role',
        'BucketARN': 'arn:aws:s3:::amzn-s3-demo-bucket',
        'Prefix': 'datalake/customer-activity/',
        'CompressionFormat': 'GZIP'
    }
)

# Stream for Redshift analytics
firehose.create_delivery_stream(
    DeliveryStreamName='activity-to-redshift',
    DeliveryStreamType='DirectPut',
    RedshiftDestinationConfiguration={
        'RoleARN': 'arn:aws:iam::111122223333:role/firehose-delivery-role',
        'ClusterJDBCURL': 'jdbc:redshift://cluster.region.redshift.amazonaws.com:5439/database',
        'CopyCommand': {
            'DataTableName': 'customer_activity',
            'CopyOptions': 'JSON \'auto\''
        },
        # Credentials come from AWS Secrets Manager, never hardcoded
        'SecretsManagerConfiguration': {
            'Enabled': True,
            'SecretARN': 'arn:aws:secretsmanager:us-east-1:111122223333:secret:firehose-redshift-credentials'
        },
        'S3Configuration': {
            'RoleARN': 'arn:aws:iam::111122223333:role/firehose-delivery-role',
            'BucketARN': 'arn:aws:s3:::amzn-s3-demo-bucket',
            'Prefix': 'redshift-staging/'
        }
    }
)

# implementing fanouts
import boto3, json
sns = boto3.client('sns')
firehose = boto3.client('firehose')

# Publish to SNS topic
def send_customer_activity(event_data):
    response = sns.publish(
        TopicArn='arn:aws:sns:us-east-1:111122223333:customer-activity',
        Message=json.dumps(event_data)
    )
    return response