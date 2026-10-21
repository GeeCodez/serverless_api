import boto3
import json
from typing import Dict, List

def create_notification_topics():
    """Create SNS topics for different notification types."""
    sns = boto3.client('sns')
    
    # Customer notification topic
    customer_topic = sns.create_topic(
        Name='customer-notifications',
        Attributes={
            'DisplayName': 'Customer Notifications',
            'DeliveryPolicy': json.dumps({
                'http': {
                    'defaultHealthyRetryPolicy': {
                        'minDelayTarget': 20,
                        'maxDelayTarget': 20,
                        'numRetries': 3,
                        'numMaxDelayRetries': 0,
                        'backoffFunction': 'linear'
                    }
                }
            })
        }
    )
    
    # System alert topic
    system_topic = sns.create_topic(
        Name='system-alerts',
        Attributes={
            'DisplayName': 'System Alerts',
            'DeliveryPolicy': json.dumps({
                'http': {
                    'defaultHealthyRetryPolicy': {
                        'minDelayTarget': 20,
                        'maxDelayTarget': 20,
                        'numRetries': 5,
                        'numMaxDelayRetries': 0,
                        'backoffFunction': 'exponential'
                    }
                }
            })
        }
    )
    
    # Inventory alert topic
    inventory_topic = sns.create_topic(
        Name='inventory-alerts',
        Attributes={
            'DisplayName': 'Inventory Alerts'
        }
    )
    
    return {
        'customer_topic_arn': customer_topic['TopicArn'],
        'system_topic_arn': system_topic['TopicArn'],
        'inventory_topic_arn': inventory_topic['TopicArn']
    }

def subscribe_to_notifications(topic_arn: str, subscription_type: str, endpoint: str):
    """Subscribe endpoints to SNS topics."""
    sns = boto3.client('sns')
    
    subscription = sns.subscribe(
        TopicArn=topic_arn,
        Protocol=subscription_type,  # 'email', 'sms', 'http', 'https', 'sqs'
        Endpoint=endpoint
    )
    
    return subscription['SubscriptionArn']