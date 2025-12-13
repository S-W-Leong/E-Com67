import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
cart_table = dynamodb.Table(os.environ['CART_TABLE'])
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Cart handler - add, remove, or list items
    """
    try:
        http_method = event['httpMethod']
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
        
        if not user_id:
            return error_response(401, "Unauthorized")
        
        if http_method == 'GET':
            return get_cart(user_id)
        
        elif http_method == 'POST':
            body = json.loads(event['body'])
            return add_to_cart(user_id, body)
        
        elif http_method == 'DELETE':
            body = json.loads(event.get('body', '{}'))
            return remove_from_cart(user_id, body)
        
        return error_response(400, "Unsupported method")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")

def get_cart(user_id: str) -> Dict:
    """Get all items in user's cart"""
    response = cart_table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    
    items = response.get('Items', [])
    total = Decimal('0')
    
    for item in items:
        total += Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 1)))
    
    return success_response({
        'items': items,
        'total': float(total)
    })

def add_to_cart(user_id: str, data: Dict) -> Dict:
    """Add item to cart"""
    try:
        product_id = data['productId']
        quantity = data.get('quantity', 1)
        
        # Get product details
        product = products_table.get_item(Key={'productId': product_id})
        if 'Item' not in product:
            return error_response(404, "Product not found")
        
        product_item = product['Item']
        
        # Add to cart
        cart_table.put_item(Item={
            'userId': user_id,
            'productId': product_id,
            'name': product_item.get('name'),
            'price': product_item.get('price'),
            'quantity': quantity
        })
        
        return success_response({'message': 'Item added to cart'})
    except Exception as e:
        return error_response(400, str(e))

def remove_from_cart(user_id: str, data: Dict) -> Dict:
    """Remove item from cart"""
    try:
        product_id = data['productId']
        cart_table.delete_item(
            Key={'userId': user_id, 'productId': product_id}
        )
        return success_response({'message': 'Item removed from cart'})
    except Exception as e:
        return error_response(400, str(e))

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
