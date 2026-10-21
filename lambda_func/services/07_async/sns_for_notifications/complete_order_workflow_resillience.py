def execute_order_workflow(order_data: Dict) -> Dict:
    """Execute order processing with error handling."""
    workflow_steps = [
        ('validate_inventory', validate_inventory_step),
        ('process_payment', process_payment_step),
        ('create_shipping', create_shipping_step),
        ('update_analytics', update_analytics_step)
    ]
    
    completed_steps = []
    
    try:
        for step_name, step_function in workflow_steps:
            logger.info(f"Executing step: {step_name}")
            
            step_result = step_function(order_data)
            
            if not step_result['success']:
                # Rollback completed steps
                rollback_completed_steps(completed_steps, order_data)
                return {
                    'success': False,
                    'error': f"Step {step_name} failed: {step_result['error']}",
                    'failed_step': step_name
                }
            
            completed_steps.append({
                'step': step_name,
                'result': step_result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return {
            'success': True,
            'completed_steps': completed_steps,
            'total_processing_time': calculate_processing_time(completed_steps)
        }
        
    except Exception as e:
        # Rollback any completed steps
        rollback_completed_steps(completed_steps, order_data)
        
        return {
            'success': False,
            'error': f"Workflow exception: {str(e)}",
            'completed_steps': completed_steps
        }

def rollback_completed_steps(completed_steps: List[Dict], order_data: Dict):
    """Rollback completed workflow steps in reverse order."""
    rollback_functions = {
        'validate_inventory': rollback_inventory_reservation,
        'process_payment': rollback_payment_charge,
        'create_shipping': rollback_shipping_label,
        'update_analytics': rollback_analytics_update
    }
    
    # Rollback in reverse order
    for step in reversed(completed_steps):
        step_name = step['step']
        rollback_function = rollback_functions.get(step_name)
        
        if rollback_function:
            try:
                rollback_result = rollback_function(order_data, step['result'])
                logger.info(f"Rolled back step: {step_name}")
            except Exception as e:
                logger.error(f"Failed to rollback step {step_name}: {str(e)}")
                # Continue with other rollbacks even if one fails

def configure_lambda_triggers():
    """Configure Lambda function triggers for SQS and SNS."""
    lambda_client = boto3.client('lambda')
    
    # Configure SQS trigger for order processing
    lambda_client.create_event_source_mapping(
        EventSourceArn='arn:aws:sqs:region:account:order-processing-queue',
        FunctionName='order-processor',
        BatchSize=10,  # Process up to 10 messages at once
        MaximumBatchingWindowInSeconds=5,  # Wait up to 5 seconds to batch messages
    )
    
    # Configure SNS trigger for notification dispatch
    lambda_client.add_permission(
        FunctionName='notification-dispatcher',
        StatementId='sns-trigger',
        Action='lambda:InvokeFunction',
        Principal='sns.amazonaws.com',
        SourceArn='arn:aws:sns:region:account:customer-notifications'
    )