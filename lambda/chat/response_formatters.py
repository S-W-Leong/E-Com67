"""
Response Formatting Utilities for Strands AI Agent

This module provides utility functions to convert API responses to Pydantic models,
format responses for WebSocket communication, and handle error standardization.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from decimal import Decimal

from .models import (
    # Product models
    ProductInfo, ProductRecommendation, ProductSearchResponse,
    # Cart models
    CartItem, CartSummary, CartOperation, CartOperationType,
    # Order models
    OrderItem, OrderInfo, OrderHistory, OrderTracking, OrderStatus, OrderStatusUpdate,
    # Agent response models
    AgentResponse, ErrorResponse, ToolResult, ResponseType, ErrorType,
    # Knowledge models
    KnowledgeSource, KnowledgeResponse,
    # WebSocket models
    WebSocketMessage, WebSocketMessageType,
    # Utility models
    PaginationInfo, SearchFilters
)

logger = logging.getLogger(__name__)


# ============================================================================
# Product Response Formatters
# ============================================================================

def format_product_info(product_data: Dict[str, Any]) -> ProductInfo:
    """
    Convert raw product data from DynamoDB/API to ProductInfo model.
    
    Args:
        product_data: Raw product data dictionary
        
    Returns:
        ProductInfo: Validated product information model
    """
    try:
        # Handle DynamoDB Decimal types
        if isinstance(product_data.get('price'), Decimal):
            product_data['price'] = float(product_data['price'])
        
        # Ensure required fields have defaults
        formatted_data = {
            'product_id': product_data.get('productId', product_data.get('id', '')),
            'name': product_data.get('name', ''),
            'description': product_data.get('description', ''),
            'price': product_data.get('price', 0.0),
            'currency': product_data.get('currency', 'USD'),
            'category': product_data.get('category', 'Uncategorized'),
            'stock': int(product_data.get('stock', 0)),
            'image_url': product_data.get('imageUrl', product_data.get('image')),
            'rating': product_data.get('rating'),
            'tags': product_data.get('tags', []),
            'is_available': product_data.get('isAvailable', product_data.get('stock', 0) > 0),
            'specifications': product_data.get('specifications', {}),
            'brand': product_data.get('brand'),
            'sku': product_data.get('sku', product_data.get('productId'))
        }
        
        return ProductInfo(**formatted_data)
        
    except Exception as e:
        logger.error(f"Error formatting product info: {str(e)}")
        logger.error(f"Product data: {product_data}")
        raise ValueError(f"Invalid product data: {str(e)}")


def format_product_search_response(
    query: str,
    search_results: List[Dict[str, Any]],
    total_count: int = None,
    page: int = 1,
    page_size: int = 10,
    suggestions: List[str] = None,
    filters: Dict[str, Any] = None,
    search_time_ms: int = None
) -> ProductSearchResponse:
    """
    Format product search results into structured response.
    
    Args:
        query: Original search query
        search_results: List of raw product data
        total_count: Total number of matching products
        page: Current page number
        page_size: Items per page
        suggestions: Alternative search suggestions
        filters: Applied search filters
        search_time_ms: Search execution time
        
    Returns:
        ProductSearchResponse: Structured search response
    """
    try:
        # Format individual products
        products = [format_product_info(product) for product in search_results]
        
        # Calculate total count if not provided
        if total_count is None:
            total_count = len(products)
        
        # Determine if more results are available
        has_more = (page * page_size) < total_count
        
        return ProductSearchResponse(
            query=query,
            products=products,
            total_count=total_count,
            page=page,
            page_size=page_size,
            suggestions=suggestions or [],
            filters_applied=filters or {},
            search_time_ms=search_time_ms,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error formatting search response: {str(e)}")
        raise ValueError(f"Invalid search response data: {str(e)}")


def format_product_recommendations(
    products: List[Dict[str, Any]],
    query_context: str = "",
    user_preferences: Dict[str, Any] = None
) -> List[ProductRecommendation]:
    """
    Format product recommendations with reasoning and scoring.
    
    Args:
        products: List of recommended products with scores
        query_context: Original user query for context
        user_preferences: User preference data
        
    Returns:
        List[ProductRecommendation]: Formatted recommendations
    """
    try:
        recommendations = []
        
        for product_data in products:
            # Extract recommendation metadata
            relevance_score = product_data.get('relevance_score', 0.5)
            reasoning = product_data.get('reasoning', 'Recommended based on your search')
            
            # Format the product info
            product_info = format_product_info(product_data)
            
            # Determine match factors
            category_match = _check_category_match(product_data, query_context)
            price_match = _check_price_match(product_data, user_preferences)
            
            # Generate similarity factors
            similarity_factors = _generate_similarity_factors(product_data, query_context)
            
            # Determine confidence level
            confidence_level = _calculate_confidence_level(relevance_score)
            
            recommendation = ProductRecommendation(
                product=product_info,
                relevance_score=relevance_score,
                reasoning=reasoning,
                category_match=category_match,
                price_match=price_match,
                similarity_factors=similarity_factors,
                confidence_level=confidence_level
            )
            
            recommendations.append(recommendation)
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error formatting recommendations: {str(e)}")
        raise ValueError(f"Invalid recommendation data: {str(e)}")


# ============================================================================
# Cart Response Formatters
# ============================================================================

def format_cart_item(item_data: Dict[str, Any]) -> CartItem:
    """
    Convert raw cart item data to CartItem model.
    
    Args:
        item_data: Raw cart item data
        
    Returns:
        CartItem: Validated cart item model
    """
    try:
        # Handle DynamoDB Decimal types
        if isinstance(item_data.get('price'), Decimal):
            item_data['price'] = float(item_data['price'])
        if isinstance(item_data.get('subtotal'), Decimal):
            item_data['subtotal'] = float(item_data['subtotal'])
        
        # Parse added_at timestamp if it's a string
        added_at = item_data.get('addedAt', item_data.get('added_at'))
        if isinstance(added_at, str):
            added_at = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
        elif added_at is None:
            added_at = datetime.utcnow()
        
        formatted_data = {
            'product_id': item_data.get('productId', item_data.get('product_id', '')),
            'name': item_data.get('name', ''),
            'price': item_data.get('price', 0.0),
            'quantity': int(item_data.get('quantity', 1)),
            'subtotal': item_data.get('subtotal', item_data.get('price', 0) * item_data.get('quantity', 1)),
            'image_url': item_data.get('imageUrl', item_data.get('image_url')),
            'is_available': item_data.get('isAvailable', True),
            'stock_quantity': int(item_data.get('stockQuantity', item_data.get('stock', 0))),
            'category': item_data.get('category'),
            'sku': item_data.get('sku'),
            'added_at': added_at
        }
        
        return CartItem(**formatted_data)
        
    except Exception as e:
        logger.error(f"Error formatting cart item: {str(e)}")
        logger.error(f"Item data: {item_data}")
        raise ValueError(f"Invalid cart item data: {str(e)}")


def format_cart_summary(cart_data: Dict[str, Any]) -> CartSummary:
    """
    Convert raw cart data to CartSummary model.
    
    Args:
        cart_data: Raw cart data from API
        
    Returns:
        CartSummary: Validated cart summary model
    """
    try:
        # Handle DynamoDB Decimal types for monetary values
        for field in ['subtotal', 'tax', 'shipping', 'discount', 'total']:
            if isinstance(cart_data.get(field), Decimal):
                cart_data[field] = float(cart_data[field])
        
        # Format cart items
        items_data = cart_data.get('items', [])
        items = [format_cart_item(item) for item in items_data]
        
        # Calculate totals if not provided
        calculated_subtotal = sum(item.subtotal for item in items)
        calculated_total_items = sum(item.quantity for item in items)
        
        # Parse last_updated timestamp
        last_updated = cart_data.get('lastUpdated', cart_data.get('last_updated'))
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        elif last_updated is None:
            last_updated = datetime.utcnow()
        
        # Parse estimated delivery
        estimated_delivery = cart_data.get('estimatedDelivery')
        if isinstance(estimated_delivery, str):
            estimated_delivery = datetime.fromisoformat(estimated_delivery.replace('Z', '+00:00'))
        
        formatted_data = {
            'user_id': cart_data.get('userId', cart_data.get('user_id', '')),
            'items': items,
            'total_items': cart_data.get('totalItems', calculated_total_items),
            'subtotal': cart_data.get('subtotal', calculated_subtotal),
            'tax': cart_data.get('tax', 0.0),
            'shipping': cart_data.get('shipping', 0.0),
            'discount': cart_data.get('discount', 0.0),
            'total': cart_data.get('total', calculated_subtotal),
            'currency': cart_data.get('currency', 'USD'),
            'last_updated': last_updated,
            'is_valid': cart_data.get('isValid', True),
            'validation_errors': cart_data.get('validationErrors', []),
            'estimated_delivery': estimated_delivery
        }
        
        return CartSummary(**formatted_data)
        
    except Exception as e:
        logger.error(f"Error formatting cart summary: {str(e)}")
        logger.error(f"Cart data: {cart_data}")
        raise ValueError(f"Invalid cart data: {str(e)}")


def format_cart_operation(
    operation_type: str,
    product_id: str,
    quantity: Optional[int],
    success: bool,
    message: str,
    cart_data: Dict[str, Any]
) -> CartOperation:
    """
    Format cart operation result.
    
    Args:
        operation_type: Type of operation performed
        product_id: Target product ID
        quantity: New quantity (for add/update operations)
        success: Whether operation succeeded
        message: Result message
        cart_data: Updated cart data
        
    Returns:
        CartOperation: Formatted operation result
    """
    try:
        cart_summary = format_cart_summary(cart_data)
        
        return CartOperation(
            operation=CartOperationType(operation_type.lower()),
            product_id=product_id,
            quantity=quantity,
            success=success,
            message=message,
            cart_summary=cart_summary
        )
        
    except Exception as e:
        logger.error(f"Error formatting cart operation: {str(e)}")
        raise ValueError(f"Invalid cart operation data: {str(e)}")


# ============================================================================
# Order Response Formatters
# ============================================================================

def format_order_item(item_data: Dict[str, Any]) -> OrderItem:
    """
    Convert raw order item data to OrderItem model.
    
    Args:
        item_data: Raw order item data
        
    Returns:
        OrderItem: Validated order item model
    """
    try:
        # Handle DynamoDB Decimal types
        if isinstance(item_data.get('price'), Decimal):
            item_data['price'] = float(item_data['price'])
        if isinstance(item_data.get('subtotal'), Decimal):
            item_data['subtotal'] = float(item_data['subtotal'])
        
        formatted_data = {
            'product_id': item_data.get('productId', item_data.get('product_id', '')),
            'name': item_data.get('name', ''),
            'price': item_data.get('price', 0.0),
            'quantity': int(item_data.get('quantity', 1)),
            'subtotal': item_data.get('subtotal', item_data.get('price', 0) * item_data.get('quantity', 1)),
            'sku': item_data.get('sku'),
            'category': item_data.get('category')
        }
        
        return OrderItem(**formatted_data)
        
    except Exception as e:
        logger.error(f"Error formatting order item: {str(e)}")
        raise ValueError(f"Invalid order item data: {str(e)}")


def format_order_info(order_data: Dict[str, Any]) -> OrderInfo:
    """
    Convert raw order data to OrderInfo model.
    
    Args:
        order_data: Raw order data from API
        
    Returns:
        OrderInfo: Validated order information model
    """
    try:
        # Handle DynamoDB Decimal types for monetary values
        for field in ['subtotal', 'tax', 'shipping', 'discount', 'totalAmount', 'total_amount']:
            if isinstance(order_data.get(field), Decimal):
                order_data[field] = float(order_data[field])
        
        # Format order items
        items_data = order_data.get('items', [])
        items = [format_order_item(item) for item in items_data]
        
        # Parse timestamps
        order_date = order_data.get('orderDate', order_data.get('order_date'))
        if isinstance(order_date, str):
            order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
        elif order_date is None:
            order_date = datetime.utcnow()
        
        estimated_delivery = order_data.get('estimatedDelivery', order_data.get('estimated_delivery'))
        if isinstance(estimated_delivery, str):
            estimated_delivery = datetime.fromisoformat(estimated_delivery.replace('Z', '+00:00'))
        
        actual_delivery = order_data.get('actualDelivery', order_data.get('actual_delivery'))
        if isinstance(actual_delivery, str):
            actual_delivery = datetime.fromisoformat(actual_delivery.replace('Z', '+00:00'))
        
        # Handle status enum
        status = order_data.get('status', 'pending').lower()
        if status not in [s.value for s in OrderStatus]:
            status = 'pending'
        
        formatted_data = {
            'order_id': order_data.get('orderId', order_data.get('order_id', '')),
            'user_id': order_data.get('userId', order_data.get('user_id', '')),
            'status': OrderStatus(status),
            'items': items,
            'subtotal': order_data.get('subtotal', 0.0),
            'tax': order_data.get('tax', 0.0),
            'shipping': order_data.get('shipping', 0.0),
            'discount': order_data.get('discount', 0.0),
            'total_amount': order_data.get('totalAmount', order_data.get('total_amount', 0.0)),
            'currency': order_data.get('currency', 'USD'),
            'order_date': order_date,
            'estimated_delivery': estimated_delivery,
            'actual_delivery': actual_delivery,
            'tracking_number': order_data.get('trackingNumber', order_data.get('tracking_number')),
            'shipping_address': order_data.get('shippingAddress', order_data.get('shipping_address', {})),
            'billing_address': order_data.get('billingAddress', order_data.get('billing_address')),
            'payment_method': order_data.get('paymentMethod', order_data.get('payment_method', 'unknown')),
            'payment_status': order_data.get('paymentStatus', order_data.get('payment_status', 'pending'))
        }
        
        return OrderInfo(**formatted_data)
        
    except Exception as e:
        logger.error(f"Error formatting order info: {str(e)}")
        logger.error(f"Order data: {order_data}")
        raise ValueError(f"Invalid order data: {str(e)}")


def format_order_history(
    user_id: str,
    orders_data: List[Dict[str, Any]],
    total_orders: int = None,
    page: int = 1,
    page_size: int = 10
) -> OrderHistory:
    """
    Format order history response.
    
    Args:
        user_id: User identifier
        orders_data: List of raw order data
        total_orders: Total number of orders for user
        page: Current page number
        page_size: Items per page
        
    Returns:
        OrderHistory: Formatted order history
    """
    try:
        # Format individual orders
        orders = [format_order_info(order) for order in orders_data]
        
        # Calculate total orders if not provided
        if total_orders is None:
            total_orders = len(orders)
        
        # Calculate total spent
        total_spent = sum(order.total_amount for order in orders)
        
        # Determine if more pages exist
        has_more = (page * page_size) < total_orders
        
        return OrderHistory(
            user_id=user_id,
            orders=orders,
            total_orders=total_orders,
            page=page,
            page_size=page_size,
            has_more=has_more,
            total_spent=total_spent
        )
        
    except Exception as e:
        logger.error(f"Error formatting order history: {str(e)}")
        raise ValueError(f"Invalid order history data: {str(e)}")


def format_order_tracking(tracking_data: Dict[str, Any]) -> OrderTracking:
    """
    Format order tracking information.
    
    Args:
        tracking_data: Raw tracking data
        
    Returns:
        OrderTracking: Formatted tracking information
    """
    try:
        # Parse timestamps in status history
        status_history = []
        for update in tracking_data.get('statusHistory', []):
            timestamp = update.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif timestamp is None:
                timestamp = datetime.utcnow()
            
            status_update = OrderStatusUpdate(
                status=OrderStatus(update.get('status', 'pending').lower()),
                timestamp=timestamp,
                notes=update.get('notes'),
                location=update.get('location')
            )
            status_history.append(status_update)
        
        # Parse delivery dates
        estimated_delivery = tracking_data.get('estimatedDelivery')
        if isinstance(estimated_delivery, str):
            estimated_delivery = datetime.fromisoformat(estimated_delivery.replace('Z', '+00:00'))
        
        actual_delivery = tracking_data.get('actualDelivery')
        if isinstance(actual_delivery, str):
            actual_delivery = datetime.fromisoformat(actual_delivery.replace('Z', '+00:00'))
        
        return OrderTracking(
            order_id=tracking_data.get('orderId', tracking_data.get('order_id', '')),
            current_status=OrderStatus(tracking_data.get('currentStatus', 'pending').lower()),
            tracking_number=tracking_data.get('trackingNumber'),
            estimated_delivery=estimated_delivery,
            actual_delivery=actual_delivery,
            status_history=status_history,
            carrier=tracking_data.get('carrier'),
            tracking_url=tracking_data.get('trackingUrl'),
            current_location=tracking_data.get('currentLocation')
        )
        
    except Exception as e:
        logger.error(f"Error formatting order tracking: {str(e)}")
        raise ValueError(f"Invalid tracking data: {str(e)}")


# ============================================================================
# Agent Response Formatters
# ============================================================================

def format_agent_response(
    message: str,
    response_type: str,
    session_id: str,
    data: Optional[Dict[str, Any]] = None,
    suggestions: List[str] = None,
    tools_used: List[str] = None,
    requires_action: bool = False,
    action_buttons: List[Dict[str, str]] = None,
    confidence_score: Optional[float] = None
) -> AgentResponse:
    """
    Format structured agent response.
    
    Args:
        message: Main response message
        response_type: Type of response
        session_id: Session identifier
        data: Additional structured data
        suggestions: Follow-up suggestions
        tools_used: List of tools used
        requires_action: Whether user action is required
        action_buttons: Suggested action buttons
        confidence_score: Response confidence
        
    Returns:
        AgentResponse: Formatted agent response
    """
    try:
        return AgentResponse(
            message=message,
            response_type=ResponseType(response_type.lower()),
            session_id=session_id,
            data=data,
            suggestions=suggestions or [],
            tools_used=tools_used or [],
            requires_action=requires_action,
            action_buttons=action_buttons or [],
            confidence_score=confidence_score
        )
        
    except Exception as e:
        logger.error(f"Error formatting agent response: {str(e)}")
        raise ValueError(f"Invalid agent response data: {str(e)}")


def format_error_response(
    error_code: str,
    error_message: str,
    error_type: str,
    session_id: str,
    suggestions: List[str] = None,
    retry_possible: bool = True,
    debug_info: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """
    Format structured error response.
    
    Args:
        error_code: Error code identifier
        error_message: Human-readable error message
        error_type: Error category
        session_id: Session identifier
        suggestions: Suggested solutions
        retry_possible: Whether operation can be retried
        debug_info: Debug information
        
    Returns:
        ErrorResponse: Formatted error response
    """
    try:
        return ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            error_type=ErrorType(error_type.lower()),
            session_id=session_id,
            suggestions=suggestions or [],
            retry_possible=retry_possible,
            debug_info=debug_info
        )
        
    except Exception as e:
        logger.error(f"Error formatting error response: {str(e)}")
        # Return a basic error response if formatting fails
        return ErrorResponse(
            error_code="FORMATTING_ERROR",
            error_message="An error occurred while formatting the response",
            error_type=ErrorType.INTERNAL,
            session_id=session_id,
            retry_possible=False
        )


def format_tool_result(
    tool_name: str,
    success: bool,
    execution_time: float,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    retry_count: int = 0
) -> ToolResult:
    """
    Format tool execution result.
    
    Args:
        tool_name: Name of the executed tool
        success: Whether execution succeeded
        execution_time: Execution time in seconds
        result: Tool result data
        error: Error message if failed
        retry_count: Number of retries attempted
        
    Returns:
        ToolResult: Formatted tool result
    """
    try:
        return ToolResult(
            tool_name=tool_name,
            success=success,
            execution_time=execution_time,
            result=result,
            error=error,
            retry_count=retry_count
        )
        
    except Exception as e:
        logger.error(f"Error formatting tool result: {str(e)}")
        raise ValueError(f"Invalid tool result data: {str(e)}")


# ============================================================================
# WebSocket Message Formatters
# ============================================================================

def format_websocket_message(
    message_type: str,
    content: str,
    session_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format message for WebSocket transmission.
    
    Args:
        message_type: Type of WebSocket message
        content: Message content
        session_id: Session identifier
        data: Additional message data
        
    Returns:
        Dict: Formatted WebSocket message
    """
    try:
        websocket_msg = WebSocketMessage(
            type=WebSocketMessageType(message_type.lower()),
            message=content,
            timestamp=int(time.time() * 1000),
            session_id=session_id,
            data=data
        )
        
        return websocket_msg.dict(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Error formatting WebSocket message: {str(e)}")
        # Return a basic message if formatting fails
        return {
            'type': 'error',
            'message': 'An error occurred while formatting the message',
            'timestamp': int(time.time() * 1000)
        }


def format_typing_indicator(session_id: str, is_typing: bool) -> Dict[str, Any]:
    """
    Format typing indicator message.
    
    Args:
        session_id: Session identifier
        is_typing: Whether agent is typing
        
    Returns:
        Dict: Formatted typing indicator message
    """
    return format_websocket_message(
        message_type='typing',
        content='',
        session_id=session_id,
        data={'is_typing': is_typing}
    )


# ============================================================================
# Utility Functions
# ============================================================================

def sanitize_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize response data by removing sensitive information.
    
    Args:
        data: Raw response data
        
    Returns:
        Dict: Sanitized response data
    """
    # Fields to remove from responses
    sensitive_fields = [
        'password', 'token', 'secret', 'key', 'auth',
        'internal_id', 'debug_info', 'stack_trace'
    ]
    
    sanitized = {}
    for key, value in data.items():
        if key.lower() not in sensitive_fields:
            if isinstance(value, dict):
                sanitized[key] = sanitize_response_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    sanitize_response_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
    
    return sanitized


def validate_response_size(response_data: Dict[str, Any], max_size_kb: int = 256) -> bool:
    """
    Validate that response size is within WebSocket limits.
    
    Args:
        response_data: Response data to validate
        max_size_kb: Maximum size in kilobytes
        
    Returns:
        bool: Whether response is within size limits
    """
    try:
        response_json = json.dumps(response_data)
        size_kb = len(response_json.encode('utf-8')) / 1024
        return size_kb <= max_size_kb
    except Exception:
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def _check_category_match(product_data: Dict[str, Any], query_context: str) -> bool:
    """Check if product category matches query context."""
    product_category = product_data.get('category', '').lower()
    query_lower = query_context.lower()
    
    # Simple keyword matching - in production, this would be more sophisticated
    category_keywords = product_category.split()
    return any(keyword in query_lower for keyword in category_keywords)


def _check_price_match(product_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> bool:
    """Check if product price matches user preferences."""
    if not user_preferences:
        return True
    
    product_price = float(product_data.get('price', 0))
    price_min = user_preferences.get('price_min')
    price_max = user_preferences.get('price_max')
    
    if price_min is not None and product_price < price_min:
        return False
    if price_max is not None and product_price > price_max:
        return False
    
    return True


def _generate_similarity_factors(product_data: Dict[str, Any], query_context: str) -> List[str]:
    """Generate similarity factors for recommendation reasoning."""
    factors = []
    
    # Check for keyword matches
    product_name = product_data.get('name', '').lower()
    product_description = product_data.get('description', '').lower()
    query_lower = query_context.lower()
    
    if any(word in product_name for word in query_lower.split()):
        factors.append("Name matches search terms")
    
    if any(word in product_description for word in query_lower.split()):
        factors.append("Description matches search terms")
    
    # Check for category match
    if _check_category_match(product_data, query_context):
        factors.append("Category relevance")
    
    # Check for high rating
    rating = product_data.get('rating')
    if rating and rating >= 4.0:
        factors.append("High customer rating")
    
    # Check for availability
    if product_data.get('isAvailable', True):
        factors.append("Currently available")
    
    return factors


def _calculate_confidence_level(relevance_score: float) -> str:
    """Calculate confidence level based on relevance score."""
    if relevance_score >= 0.8:
        return "high"
    elif relevance_score >= 0.5:
        return "medium"
    else:
        return "low"