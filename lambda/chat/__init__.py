"""
Strands AI Agent Chat Module

This module contains the enhanced chat functionality with Pydantic models,
response formatters, and validation utilities for the E-Com67 platform.
"""

# Import main models for easy access
from .models import (
    # Product models
    ProductInfo,
    ProductRecommendation,
    ProductSearchResponse,
    
    # Cart models
    CartItem,
    CartSummary,
    CartOperation,
    CartOperationType,
    
    # Order models
    OrderItem,
    OrderInfo,
    OrderHistory,
    OrderTracking,
    OrderStatus,
    OrderStatusUpdate,
    
    # Agent response models
    AgentResponse,
    ErrorResponse,
    ToolResult,
    ResponseType,
    ErrorType,
    
    # Knowledge models
    KnowledgeSource,
    KnowledgeResponse,
    
    # WebSocket models
    WebSocketMessage,
    WebSocketMessageType,
    
    # Utility models
    PaginationInfo,
    SearchFilters
)

# Import response formatters
from .response_formatters import (
    # Product formatters
    format_product_info,
    format_product_search_response,
    format_product_recommendations,
    
    # Cart formatters
    format_cart_item,
    format_cart_summary,
    format_cart_operation,
    
    # Order formatters
    format_order_item,
    format_order_info,
    format_order_history,
    format_order_tracking,
    
    # Agent response formatters
    format_agent_response,
    format_error_response,
    format_tool_result,
    
    # WebSocket formatters
    format_websocket_message,
    format_typing_indicator,
    
    # Utility functions
    sanitize_response_data,
    validate_response_size
)

# Import validation utilities
from .validation_utils import (
    # Validation functions
    validate_product_data,
    validate_cart_data,
    validate_cart_item_data,
    validate_order_data,
    validate_order_item_data,
    validate_address_data,
    
    # Sanitization functions
    sanitize_product_data,
    sanitize_cart_data,
    sanitize_cart_item_data,
    sanitize_order_data,
    sanitize_order_item_data,
    sanitize_address_data,
    
    # Batch processing functions
    validate_and_sanitize_products,
    validate_and_sanitize_orders
)

__version__ = "1.0.0"
__author__ = "E-Com67 Development Team"

__all__ = [
    # Models
    "ProductInfo",
    "ProductRecommendation", 
    "ProductSearchResponse",
    "CartItem",
    "CartSummary",
    "CartOperation",
    "CartOperationType",
    "OrderItem",
    "OrderInfo",
    "OrderHistory",
    "OrderTracking",
    "OrderStatus",
    "OrderStatusUpdate",
    "AgentResponse",
    "ErrorResponse",
    "ToolResult",
    "ResponseType",
    "ErrorType",
    "KnowledgeSource",
    "KnowledgeResponse",
    "WebSocketMessage",
    "WebSocketMessageType",
    "PaginationInfo",
    "SearchFilters",
    
    # Response formatters
    "format_product_info",
    "format_product_search_response",
    "format_product_recommendations",
    "format_cart_item",
    "format_cart_summary",
    "format_cart_operation",
    "format_order_item",
    "format_order_info",
    "format_order_history",
    "format_order_tracking",
    "format_agent_response",
    "format_error_response",
    "format_tool_result",
    "format_websocket_message",
    "format_typing_indicator",
    "sanitize_response_data",
    "validate_response_size",
    
    # Validation utilities
    "validate_product_data",
    "validate_cart_data",
    "validate_cart_item_data",
    "validate_order_data",
    "validate_order_item_data",
    "validate_address_data",
    "sanitize_product_data",
    "sanitize_cart_data",
    "sanitize_cart_item_data",
    "sanitize_order_data",
    "sanitize_order_item_data",
    "sanitize_address_data",
    "validate_and_sanitize_products",
    "validate_and_sanitize_orders"
]