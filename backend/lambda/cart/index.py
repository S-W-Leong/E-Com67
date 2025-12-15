import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

# AWS Lambda Powertools
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
cart_table = dynamodb.Table(os.environ['CART_TABLE'])
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Cart handler - add, remove, or list items
    """
    try:
        http_method = event['httpMethod']
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')

        logger.info(f"Processing {http_method} request", extra={"user_id": user_id})

        if not user_id:
            logger.warning("Unauthorized request - missing user_id")
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
        logger.exception("Unhandled exception in cart handler")
        return error_response(500, "Internal server error")

@tracer.capture_method
def get_cart(user_id: str) -> Dict:
    """Get all items in user's cart"""
    logger.info("Fetching cart items", extra={"user_id": user_id})
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

@tracer.capture_method
def add_to_cart(user_id: str, data: Dict) -> Dict:
    """Add item to cart"""
    try:
        product_id = data['productId']
        logger.info("Adding item to cart", extra={"user_id": user_id, "product_id": product_id})
        quantity = data.get('quantity', 1)
        
        # Get product details
        product = products_table.get_item(Key={'productId': product_id})
        if 'Item' not in product:
            logger.warning("Product not found", extra={"product_id": product_id})
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
        
        logger.info("Item added to cart successfully")
        return success_response({'message': 'Item added to cart'})
    except Exception as e:
        logger.exception("Error adding item to cart")
        return error_response(400, str(e))

@tracer.capture_method
def remove_from_cart(user_id: str, data: Dict) -> Dict:
    """Remove item from cart"""
    try:
        product_id = data['productId']
        logger.info("Removing item from cart", extra={"user_id": user_id, "product_id": product_id})
        cart_table.delete_item(
            Key={'userId': user_id, 'productId': product_id}
        )
        logger.info("Item removed from cart successfully")
        return success_response({'message': 'Item removed from cart'})
    except Exception as e:
        logger.exception("Error removing item from cart")
        return error_response(400, str(e))

def success_response(data: Any, status_code: int = 200) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,POST,DELETE'
        },
        'body': json.dumps(data, default=str)
    }

def error_response(status_code: int, message: str) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,POST,DELETE'
        },
        'body': json.dumps({'error': message})
    }
