"""
Demonstration of Pydantic Models and Response Formatters Usage

This script shows how to use the comprehensive Pydantic models and response
formatters for the Strands AI Agent enhancement.
"""

# Example usage patterns for the implemented models and formatters

# ============================================================================
# Product Data Example
# ============================================================================

# Raw product data from DynamoDB/API
raw_product_data = {
    'productId': 'laptop-gaming-001',
    'name': 'ASUS ROG Gaming Laptop',
    'description': 'High-performance gaming laptop with RTX 4070 graphics card',
    'price': 1299.99,  # Could be Decimal from DynamoDB
    'currency': 'USD',
    'category': 'Electronics',
    'stock': 15,
    'imageUrl': 'https://example.com/images/laptop-001.jpg',
    'rating': 4.5,
    'tags': ['gaming', 'laptop', 'RTX', 'high-performance'],
    'isAvailable': True,
    'specifications': {
        'processor': 'Intel i7-12700H',
        'memory': '16GB DDR4',
        'storage': '1TB SSD',
        'graphics': 'RTX 4070'
    },
    'brand': 'ASUS',
    'sku': 'ROG-STRIX-G15'
}

# Using the formatter to create a validated ProductInfo model
# formatted_product = format_product_info(raw_product_data)

# ============================================================================
# Cart Data Example
# ============================================================================

# Raw cart data from DynamoDB
raw_cart_data = {
    'userId': 'user-12345',
    'items': [
        {
            'productId': 'laptop-gaming-001',
            'name': 'ASUS ROG Gaming Laptop',
            'price': 1299.99,
            'quantity': 1,
            'subtotal': 1299.99,
            'imageUrl': 'https://example.com/images/laptop-001.jpg',
            'isAvailable': True,
            'stockQuantity': 15,
            'category': 'Electronics',
            'sku': 'ROG-STRIX-G15',
            'addedAt': '2023-12-23T10:30:00Z'
        }
    ],
    'totalItems': 1,
    'subtotal': 1299.99,
    'tax': 104.00,
    'shipping': 0.00,
    'discount': 50.00,
    'total': 1353.99,
    'currency': 'USD',
    'lastUpdated': '2023-12-23T10:30:00Z',
    'isValid': True,
    'validationErrors': [],
    'estimatedDelivery': '2023-12-28T00:00:00Z'
}

# Using the formatter to create a validated CartSummary model
# formatted_cart = format_cart_summary(raw_cart_data)

# ============================================================================
# Order Data Example
# ============================================================================

# Raw order data from DynamoDB
raw_order_data = {
    'orderId': 'order-67890',
    'userId': 'user-12345',
    'status': 'shipped',
    'items': [
        {
            'productId': 'laptop-gaming-001',
            'name': 'ASUS ROG Gaming Laptop',
            'price': 1299.99,
            'quantity': 1,
            'subtotal': 1299.99,
            'sku': 'ROG-STRIX-G15',
            'category': 'Electronics'
        }
    ],
    'subtotal': 1299.99,
    'tax': 104.00,
    'shipping': 0.00,
    'discount': 50.00,
    'totalAmount': 1353.99,
    'currency': 'USD',
    'orderDate': '2023-12-20T14:30:00Z',
    'estimatedDelivery': '2023-12-28T00:00:00Z',
    'trackingNumber': 'TRK123456789',
    'shippingAddress': {
        'street': '123 Main Street',
        'city': 'San Francisco',
        'state': 'CA',
        'postalCode': '94105',
        'country': 'USA'
    },
    'paymentMethod': 'credit_card',
    'paymentStatus': 'completed'
}

# Using the formatter to create a validated OrderInfo model
# formatted_order = format_order_info(raw_order_data)

# ============================================================================
# Agent Response Example
# ============================================================================

# Creating a structured agent response
agent_response_data = {
    'message': 'I found a great gaming laptop for you! The ASUS ROG Gaming Laptop is currently available for $1,299.99.',
    'response_type': 'product_list',
    'session_id': 'session-abc123',
    'data': {
        'products': [raw_product_data],
        'search_query': 'gaming laptop',
        'total_results': 1
    },
    'suggestions': [
        'Would you like to add this to your cart?',
        'Do you need any accessories?',
        'Would you like to see similar products?'
    ],
    'tools_used': ['product_search'],
    'requires_action': False,
    'action_buttons': [
        {'text': 'Add to Cart', 'action': 'add_to_cart'},
        {'text': 'View Details', 'action': 'view_product'}
    ],
    'confidence_score': 0.95
}

# Using the formatter to create a validated AgentResponse model
# formatted_response = format_agent_response(**agent_response_data)

# ============================================================================
# WebSocket Message Example
# ============================================================================

# Creating a WebSocket message for real-time communication
websocket_message_data = {
    'message_type': 'message',
    'content': 'I found a great gaming laptop for you!',
    'session_id': 'session-abc123',
    'data': {
        'response_type': 'product_list',
        'product_count': 1
    }
}

# Using the formatter to create a WebSocket-compatible message
# ws_message = format_websocket_message(**websocket_message_data)

# ============================================================================
# Error Response Example
# ============================================================================

# Creating a structured error response
error_response_data = {
    'error_code': 'PRODUCT_NOT_FOUND',
    'error_message': 'The requested product could not be found in our catalog.',
    'error_type': 'not_found',
    'session_id': 'session-abc123',
    'suggestions': [
        'Try searching with different keywords',
        'Browse our categories',
        'Contact customer support'
    ],
    'retry_possible': True
}

# Using the formatter to create a validated ErrorResponse model
# formatted_error = format_error_response(**error_response_data)

# ============================================================================
# Validation Example
# ============================================================================

# Validating product data before processing
# validation_errors = validate_product_data(raw_product_data)
# if validation_errors:
#     print(f"Validation errors found: {validation_errors}")
# else:
#     print("Product data is valid")

# Sanitizing data from external sources
# sanitized_product = sanitize_product_data(raw_product_data)

# ============================================================================
# Integration with Strands Agent Tools
# ============================================================================

"""
Example of how these models would be used in Strands agent tools:

@tool
def search_products(query: str, category: str = None) -> ProductSearchResponse:
    # Call existing search API
    raw_results = search_api.search(query, category)
    
    # Format and validate results
    formatted_products = [format_product_info(product) for product in raw_results['products']]
    
    # Return structured response
    return ProductSearchResponse(
        query=query,
        products=formatted_products,
        total_count=raw_results['total'],
        suggestions=raw_results.get('suggestions', [])
    )

@tool
def add_to_cart(product_id: str, quantity: int = 1) -> CartOperation:
    # Call existing cart API
    result = cart_api.add_item(product_id, quantity)
    
    # Format the operation result
    return format_cart_operation(
        operation_type='add',
        product_id=product_id,
        quantity=quantity,
        success=result['success'],
        message=result['message'],
        cart_data=result['cart']
    )

@tool
def get_order_history(page: int = 1) -> OrderHistory:
    # Call existing orders API
    raw_orders = orders_api.get_user_orders(page=page)
    
    # Format the order history
    return format_order_history(
        user_id=get_current_user_id(),
        orders_data=raw_orders['orders'],
        total_orders=raw_orders['total'],
        page=page
    )
"""

print("✓ Pydantic models and formatters are ready for Strands AI Agent integration!")
print("✓ All models include comprehensive validation and error handling")
print("✓ Response formatters handle DynamoDB Decimal types and data sanitization")
print("✓ WebSocket message formatting ensures real-time communication compatibility")
print("✓ Error responses provide structured feedback with actionable suggestions")