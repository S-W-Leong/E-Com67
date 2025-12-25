"""
Basic tests for Pydantic models to ensure they work correctly.
This is a simple validation script to test model creation and validation.
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from models import (
        ProductInfo, ProductSearchResponse, ProductRecommendation,
        CartItem, CartSummary, CartOperation, CartOperationType,
        OrderItem, OrderInfo, OrderHistory, OrderStatus,
        AgentResponse, ErrorResponse, ResponseType, ErrorType,
        WebSocketMessage, WebSocketMessageType
    )
    
    from response_formatters import (
        format_product_info, format_cart_summary, format_order_info,
        format_agent_response, format_websocket_message
    )
    
    from validation_utils import (
        validate_product_data, sanitize_product_data,
        validate_cart_data, sanitize_cart_data
    )
    
    print("✓ All imports successful")
    
    # Test ProductInfo model
    product_data = {
        'product_id': 'test-123',
        'name': 'Test Product',
        'description': 'A test product for validation',
        'price': 29.99,
        'category': 'Electronics',
        'stock': 10,
        'is_available': True
    }
    
    product = ProductInfo(**product_data)
    print(f"✓ ProductInfo created: {product.name} - ${product.price}")
    
    # Test ProductSearchResponse
    search_response = ProductSearchResponse(
        query="test search",
        products=[product],
        total_count=1
    )
    print(f"✓ ProductSearchResponse created with {len(search_response.products)} products")
    
    # Test CartItem model
    cart_item_data = {
        'product_id': 'test-123',
        'name': 'Test Product',
        'price': 29.99,
        'quantity': 2,
        'subtotal': 59.98,
        'is_available': True,
        'stock_quantity': 10
    }
    
    cart_item = CartItem(**cart_item_data)
    print(f"✓ CartItem created: {cart_item.quantity}x {cart_item.name}")
    
    # Test CartSummary model
    cart_summary_data = {
        'user_id': 'user-123',
        'items': [cart_item],
        'total_items': 2,
        'subtotal': 59.98,
        'tax': 4.80,
        'total': 64.78,
        'is_valid': True
    }
    
    cart_summary = CartSummary(**cart_summary_data)
    print(f"✓ CartSummary created: {cart_summary.total_items} items, ${cart_summary.total}")
    
    # Test OrderInfo model
    order_item_data = {
        'product_id': 'test-123',
        'name': 'Test Product',
        'price': 29.99,
        'quantity': 2,
        'subtotal': 59.98
    }
    
    order_item = OrderItem(**order_item_data)
    
    order_data = {
        'order_id': 'order-123',
        'user_id': 'user-123',
        'status': OrderStatus.PENDING,
        'items': [order_item],
        'subtotal': 59.98,
        'tax': 4.80,
        'shipping': 5.00,
        'total_amount': 69.78,
        'order_date': datetime.utcnow(),
        'shipping_address': {
            'street': '123 Test St',
            'city': 'Test City',
            'country': 'Test Country'
        },
        'payment_method': 'credit_card'
    }
    
    order = OrderInfo(**order_data)
    print(f"✓ OrderInfo created: {order.order_id} - ${order.total_amount}")
    
    # Test AgentResponse model
    agent_response = AgentResponse(
        message="Test response message",
        response_type=ResponseType.INFO,
        session_id="session-123"
    )
    print(f"✓ AgentResponse created: {agent_response.response_type}")
    
    # Test ErrorResponse model
    error_response = ErrorResponse(
        error_code="TEST_ERROR",
        error_message="This is a test error",
        error_type=ErrorType.VALIDATION,
        session_id="session-123"
    )
    print(f"✓ ErrorResponse created: {error_response.error_code}")
    
    # Test WebSocketMessage model
    ws_message = WebSocketMessage(
        type=WebSocketMessageType.MESSAGE,
        message="Test WebSocket message",
        timestamp=1234567890000
    )
    print(f"✓ WebSocketMessage created: {ws_message.type}")
    
    # Test response formatters
    formatted_product = format_product_info(product_data)
    print(f"✓ format_product_info works: {formatted_product.name}")
    
    # Test validation utilities
    validation_errors = validate_product_data(product_data)
    print(f"✓ validate_product_data works: {len(validation_errors)} errors")
    
    sanitized_product = sanitize_product_data(product_data)
    print(f"✓ sanitize_product_data works: {sanitized_product.get('name')}")
    
    # Test with DynamoDB Decimal types
    dynamodb_data = {
        'product_id': 'test-456',
        'name': 'DynamoDB Product',
        'description': 'Product with Decimal price',
        'price': Decimal('39.99'),  # DynamoDB returns Decimal
        'category': 'Test',
        'stock': 5,
        'is_available': True
    }
    
    formatted_dynamodb = format_product_info(dynamodb_data)
    print(f"✓ DynamoDB Decimal handling works: ${formatted_dynamodb.price}")
    
    print("\n🎉 All tests passed! Pydantic models are working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)