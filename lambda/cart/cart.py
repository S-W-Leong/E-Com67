"""
Cart Lambda Function

Handles shopping cart operations including add, update, remove, and get.
Implements cart validation logic with product availability checks.
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

# Import utilities from layer
from utils.validators import validate_cart_item, ValidationError
from utils.exceptions import BusinessLogicError
from utils.formatters import format_timestamp


def convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj


logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

def get_cart_table():
    """Get cart table with lazy initialization"""
    return dynamodb.Table(os.environ['CART_TABLE_NAME'])

def get_products_table():
    """Get products table with lazy initialization"""
    return dynamodb.Table(os.environ['PRODUCTS_TABLE_NAME'])


class CartService:
    """Service class for cart operations"""
    
    @staticmethod
    @tracer.capture_method
    def add_item_to_cart(user_id: str, cart_item: Dict[str, Any]) -> Dict[str, Any]:
        """Add or update item in cart with product availability validation"""
        logger.info("Adding item to cart", extra={"user_id": user_id, "cart_item": cart_item})
        
        # Validate cart item data
        validated_item = validate_cart_item(cart_item)
        product_id = validated_item['productId']
        quantity = validated_item['quantity']
        
        # Get product details and validate availability
        product = CartService._get_product_details(product_id)
        if not product:
            raise BusinessLogicError(f"Product {product_id} not found")
        
        if not product.get('isActive', False):
            raise BusinessLogicError(f"Product {product_id} is not available")
        
        # Check stock availability
        available_stock = product.get('stock', 0)
        if available_stock < quantity:
            raise BusinessLogicError(f"Insufficient stock. Available: {available_stock}, Requested: {quantity}")
        
        current_time = int(time.time())
        
        # Check if item already exists in cart
        existing_item = CartService._get_cart_item(user_id, product_id)
        
        if existing_item:
            # Update existing item quantity
            new_quantity = existing_item['quantity'] + quantity
            
            # Validate total quantity against stock
            if available_stock < new_quantity:
                raise BusinessLogicError(f"Insufficient stock for total quantity. Available: {available_stock}, Total requested: {new_quantity}")
            
            try:
                response = get_cart_table().update_item(
                    Key={'userId': user_id, 'productId': product_id},
                    UpdateExpression="SET quantity = :quantity, updatedAt = :updated_at",
                    ExpressionAttributeValues={
                        ':quantity': int(new_quantity),  # Ensure it's an int
                        ':updated_at': current_time
                    },
                    ReturnValues='ALL_NEW'
                )
                
                updated_item = response['Attributes']
                updated_item = convert_decimals_to_float(updated_item)
                
                logger.info("Cart item updated", extra={"user_id": user_id, "product_id": product_id, "new_quantity": new_quantity})
                metrics.add_metric(name="CartItemUpdated", unit=MetricUnit.Count, value=1)
                
                return updated_item
                
            except ClientError as e:
                logger.error("Failed to update cart item", extra={"user_id": user_id, "product_id": product_id, "error": str(e)})
                raise BusinessLogicError(f"Failed to update cart item: {str(e)}")
        else:
            # Add new item to cart
            cart_item_data = {
                'userId': user_id,
                'productId': product_id,
                'name': product['name'],
                'price': Decimal(str(product['price'])),
                'quantity': quantity,
                'imageUrl': product.get('imageUrl', ''),
                'addedAt': current_time,
                'updatedAt': current_time
            }
            
            try:
                get_cart_table().put_item(Item=cart_item_data)
                
                # Convert Decimal back to float for JSON serialization
                cart_item_data = convert_decimals_to_float(cart_item_data)
                
                logger.info("Cart item added", extra={"user_id": user_id, "product_id": product_id})
                metrics.add_metric(name="CartItemAdded", unit=MetricUnit.Count, value=1)
                
                return cart_item_data
                
            except ClientError as e:
                logger.error("Failed to add cart item", extra={"user_id": user_id, "product_id": product_id, "error": str(e)})
                raise BusinessLogicError(f"Failed to add cart item: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def update_cart_item(user_id: str, product_id: str, quantity: int) -> Optional[Dict[str, Any]]:
        """Update cart item quantity with stock validation"""
        logger.info("Updating cart item", extra={"user_id": user_id, "product_id": product_id, "quantity": quantity})
        
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        # Get product details and validate availability
        product = CartService._get_product_details(product_id)
        if not product:
            raise BusinessLogicError(f"Product {product_id} not found")
        
        if not product.get('isActive', False):
            raise BusinessLogicError(f"Product {product_id} is not available")
        
        # Check stock availability
        available_stock = product.get('stock', 0)
        if available_stock < quantity:
            raise BusinessLogicError(f"Insufficient stock. Available: {available_stock}, Requested: {quantity}")
        
        current_time = int(time.time())
        
        try:
            response = get_cart_table().update_item(
                Key={'userId': user_id, 'productId': product_id},
                UpdateExpression="SET quantity = :quantity, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ':quantity': quantity,
                    ':updated_at': current_time
                },
                ConditionExpression=Attr('userId').exists() & Attr('productId').exists(),
                ReturnValues='ALL_NEW'
            )
            
            updated_item = response['Attributes']
            updated_item = convert_decimals_to_float(updated_item)
            
            logger.info("Cart item quantity updated", extra={"user_id": user_id, "product_id": product_id, "quantity": quantity})
            metrics.add_metric(name="CartItemQuantityUpdated", unit=MetricUnit.Count, value=1)
            
            return updated_item
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Cart item not found for update", extra={"user_id": user_id, "product_id": product_id})
                return None
            
            logger.error("Failed to update cart item", extra={"user_id": user_id, "product_id": product_id, "error": str(e)})
            raise BusinessLogicError(f"Failed to update cart item: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def remove_cart_item(user_id: str, product_id: str) -> bool:
        """Remove item from cart"""
        logger.info("Removing cart item", extra={"user_id": user_id, "product_id": product_id})
        
        try:
            response = get_cart_table().delete_item(
                Key={'userId': user_id, 'productId': product_id},
                ConditionExpression=Attr('userId').exists() & Attr('productId').exists(),
                ReturnValues='ALL_OLD'
            )
            
            if 'Attributes' in response:
                logger.info("Cart item removed", extra={"user_id": user_id, "product_id": product_id})
                metrics.add_metric(name="CartItemRemoved", unit=MetricUnit.Count, value=1)
                return True
            else:
                logger.info("Cart item not found for removal", extra={"user_id": user_id, "product_id": product_id})
                return False
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Cart item not found for removal", extra={"user_id": user_id, "product_id": product_id})
                return False
            
            logger.error("Failed to remove cart item", extra={"user_id": user_id, "product_id": product_id, "error": str(e)})
            raise BusinessLogicError(f"Failed to remove cart item: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def get_cart_contents(user_id: str) -> Dict[str, Any]:
        """Get all cart contents with real-time pricing and availability validation"""
        logger.info("Getting cart contents", extra={"user_id": user_id})
        
        try:
            response = get_cart_table().query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            
            cart_items = response.get('Items', [])
            
            # Validate each item against current product data and update pricing
            validated_items = []
            subtotal = Decimal('0')
            unavailable_items = []
            
            for item in cart_items:
                product_id = item['productId']
                
                # Get current product details
                product = CartService._get_product_details(product_id)
                
                if not product or not product.get('isActive', False):
                    unavailable_items.append({
                        'productId': product_id,
                        'name': item.get('name', 'Unknown Product'),
                        'reason': 'Product no longer available'
                    })
                    continue
                
                # Check stock availability
                available_stock = product.get('stock', 0)
                requested_quantity = item['quantity']
                
                if available_stock < requested_quantity:
                    unavailable_items.append({
                        'productId': product_id,
                        'name': product['name'],
                        'reason': f'Insufficient stock. Available: {available_stock}, In cart: {requested_quantity}'
                    })
                    continue
                
                # Update item with current pricing
                current_price = Decimal(str(product['price']))
                item_total = current_price * requested_quantity
                
                validated_item = {
                    'userId': item['userId'],
                    'productId': product_id,
                    'name': product['name'],
                    'price': float(current_price),
                    'quantity': requested_quantity,
                    'itemTotal': float(item_total),
                    'imageUrl': product.get('imageUrl', ''),
                    'addedAt': item.get('addedAt'),
                    'updatedAt': item.get('updatedAt')
                }
                
                validated_items.append(validated_item)
                subtotal += item_total
            
            # Calculate totals (for now, just subtotal - tax calculation would be added later)
            tax_rate = Decimal('0.08')  # 8% tax rate - would be configurable
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            cart_summary = {
                'items': validated_items,
                'itemCount': len(validated_items),
                'subtotal': float(subtotal),
                'taxAmount': float(tax_amount),
                'totalAmount': float(total_amount),
                'unavailableItems': unavailable_items,
                'isValid': len(unavailable_items) == 0
            }
            
            logger.info("Cart contents retrieved", extra={
                "user_id": user_id, 
                "item_count": len(validated_items),
                "unavailable_count": len(unavailable_items)
            })
            metrics.add_metric(name="CartContentsRetrieved", unit=MetricUnit.Count, value=1)
            
            return cart_summary
            
        except ClientError as e:
            logger.error("Failed to get cart contents", extra={"user_id": user_id, "error": str(e)})
            raise BusinessLogicError(f"Failed to get cart contents: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def clear_cart(user_id: str) -> bool:
        """Clear all items from user's cart"""
        logger.info("Clearing cart", extra={"user_id": user_id})
        
        try:
            # Get all cart items first
            response = get_cart_table().query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            
            cart_items = response.get('Items', [])
            
            if not cart_items:
                logger.info("Cart already empty", extra={"user_id": user_id})
                return True
            
            # Delete all items
            with get_cart_table().batch_writer() as batch:
                for item in cart_items:
                    batch.delete_item(
                        Key={
                            'userId': item['userId'],
                            'productId': item['productId']
                        }
                    )
            
            logger.info("Cart cleared", extra={"user_id": user_id, "items_removed": len(cart_items)})
            metrics.add_metric(name="CartCleared", unit=MetricUnit.Count, value=1)
            
            return True
            
        except ClientError as e:
            logger.error("Failed to clear cart", extra={"user_id": user_id, "error": str(e)})
            raise BusinessLogicError(f"Failed to clear cart: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def validate_cart_for_checkout(user_id: str) -> Dict[str, Any]:
        """Validate cart for checkout - used by Step Functions"""
        logger.info("Validating cart for checkout", extra={"user_id": user_id})
        
        cart_contents = CartService.get_cart_contents(user_id)
        
        if not cart_contents['items']:
            raise BusinessLogicError("Cart is empty")
        
        if not cart_contents['isValid']:
            unavailable_items = cart_contents['unavailableItems']
            raise BusinessLogicError(f"Cart contains unavailable items: {unavailable_items}")
        
        # Return validation result for Step Functions
        validation_result = {
            'isValid': True,
            'userId': user_id,
            'items': cart_contents['items'],
            'subtotal': cart_contents['subtotal'],
            'taxAmount': cart_contents['taxAmount'],
            'totalAmount': cart_contents['totalAmount'],
            'itemCount': cart_contents['itemCount']
        }
        
        logger.info("Cart validation successful", extra={"user_id": user_id, "total_amount": cart_contents['totalAmount']})
        metrics.add_metric(name="CartValidatedForCheckout", unit=MetricUnit.Count, value=1)
        
        return validation_result
    
    @staticmethod
    @tracer.capture_method
    def _get_product_details_raw(product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details from products table with original Decimal types"""
        try:
            response = get_products_table().get_item(Key={'productId': product_id})
            
            if 'Item' not in response:
                return None
            
            return response['Item']
            
        except ClientError as e:
            logger.error("Failed to get product details", extra={"product_id": product_id, "error": str(e)})
            return None
    
    @staticmethod
    @tracer.capture_method
    def _get_product_details(product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details from products table"""
        try:
            response = get_products_table().get_item(Key={'productId': product_id})
            
            if 'Item' not in response:
                return None
            
            product = response['Item']
            # Convert Decimal objects to float for calculations
            product = convert_decimals_to_float(product)
            
            return product
            
        except ClientError as e:
            logger.error("Failed to get product details", extra={"product_id": product_id, "error": str(e)})
            return None
    
    @staticmethod
    @tracer.capture_method
    def _get_cart_item(user_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Get specific cart item"""
        try:
            response = get_cart_table().get_item(
                Key={'userId': user_id, 'productId': product_id}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            # Convert Decimal objects to float
            item = convert_decimals_to_float(item)
            
            return item
            
        except ClientError as e:
            logger.error("Failed to get cart item", extra={"user_id": user_id, "product_id": product_id, "error": str(e)})
            return None


def extract_user_id_from_event(event: Dict[str, Any]) -> str:
    """Extract user ID from JWT token in API Gateway event"""
    # For now, we'll use a placeholder - in real implementation this would extract from JWT
    # This would be replaced with proper JWT token parsing
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    # In a real implementation, this would extract the user ID from the JWT claims
    user_id = authorizer.get('claims', {}).get('sub')
    
    if not user_id:
        # For testing purposes, allow user_id to be passed in headers
        headers = event.get('headers', {})
        user_id = headers.get('x-user-id') or headers.get('X-User-Id')
    
    if not user_id:
        raise ValidationError("User ID not found in request")
    
    return user_id


def create_error_response(status_code: int, error_code: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized error response"""
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": format_timestamp(time.time())
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-User-Id"
        },
        "body": json.dumps(error_response)
    }


def create_success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-User-Id"
        },
        "body": json.dumps(data)
    }


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for cart operations"""
    
    logger.info("Cart function invoked", extra={"event": event})
    
    try:
        http_method = event.get('httpMethod', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        # Handle Step Functions invocation for checkout validation first
        if event.get('source') == 'step-functions':
            # This is a Step Functions invocation
            step_function_input = event.get('input', {})
            user_id = step_function_input.get('userId')
            
            if not user_id:
                raise ValidationError("User ID required for checkout validation")
            
            validation_result = CartService.validate_cart_for_checkout(user_id)
            return validation_result
        
        # Handle OPTIONS request for CORS
        if http_method == 'OPTIONS':
            return create_success_response({}, 200)
        
        # Extract user ID from JWT token or headers
        try:
            user_id = extract_user_id_from_event(event)
        except ValidationError as e:
            return create_error_response(401, "UNAUTHORIZED", str(e))
        
        # Route based on HTTP method and path
        if http_method == 'GET':
            # Get cart contents
            cart_contents = CartService.get_cart_contents(user_id)
            return create_success_response(cart_contents)
        
        elif http_method == 'POST':
            # Add item to cart
            try:
                body = json.loads(event.get('body', '{}'))
                cart_item = CartService.add_item_to_cart(user_id, body)
                return create_success_response(cart_item, 201)
            except json.JSONDecodeError:
                return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
            except ValidationError as e:
                return create_error_response(400, "VALIDATION_ERROR", str(e))
            except BusinessLogicError as e:
                return create_error_response(400, "BUSINESS_LOGIC_ERROR", str(e))
        
        elif http_method == 'PUT':
            # Update cart item quantity
            product_id = path_parameters.get('productId')
            if not product_id:
                return create_error_response(400, "MISSING_PRODUCT_ID", "Product ID is required")
            
            try:
                body = json.loads(event.get('body', '{}'))
                quantity = body.get('quantity')
                
                if quantity is None:
                    return create_error_response(400, "MISSING_QUANTITY", "Quantity is required")
                
                updated_item = CartService.update_cart_item(user_id, product_id, quantity)
                if updated_item:
                    return create_success_response(updated_item)
                else:
                    return create_error_response(404, "CART_ITEM_NOT_FOUND", "Cart item not found")
            except json.JSONDecodeError:
                return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
            except ValidationError as e:
                return create_error_response(400, "VALIDATION_ERROR", str(e))
            except BusinessLogicError as e:
                return create_error_response(400, "BUSINESS_LOGIC_ERROR", str(e))
        
        elif http_method == 'DELETE':
            product_id = path_parameters.get('productId')
            
            if product_id:
                # Remove specific item from cart
                success = CartService.remove_cart_item(user_id, product_id)
                if success:
                    return create_success_response({"message": "Item removed from cart"})
                else:
                    return create_error_response(404, "CART_ITEM_NOT_FOUND", "Cart item not found")
            else:
                # Clear entire cart
                success = CartService.clear_cart(user_id)
                if success:
                    return create_success_response({"message": "Cart cleared"})
                else:
                    return create_error_response(500, "CLEAR_CART_FAILED", "Failed to clear cart")
        
        else:
            return create_error_response(405, "METHOD_NOT_ALLOWED", f"HTTP method {http_method} not allowed")
    
    except Exception as e:
        logger.exception("Unexpected error in cart function")
        metrics.add_metric(name="CartUnexpectedError", unit=MetricUnit.Count, value=1)
        
        return create_error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred")