"""
Order Query Tool for Strands AI Agent

This tool enables the Strands agent to retrieve order information including
order history, order details, and tracking information with proper
authentication and authorization.
"""

# CRITICAL: Apply OpenTelemetry fix BEFORE any other imports
import otel_emergency_fix  # Embedded fix that doesn't depend on layers

import json
import os
import logging
import base64
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from strands import tool
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import OrderHistory, OrderInfo, OrderItem, OrderTracking, OrderStatus

# Initialize logger
logger = logging.getLogger(__name__)

# Environment variables
ORDERS_TABLE_NAME = os.environ.get("ORDERS_TABLE_NAME", "")

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
orders_table = None


def get_orders_table():
    """Get orders table with lazy initialization"""
    global orders_table
    if orders_table is None:
        orders_table = dynamodb.Table(ORDERS_TABLE_NAME)
    return orders_table


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


def format_timestamp(timestamp: int) -> str:
    """Format Unix timestamp to readable string"""
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return "Unknown"


class OrderQueryTool:
    """Order query tool for Strands agent"""
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize the order query tool with user ID"""
        self.user_id = user_id
    
    def format_order_item(self, item_data: Dict[str, Any]) -> OrderItem:
        """
        Format order item data into OrderItem model.
        
        Args:
            item_data: Raw order item data
            
        Returns:
            OrderItem model instance
        """
        # Convert Decimal objects to float
        item_data = convert_decimals_to_float(item_data)
        
        return OrderItem(
            product_id=item_data.get('productId', ''),
            name=item_data.get('name', ''),
            price=float(item_data.get('price', 0)),
            quantity=int(item_data.get('quantity', 0)),
            subtotal=float(item_data.get('subtotal', 0)),
            sku=item_data.get('sku'),
            category=item_data.get('category')
        )
    
    def format_order_info(self, order_data: Dict[str, Any]) -> OrderInfo:
        """
        Format order data into OrderInfo model.
        
        Args:
            order_data: Raw order data from DynamoDB
            
        Returns:
            OrderInfo model instance
        """
        # Convert Decimal objects to float
        order_data = convert_decimals_to_float(order_data)
        
        # Format order items
        items_data = order_data.get('items', [])
        items = [self.format_order_item(item) for item in items_data]
        
        # Parse timestamps
        order_date = datetime.fromtimestamp(order_data.get('createdAt', 0))
        
        estimated_delivery = None
        if order_data.get('estimatedDelivery'):
            try:
                estimated_delivery = datetime.fromtimestamp(order_data['estimatedDelivery'])
            except (ValueError, TypeError):
                pass
        
        actual_delivery = None
        if order_data.get('actualDelivery'):
            try:
                actual_delivery = datetime.fromtimestamp(order_data['actualDelivery'])
            except (ValueError, TypeError):
                pass
        
        # Parse order status
        status_str = order_data.get('status', 'pending')
        try:
            status = OrderStatus(status_str)
        except ValueError:
            status = OrderStatus.PENDING
        
        return OrderInfo(
            order_id=order_data.get('orderId', ''),
            user_id=order_data.get('userId', ''),
            status=status,
            items=items,
            subtotal=float(order_data.get('subtotal', 0)),
            tax=float(order_data.get('taxAmount', 0)),
            shipping=float(order_data.get('shippingCost', 0)),
            discount=float(order_data.get('discount', 0)),
            total_amount=float(order_data.get('totalAmount', 0)),
            currency=order_data.get('currency', 'USD'),
            order_date=order_date,
            estimated_delivery=estimated_delivery,
            actual_delivery=actual_delivery,
            tracking_number=order_data.get('trackingNumber'),
            shipping_address=order_data.get('shippingAddress', {}),
            billing_address=order_data.get('billingAddress'),
            payment_method=order_data.get('paymentMethod', 'Unknown'),
            payment_status=order_data.get('paymentStatus', 'pending')
        )
    
    def validate_user_access(self, order_data: Dict[str, Any], user_id: str) -> bool:
        """
        Validate that the user has access to the order.
        
        Args:
            order_data: Order data from database
            user_id: Requesting user ID
            
        Returns:
            True if user has access, False otherwise
        """
        order_user_id = order_data.get('userId')
        return order_user_id == user_id


@tool
def get_order_history(user_id: Optional[str] = None, limit: int = 10, 
                     next_token: Optional[str] = None) -> OrderHistory:
    """
    Get user's order history with pagination.
    
    Args:
        user_id: User identifier (optional, can be extracted from context)
        limit: Maximum number of orders to return (default: 10, max: 50)
        next_token: Pagination token for next page
        
    Returns:
        OrderHistory with user's orders and pagination info
    """
    logger.info(f"Getting order history: user_id={user_id}, limit={limit}")
    
    # Validate inputs
    if limit > 50:
        limit = 50
    if limit < 1:
        limit = 1
    
    if not user_id:
        return OrderHistory(
            user_id="unknown",
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )
    
    try:
        # Initialize order tool
        order_tool = OrderQueryTool(user_id)
        
        # Build query parameters
        query_params = {
            'IndexName': 'userId-timestamp-index',
            'KeyConditionExpression': Key('userId').eq(user_id),
            'ScanIndexForward': False,  # Sort by timestamp descending (newest first)
            'Limit': limit
        }
        
        # Add pagination token if provided
        if next_token:
            try:
                decoded_key = json.loads(base64.b64decode(next_token).decode('utf-8'))
                query_params['ExclusiveStartKey'] = decoded_key
            except Exception as e:
                logger.warning(f"Invalid pagination token: {str(e)}")
                # Continue without pagination token
        
        # Execute query
        response = get_orders_table().query(**query_params)
        
        orders_data = response.get('Items', [])
        
        # Format orders
        orders = []
        total_spent = 0.0
        
        for order_data in orders_data:
            try:
                order_info = order_tool.format_order_info(order_data)
                orders.append(order_info)
                total_spent += order_info.total_amount
            except Exception as e:
                logger.warning(f"Failed to format order {order_data.get('orderId', 'unknown')}: {str(e)}")
                continue
        
        # Create next token if more results available
        has_more = 'LastEvaluatedKey' in response
        next_page_token = None
        if has_more:
            try:
                next_page_token = base64.b64encode(
                    json.dumps(response['LastEvaluatedKey'], default=str).encode('utf-8')
                ).decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to create pagination token: {str(e)}")
                has_more = False
        
        # Calculate page number (approximate)
        page = 1
        if next_token:
            page = 2  # Simplified page calculation
        
        order_history = OrderHistory(
            user_id=user_id,
            orders=orders,
            total_orders=len(orders),  # This is just the current page count
            page=page,
            page_size=limit,
            has_more=has_more,
            total_spent=round(total_spent, 2)
        )
        
        logger.info(f"Order history retrieved: {len(orders)} orders, total spent ${total_spent:.2f}")
        
        return order_history
        
    except ClientError as e:
        logger.error(f"Failed to get order history: {str(e)}")
        return OrderHistory(
            user_id=user_id,
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )
    except Exception as e:
        logger.error(f"Unexpected error getting order history: {str(e)}")
        return OrderHistory(
            user_id=user_id,
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )


@tool
def get_order_details(order_id: str, user_id: Optional[str] = None) -> Optional[OrderInfo]:
    """
    Get detailed information about a specific order.
    
    Args:
        order_id: ID of the order to retrieve
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        OrderInfo with detailed order information, or None if not found/unauthorized
    """
    logger.info(f"Getting order details: order_id={order_id}, user_id={user_id}")
    
    if not user_id:
        logger.warning("User ID required for order details")
        return None
    
    try:
        # Get order from database
        response = get_orders_table().get_item(Key={'orderId': order_id})
        
        if 'Item' not in response:
            logger.warning(f"Order not found: {order_id}")
            return None
        
        order_data = response['Item']
        
        # Initialize order tool
        order_tool = OrderQueryTool(user_id)
        
        # Validate user access
        if not order_tool.validate_user_access(order_data, user_id):
            logger.warning(f"Unauthorized access attempt: user {user_id} trying to access order {order_id}")
            return None
        
        # Format and return order info
        order_info = order_tool.format_order_info(order_data)
        
        logger.info(f"Order details retrieved: {order_id}")
        return order_info
        
    except ClientError as e:
        logger.error(f"Failed to get order details for {order_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting order details for {order_id}: {str(e)}")
        return None


@tool
def track_order(order_id: str, user_id: Optional[str] = None) -> Optional[OrderTracking]:
    """
    Get tracking information for an order.
    
    Args:
        order_id: ID of the order to track
        user_id: User identifier (optional, can be extracted from context)
        
    Returns:
        OrderTracking with tracking information, or None if not found/unauthorized
    """
    logger.info(f"Tracking order: order_id={order_id}, user_id={user_id}")
    
    if not user_id:
        logger.warning("User ID required for order tracking")
        return None
    
    try:
        # Get order details first
        order_info = get_order_details(order_id, user_id)
        
        if not order_info:
            return None
        
        # Create status history (simplified - in production this would come from a separate table)
        status_history = []
        
        # Add order creation
        status_history.append({
            "status": "pending",
            "timestamp": order_info.order_date,
            "notes": "Order placed successfully"
        })
        
        # Add current status if different from pending
        if order_info.status != OrderStatus.PENDING:
            status_history.append({
                "status": order_info.status.value,
                "timestamp": datetime.utcnow(),  # In production, this would be the actual status change time
                "notes": f"Order status updated to {order_info.status.value}"
            })
        
        # Generate tracking URL if tracking number exists
        tracking_url = None
        carrier = None
        current_location = None
        
        if order_info.tracking_number:
            # In production, this would determine the carrier and generate appropriate URLs
            carrier = "Standard Shipping"
            tracking_url = f"https://tracking.example.com/{order_info.tracking_number}"
            
            # Mock current location based on status
            if order_info.status == OrderStatus.SHIPPED:
                current_location = "In transit to destination"
            elif order_info.status == OrderStatus.DELIVERED:
                current_location = "Delivered"
            else:
                current_location = "Processing at fulfillment center"
        
        tracking_info = OrderTracking(
            order_id=order_id,
            current_status=order_info.status,
            tracking_number=order_info.tracking_number,
            estimated_delivery=order_info.estimated_delivery,
            actual_delivery=order_info.actual_delivery,
            status_history=status_history,
            carrier=carrier,
            tracking_url=tracking_url,
            current_location=current_location
        )
        
        logger.info(f"Order tracking retrieved: {order_id}")
        return tracking_info
        
    except Exception as e:
        logger.error(f"Unexpected error tracking order {order_id}: {str(e)}")
        return None


@tool
def search_orders(user_id: Optional[str] = None, status_filter: Optional[str] = None,
                 date_from: Optional[str] = None, date_to: Optional[str] = None,
                 limit: int = 10) -> OrderHistory:
    """
    Search and filter user orders by various criteria.
    
    Args:
        user_id: User identifier (optional, can be extracted from context)
        status_filter: Filter by order status (e.g., "pending", "shipped", "delivered")
        date_from: Start date for filtering (ISO format: YYYY-MM-DD)
        date_to: End date for filtering (ISO format: YYYY-MM-DD)
        limit: Maximum number of results (default: 10, max: 50)
        
    Returns:
        OrderHistory with filtered orders
    """
    logger.info(f"Searching orders: user_id={user_id}, status={status_filter}, date_from={date_from}, date_to={date_to}")
    
    # Validate inputs
    if limit > 50:
        limit = 50
    if limit < 1:
        limit = 1
    
    if not user_id:
        return OrderHistory(
            user_id="unknown",
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )
    
    try:
        # Initialize order tool
        order_tool = OrderQueryTool(user_id)
        
        # Build filter expressions
        filter_expressions = []
        expression_values = {}
        expression_names = {}
        
        # Status filter
        if status_filter:
            filter_expressions.append("#status = :status")
            expression_names['#status'] = 'status'
            expression_values[':status'] = status_filter
        
        # Date filters (convert to timestamps)
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                date_from_ts = int(date_from_dt.timestamp())
                filter_expressions.append("#createdAt >= :date_from")
                expression_names['#createdAt'] = 'createdAt'
                expression_values[':date_from'] = date_from_ts
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                # Set to end of day
                date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)
                date_to_ts = int(date_to_dt.timestamp())
                filter_expressions.append("#createdAt <= :date_to")
                expression_names['#createdAt'] = 'createdAt'
                expression_values[':date_to'] = date_to_ts
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        # Build query parameters
        query_params = {
            'IndexName': 'userId-timestamp-index',
            'KeyConditionExpression': Key('userId').eq(user_id),
            'ScanIndexForward': False,  # Sort by timestamp descending
            'Limit': limit
        }
        
        # Add filter expression if any filters are applied
        if filter_expressions:
            query_params['FilterExpression'] = ' AND '.join(filter_expressions)
            if expression_names:
                query_params['ExpressionAttributeNames'] = expression_names
            if expression_values:
                query_params['ExpressionAttributeValues'] = expression_values
        
        # Execute query
        response = get_orders_table().query(**query_params)
        
        orders_data = response.get('Items', [])
        
        # Format orders
        orders = []
        total_spent = 0.0
        
        for order_data in orders_data:
            try:
                order_info = order_tool.format_order_info(order_data)
                orders.append(order_info)
                total_spent += order_info.total_amount
            except Exception as e:
                logger.warning(f"Failed to format order {order_data.get('orderId', 'unknown')}: {str(e)}")
                continue
        
        # Check if more results available
        has_more = 'LastEvaluatedKey' in response
        
        order_history = OrderHistory(
            user_id=user_id,
            orders=orders,
            total_orders=len(orders),
            page=1,
            page_size=limit,
            has_more=has_more,
            total_spent=round(total_spent, 2)
        )
        
        logger.info(f"Order search completed: {len(orders)} orders found")
        
        return order_history
        
    except ClientError as e:
        logger.error(f"Failed to search orders: {str(e)}")
        return OrderHistory(
            user_id=user_id,
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )
    except Exception as e:
        logger.error(f"Unexpected error searching orders: {str(e)}")
        return OrderHistory(
            user_id=user_id,
            orders=[],
            total_orders=0,
            page=1,
            page_size=limit,
            has_more=False,
            total_spent=0.0
        )