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
    Supports both API Gateway and Step Functions invocations
    """
    try:
        # Check if this is a Step Functions invocation (no httpMethod)
        if 'action' in event and 'httpMethod' not in event:
            return handle_step_functions_invocation(event)
        
        # API Gateway invocation
        http_method = event.get('httpMethod')
        if not http_method:
            logger.warning("Missing httpMethod in event")
            return error_response(400, "Invalid request format")
            
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
def handle_step_functions_invocation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Step Functions invocation for cart validation.
    Returns direct response (not API Gateway format).
    """
    action = event.get('action')
    user_id = event.get('userId')
    
    logger.info(f"Step Functions invocation - action: {action}", extra={"user_id": user_id})
    
    if action == 'validate':
        return validate_cart_for_checkout(event)
    else:
        raise ValueError(f"Unknown action: {action}")


@tracer.capture_method
def validate_cart_for_checkout(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate cart items for checkout process.
    Called from Step Functions checkout workflow.
    """
    user_id = event.get('userId')
    order_id = event.get('orderId')
    items = event.get('items', [])
    total_amount = event.get('totalAmount')
    
    logger.info("Validating cart for checkout", extra={
        "user_id": user_id,
        "order_id": order_id,
        "items_count": len(items)
    })
    
    # Validate items exist and have valid quantities
    validated_items = []
    calculated_total = Decimal('0')
    
    for item in items:
        product_id = item.get('productId')
        quantity = int(item.get('quantity', 1))
        price = Decimal(str(item.get('price', 0)))
        
        if quantity < 1:
            raise ValueError(f"Invalid quantity for product {product_id}")
        
        # Verify product exists
        product_response = products_table.get_item(Key={'productId': product_id})
        if 'Item' not in product_response:
            raise ValueError(f"Product not found: {product_id}")
        
        product = product_response['Item']
        
        validated_items.append({
            'productId': product_id,
            'name': item.get('name', product.get('name')),
            'price': float(price),
            'quantity': quantity
        })
        
        calculated_total += price * quantity
    
    # Add tax (10%)
    tax = calculated_total * Decimal('0.10')
    final_total = calculated_total + tax
    
    logger.info("Cart validation successful", extra={
        "calculated_total": float(final_total),
        "provided_total": total_amount
    })
    
    # Return validated data for next step
    return {
        'orderId': order_id,
        'userId': user_id,
        'items': validated_items,
        'subtotal': float(calculated_total),
        'tax': float(tax),
        'totalAmount': str(total_amount),  # Keep original for payment
        'paymentToken': event.get('paymentToken'),
        'email': event.get('email'),
        'validated': True
    }

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
    """Add item to cart or update quantity"""
    try:
        product_id = data['productId']
        quantity = data.get('quantity', 1)
        
        # Ensure quantity is at least 1
        if quantity < 1:
            return error_response(400, "Quantity must be at least 1")
        
        logger.info("Updating cart item", extra={"user_id": user_id, "product_id": product_id, "quantity": quantity})
        
        # Get product details
        product = products_table.get_item(Key={'productId': product_id})
        if 'Item' not in product:
            logger.warning("Product not found", extra={"product_id": product_id})
            return error_response(404, "Product not found")
        
        product_item = product['Item']
        
        # Update cart with exact quantity (frontend handles increment/decrement logic)
        cart_table.put_item(Item={
            'userId': user_id,
            'productId': product_id,
            'name': product_item.get('name'),
            'price': product_item.get('price'),
            'description': product_item.get('description', ''),
            'imageUrl': product_item.get('imageUrl', ''),
            'quantity': quantity
        })
        
        logger.info("Cart item updated successfully", extra={"quantity": quantity})
        return success_response({'message': 'Cart updated'})
    except Exception as e:
        logger.exception("Error updating cart")
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
