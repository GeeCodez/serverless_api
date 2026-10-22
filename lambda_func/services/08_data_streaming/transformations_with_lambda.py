import json
import base64

# structure for the handler

def handler(event, context):
    output = []
    
    for record in event['records']:
        # Decode the data
        payload = json.loads(base64.b64decode(record['data']))
        
        # Transform the data
        transformed_data = transform_record(payload)
        
        # Encode and return
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(
                json.dumps(transformed_data).encode('utf-8')
            ).decode('utf-8')
        }
        output.append(output_record)
    
    return {'records': output}

def transform_record(payload):
    # Your transformation logic here
    return payload


# further transformations 
import json
import base64
import boto3

dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table('Products')

def handler(event, context):
    output = []
    
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        
        # Enrich product view events
        if payload['event_type'] == 'product_view' and 'id' in payload:
            product = get_product_info(payload['id'])
            if product:
                payload['product_name'] = product['title']
                payload['category'] = product['category']
                payload['price'] = product['price']
        
        # Add timestamp if missing
        if 'timestamp' not in payload:
            from datetime import datetime, timezone
            payload['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(
                json.dumps(payload).encode('utf-8')
            ).decode('utf-8')
        }
        output.append(output_record)
    
    return {'records': output}

def get_product_info(product_id):
    try:
        response = products_table.get_item(Key={'id': product_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching product {product_id}: {e}")
        return None
    
    
# filtering and validation
def handler(event, context):
    output = []
    
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        
        # Filter test users
        if payload.get('user_id', '').startswith('test_'):
            output_record = {
                'recordId': record['recordId'],
                'result': 'Dropped',
                'data': record['data']
            }
            output.append(output_record)
            continue
        
        # Validate required fields
        if not all(key in payload for key in ['event_type', 'user_id', 'timestamp']):
            output_record = {
                'recordId': record['recordId'],
                'result': 'ProcessingFailed',
                'data': record['data']
            }
            output.append(output_record)
            continue
        
        # Record is valid
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(
                json.dumps(payload).encode('utf-8')
            ).decode('utf-8')
        }
        output.append(output_record)
    
    return {'records': output}

