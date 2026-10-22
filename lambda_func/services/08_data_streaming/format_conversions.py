import json, base64

def handler(event, context):
    output = []
    
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        
        # Convert to CSV format for Redshift
        if payload['event_type'] == 'purchase':
            csv_line = f"{payload['timestamp']},{payload['user_id']},{payload['order_id']},{payload['total_amount']}\n"
            
            output_record = {
                'recordId': record['recordId'],
                'result': 'Ok',
                'data': base64.b64encode(csv_line.encode('utf-8')).decode('utf-8')
            }
        else:
            # Keep JSON format for other events
            output_record = {
                'recordId': record['recordId'],
                'result': 'Ok',
                'data': record['data']
            }
        
        output.append(output_record)
    
    return {'records': output}

