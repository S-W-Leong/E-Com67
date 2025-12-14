import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Product CRUD handler
    """
    try:
        http_method = event['httpMethod']
        path_params = event.get('pathParameters', {}) or {}
        
        if http_method == 'GET':
            if path_params and 'productId' in path_params:
                return get_product(path_params['productId'])
            else:
                return list_products(event.get('queryStringParameters', {}) or {})
        
        elif http_method == 'POST':
            body = json.loads(event['body'])
            return create_product(body)
        
        elif http_method == 'PUT':
            body = json.loads(event['body'])
            return update_product(path_params['productId'], body)
        
        elif http_method == 'DELETE':
            return delete_product(path_params['productId'])
        
        return error_response(400, "Unsupported method")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")

def list_products(query_params: Dict) -> Dict:
    """List products with optional category filter"""
    category = query_params.get('category') if query_params else None
    
    if category:
        response = products_table.query(
            IndexName='category-index',
            KeyConditionExpression='category = :cat',
            ExpressionAttributeValues={':cat': category}
        )
    else:
        response = products_table.scan(Limit=50)
    
    return success_response(response.get('Items', []))

def get_product(product_id: str) -> Dict:
    """Get single product"""
    response = products_table.get_item(Key={'productId': product_id})
    
    if 'Item' not in response:
        return error_response(404, "Product not found")
    
    return success_response(response['Item'])

def create_product(data: Dict) -> Dict:
    """Create new product"""
    import uuid
    
    product_id = str(uuid.uuid4())
    item = {
        'productId': product_id,
        'name': data['name'],
        'description': data.get('description', ''),
        'price': Decimal(str(data['price'])),
        'category': data['category'],
        'stock': data.get('stock', 0),
        'imageUrl': data.get('imageUrl', '')
    }
    
    products_table.put_item(Item=item)
    return success_response(item, 201)

def update_product(product_id: str, data: Dict) -> Dict:
    """Update existing product"""
    try:
        update_expression = "SET "
        expression_attribute_values = {}
        
        for key, value in data.items():
            if key != 'productId':
                update_expression += f"{key} = :{key}, "
                if isinstance(value, (int, float)):
                    expression_attribute_values[f":{key}"] = Decimal(str(value))
                else:
                    expression_attribute_values[f":{key}"] = value
        
        update_expression = update_expression.rstrip(", ")
        
        response = products_table.update_item(
            Key={'productId': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        return success_response(response.get('Attributes', {}))
    except Exception as e:
        return error_response(400, str(e))

def delete_product(product_id: str) -> Dict:
    """Delete product"""
    products_table.delete_item(Key={'productId': product_id})
    return success_response({'message': 'Product deleted'})

def success_response(data: Any, status_code: int = 200) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data, default=str)
    }

def error_response(status_code: int, message: str) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
