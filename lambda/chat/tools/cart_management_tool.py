"""
Cart Management Tool for Strands AI Agent

This tool enables the Strands agent to manage shopping carts including
adding, updating, removing items, and retrieving cart contents with
real-time validation and pricing.
"""

import json
import os
import logging
import time
from typing import Dict, Any, List, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from strands import tool
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import CartSummary, CartItem, CartOperation, CartOperationType

# Initialize logger
logger = logging.getLogger(__name__)

# Environment variables
CART_TABLE_NAME = os.environ.get("CART_TABLE_NAME", "")
PRODUCTS_TABLE_NAME = os.environ.get("PRODUCTS_TABLE_NAME", "")

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
cart_table = None
products_table = None


def get_cart_table():
    """Get cart table with lazy initialization"""
    global cart_table
    if cart_table is None:
        cart_table = dynamodb.Table(CART_TABLE_NAME)
    return cart_table


def get_products_table():
    """Get products table with lazy initialization"""
    global products_table
    if products_table is None:
        products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)
    return products_table


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


class CartManagementTool:
    """Cart management tool for Strands agent"""
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize the cart management tool with user ID"""
        self.user_id = user_id
        
    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get product details from products table.
        
        Args:
            product_id: Product identifier
            
        Returns:
            Product data or None if not found
        """
        try:
            response = get_products_table().get_item(Key={'productId': product_id})
            
            if 'Item' not in response:
                return None
            
            product = response['Item']
            # Convert Decimal objects to float
            product = convert_decimals_to_float(product)
            
            return product
            
        except ClientError as e:
            logger.error(f"Failed to get product details for {product_id}: {str(e)}")
            return None
    
    def validate_product_availability(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """
        Validate product availability and pricing.
        
        Args:
            product_id: Product identifier
            quantity: Requested quantity
            
        Returns:
            Validation result with product details
            
        Raises:
            ValueError: If product is not available or insufficient stock
        """
        product = self.get_product_details(product_id)
        
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        if not product.get('isActive', False):
            raise ValueError(f"Product {product_id} is not available")
        
        available_stock = product.get('stock', 0)
        if available_stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {available_stock}, Requested: {quantity}")
        
        return {
            'product': product,
            'available_stock': available_stock,
            'unit_price': float(product.get('price', 0))
        }
    
    def format_cart_item(self, item_data: Dict[str, Any]) -> CartItem:
        """
        Format cart item data into CartItem model.
        
        Args:
            item_data: Raw cart item data from DynamoDB
            
        Returns:
            CartItem model instance
        """
        # Convert Decimal objects to float
        item_data = convert_decimals_to_float(item_data)
        
        # Calculate subtotal
        price = float(item_data.get('price', 0))
        quantity = int(item_data.get('quantity', 0))
        subtotal = price * quantity
        
        return CartItem(
            product_id=item_data.get('productId', ''),
            name=item_data.get('name', ''),
            price=price,
            quantity=quantity,
            subtotal=subtotal,
            image_url=item_data.get('imageUrl'),
            is_available=True,  # Will be validated separately
            stock_quantity=item_data.get('stock_quantity', 0),
            category=item_data.get('category'),
            sku=item_data.get('sku'),
            added_at=item_data.get('addedAt')
        )
    
    def calculate_cart_totals(self, items: List[CartItem]) -> Dict[str, float]:
        """
        Calculate cart totals including tax and shipping.
        
        Args:
            items: List of cart items
            
        Returns:
            Dictionary with subtotal, tax, shipping, and total
        """
        subtotal = sum(item.subtotal for item in items)
        
        # Calculate tax (8% rate - would be configurable in production)
        tax_rate = 0.08
        tax_amount = subtotal * tax_rate
        
        # Calculate shipping (free over $50, otherwise $5.99)
        shipping_cost = 0.0 if subtotal >= 50.0 else 5.99
        
        # Calculate total
        total_amount = subtotal + tax_amount + shipping_cost
        
        return {
            'subtotal': round(subtotal, 2),
            'tax': round(tax_amount, 2),
            'shipping': round(shipping_cost, 2),
            'total': round(total_amount, 2)
        }
    
    def validate_cart_items(self, cart_items: List[Dict[str, Any]]) -> tuple[List[CartItem], List[str]]:
        """
        Validate cart items against current product data.
        
        Args:
            cart_items: Raw cart item data from DynamoDB
            
        Returns:
            Tuple of (valid_items, validation_errors)
        """
        valid_items = []
        validation_errors = []
        
        for item in cart_items:
            product_id = item.get('productId')
            quantity = item.get('quantity', 0)
            
            try:
                # Validate product availability
                validation_result = self.validate_product_availability(product_id, quantity)
                product = validation_result['product']
                
                # Update item with current product data
                item['name'] = product['name']
                item['price'] = product['price']
                item['imageUrl'] = product.get('imageUrl', '')
                item['category'] = product.get('category')
                item['sku'] = product.get('sku')
                item['stock_quantity'] = product.get('stock', 0)
                
                # Format cart item
                cart_item = self.format_cart_item(item)
                valid_items.append(cart_item)
                
            except ValueError as e:
                validation_errors.append(f"Item {product_id}: {str(e)}")
                logger.warning(f"Cart item validation failed: {str(e)}")
        
        return valid_items, validation_errors


@tool
def add_to_cart(product_id: str, quantity: int = 1, user_id: Optional[str] = None) -> CartOperation:
    """
    Add a product to the user's shopping cart with validation and pricing.
    
    Args:
        product_id: ID of the product to add
        quantity: Quantity to add (default: 1)
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        CartOperation with updated cart state
    """
    logger.info(f"Adding to cart: product_id={product_id}, quantity={quantity}, user_id={user_id}")
    
    # Validate inputs
    if quantity <= 0:
        return CartOperation(
            operation=CartOperationType.ADD,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message="Quantity must be positive",
            cart_summary=CartSummary(
                user_id=user_id or "unknown",
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["Invalid quantity"]
            )
        )
    
    if not user_id:
        return CartOperation(
            operation=CartOperationType.ADD,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message="User authentication required",
            cart_summary=CartSummary(
                user_id="unknown",
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["User not authenticated"]
            )
        )
    
    try:
        # Initialize cart tool
        cart_tool = CartManagementTool(user_id)
        
        # Validate product availability
        validation_result = cart_tool.validate_product_availability(product_id, quantity)
        product = validation_result['product']
        
        current_time = int(time.time())
        
        # Check if item already exists in cart
        try:
            existing_response = get_cart_table().get_item(
                Key={'userId': user_id, 'productId': product_id}
            )
            
            if 'Item' in existing_response:
                # Update existing item quantity
                existing_item = existing_response['Item']
                new_quantity = existing_item['quantity'] + quantity
                
                # Validate total quantity against stock
                cart_tool.validate_product_availability(product_id, new_quantity)
                
                # Update item in cart
                get_cart_table().update_item(
                    Key={'userId': user_id, 'productId': product_id},
                    UpdateExpression="SET quantity = :quantity, updatedAt = :updated_at",
                    ExpressionAttributeValues={
                        ':quantity': new_quantity,
                        ':updated_at': current_time
                    }
                )
                
                message = f"Updated {product['name']} quantity to {new_quantity}"
                
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
                
                get_cart_table().put_item(Item=cart_item_data)
                
                message = f"Added {product['name']} to cart"
        
        except ClientError as e:
            logger.error(f"Failed to add item to cart: {str(e)}")
            return CartOperation(
                operation=CartOperationType.ADD,
                product_id=product_id,
                quantity=quantity,
                success=False,
                message=f"Failed to add item to cart: {str(e)}",
                cart_summary=CartSummary(
                    user_id=user_id,
                    items=[],
                    total_items=0,
                    subtotal=0.0,
                    tax=0.0,
                    total=0.0,
                    is_valid=False,
                    validation_errors=[f"Database error: {str(e)}"]
                )
            )
        
        # Get updated cart contents
        updated_cart = get_cart_contents(user_id)
        
        return CartOperation(
            operation=CartOperationType.ADD,
            product_id=product_id,
            quantity=quantity,
            success=True,
            message=message,
            cart_summary=updated_cart
        )
        
    except ValueError as e:
        logger.warning(f"Product validation failed: {str(e)}")
        return CartOperation(
            operation=CartOperationType.ADD,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message=str(e),
            cart_summary=CartSummary(
                user_id=user_id,
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=[str(e)]
            )
        )
    except Exception as e:
        logger.error(f"Unexpected error adding to cart: {str(e)}")
        return CartOperation(
            operation=CartOperationType.ADD,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message="An unexpected error occurred",
            cart_summary=CartSummary(
                user_id=user_id,
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["Unexpected error occurred"]
            )
        )


@tool
def get_cart_contents(user_id: Optional[str] = None) -> CartSummary:
    """
    Get current cart contents with real-time validation and pricing.
    
    Args:
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        CartSummary with current cart state
    """
    logger.info(f"Getting cart contents for user: {user_id}")
    
    if not user_id:
        return CartSummary(
            user_id="unknown",
            items=[],
            total_items=0,
            subtotal=0.0,
            tax=0.0,
            total=0.0,
            is_valid=False,
            validation_errors=["User authentication required"]
        )
    
    try:
        # Get cart items from DynamoDB
        response = get_cart_table().query(
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        
        cart_items = response.get('Items', [])
        
        if not cart_items:
            # Return empty cart
            return CartSummary(
                user_id=user_id,
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=True,
                validation_errors=[]
            )
        
        # Initialize cart tool for validation
        cart_tool = CartManagementTool(user_id)
        
        # Validate cart items against current product data
        valid_items, validation_errors = cart_tool.validate_cart_items(cart_items)
        
        # Calculate totals
        totals = cart_tool.calculate_cart_totals(valid_items)
        
        # Create cart summary
        cart_summary = CartSummary(
            user_id=user_id,
            items=valid_items,
            total_items=sum(item.quantity for item in valid_items),
            subtotal=totals['subtotal'],
            tax=totals['tax'],
            shipping=totals['shipping'],
            total=totals['total'],
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors
        )
        
        logger.info(f"Cart contents retrieved: {len(valid_items)} items, total ${totals['total']}")
        
        return cart_summary
        
    except ClientError as e:
        logger.error(f"Failed to get cart contents: {str(e)}")
        return CartSummary(
            user_id=user_id,
            items=[],
            total_items=0,
            subtotal=0.0,
            tax=0.0,
            total=0.0,
            is_valid=False,
            validation_errors=[f"Database error: {str(e)}"]
        )
    except Exception as e:
        logger.error(f"Unexpected error getting cart contents: {str(e)}")
        return CartSummary(
            user_id=user_id,
            items=[],
            total_items=0,
            subtotal=0.0,
            tax=0.0,
            total=0.0,
            is_valid=False,
            validation_errors=["Unexpected error occurred"]
        )


@tool
def update_cart_item(product_id: str, quantity: int, user_id: Optional[str] = None) -> CartOperation:
    """
    Update the quantity of an item in the cart.
    
    Args:
        product_id: ID of the product to update
        quantity: New quantity (must be positive)
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        CartOperation with updated cart state
    """
    logger.info(f"Updating cart item: product_id={product_id}, quantity={quantity}, user_id={user_id}")
    
    # Validate inputs
    if quantity <= 0:
        return remove_from_cart(product_id, user_id)
    
    if not user_id:
        return CartOperation(
            operation=CartOperationType.UPDATE,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message="User authentication required",
            cart_summary=CartSummary(
                user_id="unknown",
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["User not authenticated"]
            )
        )
    
    try:
        # Initialize cart tool
        cart_tool = CartManagementTool(user_id)
        
        # Validate product availability for new quantity
        validation_result = cart_tool.validate_product_availability(product_id, quantity)
        product = validation_result['product']
        
        current_time = int(time.time())
        
        # Update item in cart
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
        
        if 'Attributes' not in response:
            return CartOperation(
                operation=CartOperationType.UPDATE,
                product_id=product_id,
                quantity=quantity,
                success=False,
                message="Item not found in cart",
                cart_summary=get_cart_contents(user_id)
            )
        
        # Get updated cart contents
        updated_cart = get_cart_contents(user_id)
        
        return CartOperation(
            operation=CartOperationType.UPDATE,
            product_id=product_id,
            quantity=quantity,
            success=True,
            message=f"Updated {product['name']} quantity to {quantity}",
            cart_summary=updated_cart
        )
        
    except ValueError as e:
        logger.warning(f"Product validation failed: {str(e)}")
        return CartOperation(
            operation=CartOperationType.UPDATE,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message=str(e),
            cart_summary=get_cart_contents(user_id)
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return CartOperation(
                operation=CartOperationType.UPDATE,
                product_id=product_id,
                quantity=quantity,
                success=False,
                message="Item not found in cart",
                cart_summary=get_cart_contents(user_id)
            )
        
        logger.error(f"Failed to update cart item: {str(e)}")
        return CartOperation(
            operation=CartOperationType.UPDATE,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message=f"Failed to update item: {str(e)}",
            cart_summary=get_cart_contents(user_id)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating cart item: {str(e)}")
        return CartOperation(
            operation=CartOperationType.UPDATE,
            product_id=product_id,
            quantity=quantity,
            success=False,
            message="An unexpected error occurred",
            cart_summary=get_cart_contents(user_id)
        )


@tool
def remove_from_cart(product_id: str, user_id: Optional[str] = None) -> CartOperation:
    """
    Remove an item from the cart.
    
    Args:
        product_id: ID of the product to remove
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        CartOperation with updated cart state
    """
    logger.info(f"Removing from cart: product_id={product_id}, user_id={user_id}")
    
    if not user_id:
        return CartOperation(
            operation=CartOperationType.REMOVE,
            product_id=product_id,
            success=False,
            message="User authentication required",
            cart_summary=CartSummary(
                user_id="unknown",
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["User not authenticated"]
            )
        )
    
    try:
        # Remove item from cart
        response = get_cart_table().delete_item(
            Key={'userId': user_id, 'productId': product_id},
            ConditionExpression=Attr('userId').exists() & Attr('productId').exists(),
            ReturnValues='ALL_OLD'
        )
        
        if 'Attributes' not in response:
            return CartOperation(
                operation=CartOperationType.REMOVE,
                product_id=product_id,
                success=False,
                message="Item not found in cart",
                cart_summary=get_cart_contents(user_id)
            )
        
        removed_item = response['Attributes']
        product_name = removed_item.get('name', 'Unknown Product')
        
        # Get updated cart contents
        updated_cart = get_cart_contents(user_id)
        
        return CartOperation(
            operation=CartOperationType.REMOVE,
            product_id=product_id,
            success=True,
            message=f"Removed {product_name} from cart",
            cart_summary=updated_cart
        )
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return CartOperation(
                operation=CartOperationType.REMOVE,
                product_id=product_id,
                success=False,
                message="Item not found in cart",
                cart_summary=get_cart_contents(user_id)
            )
        
        logger.error(f"Failed to remove cart item: {str(e)}")
        return CartOperation(
            operation=CartOperationType.REMOVE,
            product_id=product_id,
            success=False,
            message=f"Failed to remove item: {str(e)}",
            cart_summary=get_cart_contents(user_id)
        )
    except Exception as e:
        logger.error(f"Unexpected error removing cart item: {str(e)}")
        return CartOperation(
            operation=CartOperationType.REMOVE,
            product_id=product_id,
            success=False,
            message="An unexpected error occurred",
            cart_summary=get_cart_contents(user_id)
        )


@tool
def clear_cart(user_id: Optional[str] = None) -> CartOperation:
    """
    Clear all items from the user's cart.
    
    Args:
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        CartOperation with cleared cart state
    """
    logger.info(f"Clearing cart for user: {user_id}")
    
    if not user_id:
        return CartOperation(
            operation=CartOperationType.CLEAR,
            success=False,
            message="User authentication required",
            cart_summary=CartSummary(
                user_id="unknown",
                items=[],
                total_items=0,
                subtotal=0.0,
                tax=0.0,
                total=0.0,
                is_valid=False,
                validation_errors=["User not authenticated"]
            )
        )
    
    try:
        # Get all cart items first
        response = get_cart_table().query(
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        
        cart_items = response.get('Items', [])
        
        if not cart_items:
            return CartOperation(
                operation=CartOperationType.CLEAR,
                success=True,
                message="Cart is already empty",
                cart_summary=CartSummary(
                    user_id=user_id,
                    items=[],
                    total_items=0,
                    subtotal=0.0,
                    tax=0.0,
                    total=0.0,
                    is_valid=True,
                    validation_errors=[]
                )
            )
        
        # Delete all items
        with get_cart_table().batch_writer() as batch:
            for item in cart_items:
                batch.delete_item(
                    Key={
                        'userId': item['userId'],
                        'productId': item['productId']
                    }
                )
        
        # Return cleared cart summary
        cleared_cart = CartSummary(
            user_id=user_id,
            items=[],
            total_items=0,
            subtotal=0.0,
            tax=0.0,
            total=0.0,
            is_valid=True,
            validation_errors=[]
        )
        
        return CartOperation(
            operation=CartOperationType.CLEAR,
            success=True,
            message=f"Cleared {len(cart_items)} items from cart",
            cart_summary=cleared_cart
        )
        
    except ClientError as e:
        logger.error(f"Failed to clear cart: {str(e)}")
        return CartOperation(
            operation=CartOperationType.CLEAR,
            success=False,
            message=f"Failed to clear cart: {str(e)}",
            cart_summary=get_cart_contents(user_id)
        )
    except Exception as e:
        logger.error(f"Unexpected error clearing cart: {str(e)}")
        return CartOperation(
            operation=CartOperationType.CLEAR,
            success=False,
            message="An unexpected error occurred",
            cart_summary=get_cart_contents(user_id)
        )