"""
Tests for Cart Lambda Function

Tests cart operations including add, update, remove, and get.
"""

import json
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal
import os
import sys

# Set environment variables before importing
os.environ['CART_TABLE_NAME'] = 'test-cart'
os.environ['PRODUCTS_TABLE_NAME'] = 'test-products'
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'E-Com67'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'cart'

# Add the lambda directory to the path so we can import the cart module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'cart'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layers', 'utils', 'python'))

from cart import handler, CartService
from utils.exceptions import BusinessLogicError, ValidationError


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables for testing."""
    with mock_aws():
        # Set environment variables
        os.environ['CART_TABLE_NAME'] = 'test-cart'
        os.environ['PRODUCTS_TABLE_NAME'] = 'test-products'
        
        # Patch the cart module's dynamodb resource
        import cart
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        cart.dynamodb = dynamodb
        
        # Create cart table
        cart_table = dynamodb.create_table(
            TableName='test-cart',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'productId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'productId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create products table
        products_table = dynamodb.create_table(
            TableName='test-products',
            KeySchema=[
                {'AttributeName': 'productId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'productId', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for tables to be created
        cart_table.wait_until_exists()
        products_table.wait_until_exists()
        
        # Add test products
        products_table.put_item(Item={
            'productId': 'prod-1',
            'name': 'Test Product 1',
            'description': 'A test product',
            'price': Decimal('29.99'),
            'category': 'Electronics',
            'stock': 10,
            'imageUrl': 'https://example.com/image1.jpg',
            'isActive': True
        })
        
        products_table.put_item(Item={
            'productId': 'prod-2',
            'name': 'Test Product 2',
            'description': 'Another test product',
            'price': Decimal('19.99'),
            'category': 'Books',
            'stock': 5,
            'imageUrl': 'https://example.com/image2.jpg',
            'isActive': True
        })
        
        products_table.put_item(Item={
            'productId': 'prod-inactive',
            'name': 'Inactive Product',
            'description': 'An inactive product',
            'price': Decimal('39.99'),
            'category': 'Electronics',
            'stock': 0,
            'imageUrl': 'https://example.com/image3.jpg',
            'isActive': False
        })
        
        yield dynamodb


class MockLambdaContext:
    """Mock Lambda context for testing."""
    def __init__(self):
        self.function_name = 'test-cart-function'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-cart-function'
        self.memory_limit_in_mb = 128
        self.remaining_time_in_millis = lambda: 30000
        self.aws_request_id = 'test-request-id'
        self.log_group_name = '/aws/lambda/test-cart-function'
        self.log_stream_name = '2023/01/01/[$LATEST]test-stream'


def create_api_event(method='GET', path_params=None, body=None, user_id='test-user-123'):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': method,
        'pathParameters': path_params or {},
        'queryStringParameters': {},
        'headers': {'X-User-Id': user_id},
        'body': json.dumps(body) if body else None,
        'requestContext': {}
    }


class TestCartService:
    """Test CartService methods directly."""
    
    def test_add_item_to_cart_new_item(self, dynamodb_tables):
        """Test adding a new item to cart."""
        user_id = 'test-user-123'
        cart_item = {'productId': 'prod-1', 'quantity': 2}
        
        result = CartService.add_item_to_cart(user_id, cart_item)
        
        assert result['userId'] == user_id
        assert result['productId'] == 'prod-1'
        assert result['quantity'] == 2
        assert result['name'] == 'Test Product 1'
        assert result['price'] == 29.99
    
    def test_add_item_to_cart_existing_item(self, dynamodb_tables):
        """Test adding to existing cart item increases quantity."""
        user_id = 'test-user-123'
        cart_item = {'productId': 'prod-1', 'quantity': 2}
        
        # Add item first time
        CartService.add_item_to_cart(user_id, cart_item)
        
        # Add same item again
        result = CartService.add_item_to_cart(user_id, cart_item)
        
        assert result['quantity'] == 4  # 2 + 2
    
    def test_add_item_insufficient_stock(self, dynamodb_tables):
        """Test adding item with insufficient stock raises error."""
        user_id = 'test-user-123'
        cart_item = {'productId': 'prod-2', 'quantity': 10}  # Only 5 in stock
        
        with pytest.raises(BusinessLogicError, match="Insufficient stock"):
            CartService.add_item_to_cart(user_id, cart_item)
    
    def test_add_item_inactive_product(self, dynamodb_tables):
        """Test adding inactive product raises error."""
        user_id = 'test-user-123'
        cart_item = {'productId': 'prod-inactive', 'quantity': 1}
        
        with pytest.raises(BusinessLogicError, match="not available"):
            CartService.add_item_to_cart(user_id, cart_item)
    
    def test_add_item_nonexistent_product(self, dynamodb_tables):
        """Test adding nonexistent product raises error."""
        user_id = 'test-user-123'
        cart_item = {'productId': 'nonexistent', 'quantity': 1}
        
        with pytest.raises(BusinessLogicError, match="not found"):
            CartService.add_item_to_cart(user_id, cart_item)
    
    def test_update_cart_item(self, dynamodb_tables):
        """Test updating cart item quantity."""
        user_id = 'test-user-123'
        
        # Add item first
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Update quantity
        result = CartService.update_cart_item(user_id, 'prod-1', 3)
        
        assert result['quantity'] == 3
    
    def test_update_nonexistent_cart_item(self, dynamodb_tables):
        """Test updating nonexistent cart item returns None."""
        user_id = 'test-user-123'
        
        result = CartService.update_cart_item(user_id, 'prod-1', 3)
        
        assert result is None
    
    def test_remove_cart_item(self, dynamodb_tables):
        """Test removing cart item."""
        user_id = 'test-user-123'
        
        # Add item first
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Remove item
        result = CartService.remove_cart_item(user_id, 'prod-1')
        
        assert result is True
    
    def test_remove_nonexistent_cart_item(self, dynamodb_tables):
        """Test removing nonexistent cart item returns False."""
        user_id = 'test-user-123'
        
        result = CartService.remove_cart_item(user_id, 'prod-1')
        
        assert result is False
    
    def test_get_cart_contents_empty(self, dynamodb_tables):
        """Test getting empty cart contents."""
        user_id = 'test-user-123'
        
        result = CartService.get_cart_contents(user_id)
        
        assert result['items'] == []
        assert result['itemCount'] == 0
        assert result['subtotal'] == 0.0
        assert result['totalAmount'] == 0.0
        assert result['isValid'] is True
    
    def test_get_cart_contents_with_items(self, dynamodb_tables):
        """Test getting cart contents with items."""
        user_id = 'test-user-123'
        
        # Add items to cart
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        CartService.add_item_to_cart(user_id, {'productId': 'prod-2', 'quantity': 1})
        
        result = CartService.get_cart_contents(user_id)
        
        assert len(result['items']) == 2
        assert result['itemCount'] == 2
        assert result['subtotal'] == 79.97  # (29.99 * 2) + (19.99 * 1)
        assert result['isValid'] is True
    
    def test_clear_cart(self, dynamodb_tables):
        """Test clearing cart."""
        user_id = 'test-user-123'
        
        # Add items to cart
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        CartService.add_item_to_cart(user_id, {'productId': 'prod-2', 'quantity': 1})
        
        # Clear cart
        result = CartService.clear_cart(user_id)
        
        assert result is True
        
        # Verify cart is empty
        cart_contents = CartService.get_cart_contents(user_id)
        assert cart_contents['itemCount'] == 0
    
    def test_validate_cart_for_checkout(self, dynamodb_tables):
        """Test cart validation for checkout."""
        user_id = 'test-user-123'
        
        # Add items to cart
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        result = CartService.validate_cart_for_checkout(user_id)
        
        assert result['isValid'] is True
        assert result['userId'] == user_id
        assert len(result['items']) == 1
        assert result['totalAmount'] > 0


class TestCartHandler:
    """Test the Lambda handler function."""
    
    def test_get_cart_contents(self, dynamodb_tables):
        """Test GET request to get cart contents."""
        event = create_api_event('GET')
        context = MockLambdaContext()
        
        response = handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'items' in body
        assert 'itemCount' in body
    
    def test_add_item_to_cart(self, dynamodb_tables):
        """Test POST request to add item to cart."""
        event = create_api_event('POST', body={'productId': 'prod-1', 'quantity': 2})
        context = MockLambdaContext()
        
        response = handler(event, context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['productId'] == 'prod-1'
        assert body['quantity'] == 2
    
    def test_update_cart_item(self, dynamodb_tables):
        """Test PUT request to update cart item."""
        user_id = 'test-user-123'
        
        # Add item first
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Update via API
        event = create_api_event(
            'PUT', 
            path_params={'productId': 'prod-1'}, 
            body={'quantity': 3},
            user_id=user_id
        )
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['quantity'] == 3
    
    def test_remove_cart_item(self, dynamodb_tables):
        """Test DELETE request to remove cart item."""
        user_id = 'test-user-123'
        
        # Add item first
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Remove via API
        event = create_api_event(
            'DELETE', 
            path_params={'productId': 'prod-1'},
            user_id=user_id
        )
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'removed from cart' in body['message']
    
    def test_clear_cart(self, dynamodb_tables):
        """Test DELETE request to clear entire cart."""
        user_id = 'test-user-123'
        
        # Add items first
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Clear via API
        event = create_api_event('DELETE', user_id=user_id)
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'Cart cleared' in body['message']
    
    def test_invalid_json(self, dynamodb_tables):
        """Test handling of invalid JSON in request body."""
        event = create_api_event('POST')
        event['body'] = 'invalid json'
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_missing_user_id(self, dynamodb_tables):
        """Test handling of missing user ID."""
        event = create_api_event('GET')
        event['headers'] = {}  # Remove user ID header
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_options_request(self, dynamodb_tables):
        """Test OPTIONS request for CORS."""
        event = create_api_event('OPTIONS')
        
        response = handler(event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_step_functions_validation(self, dynamodb_tables):
        """Test Step Functions cart validation."""
        user_id = 'test-user-123'
        
        # Add item to cart
        CartService.add_item_to_cart(user_id, {'productId': 'prod-1', 'quantity': 2})
        
        # Create Step Functions event
        event = {
            'source': 'step-functions',
            'input': {'userId': user_id}
        }
        
        response = handler(event, MockLambdaContext())
        
        assert response['isValid'] is True
        assert response['userId'] == user_id
        assert len(response['items']) == 1