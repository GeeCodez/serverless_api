import boto3
from datetime import datetime, timedelta, timezone

def monitor_queue_metrics(queue_url: str) -> Dict:
    """Monitor SQS queue metrics for scaling decisions."""
    cloudwatch = boto3.client('cloudwatch')
    sqs = boto3.client('sqs')
    
    # Get queue attributes
    queue_attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    
    # Get CloudWatch metrics
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=15)
    
    metrics = cloudwatch.get_metric_statistics(
        Namespace='AWS/SQS',
        MetricName='ApproximateNumberOfVisibleMessages',
        Dimensions=[
            {
                'Name': 'QueueName',
                'Value': queue_url.split('/')[-1]
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,  # 5 minutes
        Statistics=['Average', 'Maximum']
    )
    
    return {
        'visible_messages': int(queue_attributes['Attributes']['ApproximateNumberOfMessages']),
        'in_flight_messages': int(queue_attributes['Attributes']['ApproximateNumberOfMessagesNotVisible']),
        'average_queue_depth': metrics['Datapoints'][-1]['Average'] if metrics['Datapoints'] else 0,
        'max_queue_depth': max([dp['Maximum'] for dp in metrics['Datapoints']]) if metrics['Datapoints'] else 0
    }

def scale_processing_capacity(queue_metrics: Dict) -> Dict:
    """Determine if additional processing capacity is needed."""
    recommendations = []
    
    # Scale up if queue depth is high
    if queue_metrics['visible_messages'] > 100:
        recommendations.append({
            'action': 'scale_up',
            'reason': f"High queue depth: {queue_metrics['visible_messages']} messages",
            'suggested_capacity': min(queue_metrics['visible_messages'] // 10, 50)
        })
    
    # Scale down if queue is consistently empty
    if queue_metrics['max_queue_depth'] < 5 and queue_metrics['visible_messages'] < 10:
        recommendations.append({
            'action': 'scale_down',
            'reason': 'Low queue utilization',
            'suggested_capacity': 2
        })
    
    return {'recommendations': recommendations}