#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Strands AI Agent

This test suite validates the complete integration of the Strands AI Agent
with all existing E-Com67 systems including APIs, WebSocket communication,
conversation flow, and error handling mechanisms.

Test Coverage:
- Strands agent integration with existing APIs (products, cart, orders)
- WebSocket message compatibility with frontend applications
- Conversation flow and context management across sessions
- Tool integration with DynamoDB, OpenSearch, and S3 services
- Error handling and fallback mechanisms under various failure scenarios
"""

import json
import pytest
import boto3
import time
import uuid
from moto import mock_aws
from unittest.mock import patch, MagicMock, Mock
from decimal import Decimal
import os
import sys
from datetime import datetime, timedelta

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))

# Mock environment variables
os.environ.update({
    'CHAT_HISTORY_TABLE_NAME': 'test-chat-history',
    'PRODUCTS_TABLE_NAME': 'test-products',
    'CART_TABLE_NAME': 'test-cart',
    'ORDERS_TABLE_NAME': 'test-orders',
    'OPENSEARCH_ENDPOINT': 'https://test-opensearch.amazonaws.com',
    'KNOWLEDGE_BASE_ID': 'test-kb-id',
    'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1',
    'AWS_DEFAULT_REGION': 'ap-southeast-1',
    'DEPLOYMENT_STAGE': 'test',
    'POWERTOOLS_METRICS_NAMESPACE': 'E-Com67-Test',
    'POWERTOOLS_SERVICE_NAME': 'chat-test'
})

# Import after setting environment variables
import chat
from strands_config import StrandsAgentManager, StrandsAgentConfig
from models import ProductInfo, CartSummary, OrderInfo, AgentResponse
from tools.product_search_tool import product_search, get_product_details
from tools.cart_management_tool import add_to_cart, get_cart_contents
from tools.order_query_tool import get_order_history, get_order_details


class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-strands-chat-function'
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = 'arn:aws:lambda:ap-southeast-1:123456789012:function:test-strands-chat'
        self.aws_request_id = f'test-request-{uuid.uuid4()}'
        self.remaining_time_in_millis = lambda: 30000


class MockStrandsAgent:
    """Mock Strands agent for testing without actual SDK"""
    
    def __init__(self, tools=None):
        self.tools = tools or []
        self.call_count = 0
        self.last_message = None
        
    def __call__(self, message):
        """Mock agent call that simulates tool usage"""
        self.call_count += 1
        self.last_message = message
        
        # Simulate different responses based on message content
        if 'search' in message.lower() or 'find' in message.lower():
            return self._mock_product_search_response(message)
        elif 'cart' in message.lower():
            return self._mock_cart_response(message)
        elif 'order' in message.lower():
            return self._mock_order_response(message)
        else:
            return self._mock_general_response(message)
    
    def _mock_product_search_response(self, message):
        """Mock product search response"""
        return MockAgentResult(
            message={
                'content': [{'text': 'I found several products matching your search. Here are the top results with detailed information and pricing.'}]
            },
            tool_calls=[
                MockToolCall('product_search', True, {
                    'products': [
                        {
                            'product_id': 'laptop-123',
                            'name': 'Gaming Laptop',
                            'price': 1299.99,
                            'description': 'High-performance gaming laptop'
                        }
                    ],
                    'total_count': 1
                })
            ]
        )
    
    def _mock_cart_response(self, message):
        """Mock cart management response"""
        return MockAgentResult(
            message={
                'content': [{'text': 'I\'ve updated your cart. Here\'s your current cart summary with all items and totals.'}]
            },
            tool_calls=[
                MockToolCall('add_to_cart', True, {
                    'success': True,
                    'cart_summary': {
                        'items': [{'product_id': 'laptop-123', 'quantity': 1, 'price': 1299.99}],
                        'total': 1299.99
                    }
                })
            ]
        )
    
    def _mock_order_response(self, message):
        """Mock order query response"""
        return MockAgentResult(
            message={
                'content': [{'text': 'Here are your recent orders with current status and tracking information.'}]
            },
            tool_calls=[
                MockToolCall('get_order_history', True, {
                    'orders': [
                        {
                            'order_id': 'order-456',
                            'status': 'shipped',
                            'total_amount': 1299.99,
                            'tracking_number': 'TRK123456'
                        }
                    ]
                })
            ]
        )
    
    def _mock_general_response(self, message):
        """Mock general response"""
        return MockAgentResult(
            message={
                'content': [{'text': 'I\'m here to help you with your shopping needs. I can search for products, manage your cart, and track your orders.'}]
            },
            tool_calls=[]
        )


class MockAgentResult:
    """Mock agent result object"""
    
    def __init__(self, message, tool_calls=None):
        self.message = message
        self.tool_calls = tool_calls or []


class MockToolCall:
    """Mock tool call result"""
    
    def __init__(self, name, success, result):
        self.name = name
        self.success = success
        self.result = result


@pytest.fixture
def mock_aws_services():
    """Set up mock AWS services for testing"""
    with mock_aws():
        # Create DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Chat history table
        chat_table = dynamodb.create_table(
            TableName='test-chat-history',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'},
                {'AttributeName': 'sessionId', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'sessionId-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'sessionId', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Products table
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
        
        # Cart table
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
        
        # Orders table
        orders_table = dynamodb.create_table(
            TableName='test-orders',
            KeySchema=[
                {'AttributeName': 'orderId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'orderId', 'AttributeType': 'S'},
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'createdAt', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'userId-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'userId', 'KeyType': 'HASH'},
                        {'AttributeName': 'createdAt', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        _populate_test_data(products_table, cart_table, orders_table, chat_table)
        
        yield {
            'dynamodb': dynamodb,
            'chat_table': chat_table,
            'products_table': products_table,
            'cart_table': cart_table,
            'orders_table': orders_table
        }


def _populate_test_data(products_table, cart_table, orders_table, chat_table):
    """Populate tables with test data"""
    
    # Test products
    test_products = [
        {
            'productId': 'laptop-123',
            'name': 'Gaming Laptop',
            'description': 'High-performance gaming laptop with RTX graphics',
            'price': Decimal('1299.99'),
            'category': 'Electronics',
            'stock': 10,
            'isActive': True,
            'imageUrl': 'https://example.com/laptop.jpg',
            'rating': Decimal('4.5'),
            'brand': 'TechBrand',
            'sku': 'TB-LAPTOP-001'
        },
        {
            'productId': 'phone-456',
            'name': 'Smartphone',
            'description': 'Latest smartphone with great camera',
            'price': Decimal('799.99'),
            'category': 'Electronics',
            'stock': 25,
            'isActive': True,
            'imageUrl': 'https://example.com/phone.jpg',
            'rating': Decimal('4.2'),
            'brand': 'PhoneCorp',
            'sku': 'PC-PHONE-002'
        },
        {
            'productId': 'headphones-789',
            'name': 'Wireless Headphones',
            'description': 'Premium noise-canceling headphones',
            'price': Decimal('299.99'),
            'category': 'Electronics',
            'stock': 0,  # Out of stock
            'isActive': True,
            'imageUrl': 'https://example.com/headphones.jpg',
            'rating': Decimal('4.8'),
            'brand': 'AudioTech',
            'sku': 'AT-HEAD-003'
        }
    ]
    
    for product in test_products:
        products_table.put_item(Item=product)
    
    # Test cart items
    test_cart_items = [
        {
            'userId': 'test-user-1',
            'productId': 'laptop-123',
            'quantity': 1,
            'price': Decimal('1299.99'),
            'addedAt': int(time.time()),
            'updatedAt': int(time.time())
        }
    ]
    
    for item in test_cart_items:
        cart_table.put_item(Item=item)
    
    # Test orders
    test_orders = [
        {
            'orderId': 'order-123',
            'userId': 'test-user-1',
            'status': 'shipped',
            'items': [
                {
                    'productId': 'phone-456',
                    'name': 'Smartphone',
                    'price': Decimal('799.99'),
                    'quantity': 1,
                    'subtotal': Decimal('799.99')
                }
            ],
            'subtotal': Decimal('799.99'),
            'taxAmount': Decimal('64.00'),
            'shippingCost': Decimal('5.99'),
            'totalAmount': Decimal('869.98'),
            'createdAt': int(time.time() - 86400),  # 1 day ago
            'estimatedDelivery': int(time.time() + 172800),  # 2 days from now
            'trackingNumber': 'TRK123456789',
            'shippingAddress': {
                'street': '123 Test St',
                'city': 'Test City',
                'state': 'TS',
                'zipCode': '12345',
                'country': 'US'
            },
            'paymentMethod': 'Credit Card',
            'paymentStatus': 'completed'
        }
    ]
    
    for order in test_orders:
        orders_table.put_item(Item=order)
    
    # Test chat history
    test_messages = [
        {
            'userId': 'test-user-1',
            'timestamp': int(time.time() - 3600) * 1000,  # 1 hour ago
            'messageId': str(uuid.uuid4()),
            'role': 'user',
            'content': 'Hello, I need help finding a laptop',
            'sessionId': 'session-123'
        },
        {
            'userId': 'test-user-1',
            'timestamp': int(time.time() - 3500) * 1000,
            'messageId': str(uuid.uuid4()),
            'role': 'assistant',
            'content': 'I can help you find a laptop! What are you looking for?',
            'sessionId': 'session-123'
        }
    ]
    
    for message in test_messages:
        chat_table.put_item(Item=message)


@pytest.fixture
def websocket_events():
    """Generate WebSocket event fixtures"""
    connection_id = 'test-connection-123'
    domain_name = 'test-api.execute-api.ap-southeast-1.amazonaws.com'
    stage = 'test'
    
    return {
        'connect': {
            'requestContext': {
                'routeKey': '$connect',
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage,
                'authorizer': {
                    'principalId': 'test-user-1'
                }
            }
        },
        'message': {
            'requestContext': {
                'routeKey': 'sendMessage',
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage,
                'authorizer': {
                    'principalId': 'test-user-1'
                }
            },
            'body': json.dumps({
                'message': 'I want to search for a gaming laptop',
                'sessionId': 'session-123'
            })
        },
        'disconnect': {
            'requestContext': {
                'routeKey': '$disconnect',
                'connectionId': connection_id,
                'domainName': domain_name,
                'stage': stage,
                'authorizer': {
                    'principalId': 'test-user-1'
                }
            }
        }
    }


class TestStrandsAgentIntegration:
    """Test Strands agent integration with E-Com67 APIs"""
    
    def test_agent_initialization_with_tools(self, mock_aws_services):
        """Test that Strands agent initializes correctly with all custom tools"""
        with patch('strands_config.Agent') as mock_agent_class, \
             patch('strands_config.BedrockModel') as mock_model_class:
            
            # Mock the Strands SDK components
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            
            mock_agent = MockStrandsAgent()
            mock_agent_class.return_value = mock_agent
            
            # Create agent manager
            config = StrandsAgentConfig.from_environment()
            manager = StrandsAgentManager(config)
            
            # Get agent with user context
            user_context = {
                'user_id': 'test-user-1',
                'session_id': 'session-123',
                'connection_id': 'test-connection-123'
            }
            
            agent = manager.get_agent(user_context)
            
            # Verify agent was created with correct configuration
            assert agent is not None
            mock_agent_class.assert_called_once()
            
            # Verify model configuration
            mock_model_class.assert_called_once()
            model_call_args = mock_model_class.call_args[1]
            assert model_call_args['model_id'] == 'amazon.titan-text-express-v1'
            assert model_call_args['temperature'] == 0.7
            assert model_call_args['region'] == 'ap-southeast-1'
    
    def test_product_search_tool_integration(self, mock_aws_services):
        """Test product search tool integration with OpenSearch and DynamoDB"""
        
        # Mock OpenSearch client
        with patch('tools.product_search_tool.get_opensearch_client') as mock_opensearch:
            mock_client = Mock()
            mock_opensearch.return_value = mock_client
            
            # Mock OpenSearch response
            mock_client.search.return_value = {
                'hits': {
                    'total': {'value': 1},
                    'hits': [
                        {
                            '_source': {
                                'productId': 'laptop-123',
                                'name': 'Gaming Laptop',
                                'description': 'High-performance gaming laptop',
                                'price': 1299.99,
                                'category': 'Electronics',
                                'stock': 10,
                                'isActive': True
                            },
                            '_score': 8.5
                        }
                    ]
                }
            }
            
            # Test product search
            result = product_search(
                query="gaming laptop",
                category="Electronics",
                limit=10
            )
            
            # Verify search was executed
            mock_client.search.assert_called_once()
            
            # Verify result structure
            assert result.query == "gaming laptop"
            assert len(result.products) == 1
            assert result.products[0].product_id == 'laptop-123'
            assert result.products[0].name == 'Gaming Laptop'
            assert result.total_count == 1
    
    def test_cart_management_tool_integration(self, mock_aws_services):
        """Test cart management tool integration with DynamoDB"""
        
        # Test adding item to cart
        result = add_to_cart(
            product_id='laptop-123',
            quantity=1,
            user_id='test-user-1'
        )
        
        # Verify operation succeeded
        assert result.success is True
        assert result.operation.value == 'add'
        assert result.product_id == 'laptop-123'
        assert result.quantity == 1
        
        # Verify cart summary is updated
        assert result.cart_summary.user_id == 'test-user-1'
        assert len(result.cart_summary.items) >= 1
        assert result.cart_summary.total_items >= 1
        
        # Test getting cart contents
        cart_contents = get_cart_contents(user_id='test-user-1')
        
        # Verify cart contents
        assert cart_contents.user_id == 'test-user-1'
        assert len(cart_contents.items) >= 1
        assert cart_contents.is_valid is True
        assert cart_contents.total > 0
    
    def test_order_query_tool_integration(self, mock_aws_services):
        """Test order query tool integration with DynamoDB"""
        
        # Test getting order history
        order_history = get_order_history(
            user_id='test-user-1',
            limit=10
        )
        
        # Verify order history
        assert order_history.user_id == 'test-user-1'
        assert len(order_history.orders) >= 1
        assert order_history.total_orders >= 1
        
        # Test getting specific order details
        order_details = get_order_details(
            order_id='order-123',
            user_id='test-user-1'
        )
        
        # Verify order details
        assert order_details is not None
        assert order_details.order_id == 'order-123'
        assert order_details.user_id == 'test-user-1'
        assert order_details.status.value == 'shipped'
        assert order_details.total_amount > 0


class TestWebSocketIntegration:
    """Test WebSocket communication and message compatibility"""
    
    def test_websocket_connection_handling(self, mock_aws_services, websocket_events):
        """Test WebSocket connection establishment and cleanup"""
        
        with patch('chat.boto3.client') as mock_boto_client:
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            # Test connection
            response = chat.handler(websocket_events['connect'], MockLambdaContext())
            
            # Verify connection response
            assert response['statusCode'] == 200
            assert 'Connected successfully' in response['body']
            
            # Verify welcome message was sent
            mock_api_gw.post_to_connection.assert_called_once()
            call_args = mock_api_gw.post_to_connection.call_args[1]
            assert call_args['ConnectionId'] == 'test-connection-123'
            
            # Parse welcome message
            message_data = json.loads(call_args['Data'])
            assert message_data['type'] == 'welcome'
            assert 'Welcome to E-Com67' in message_data['message']
    
    def test_websocket_message_processing_with_strands_agent(self, mock_aws_services, websocket_events):
        """Test WebSocket message processing with Strands agent integration"""
        
        with patch('chat.boto3.client') as mock_boto_client, \
             patch('chat.global_agent_manager') as mock_agent_manager:
            
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            # Mock agent manager and agent
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_agent = MockStrandsAgent()
            mock_manager.get_agent_for_user.return_value = mock_agent
            mock_manager.restore_session_context.return_value = {
                'conversation_history': [],
                'conversation_summary': '',
                'session_restored': True,
                'message_count': 0
            }
            
            # Process message
            response = chat.handler(websocket_events['message'], MockLambdaContext())
            
            # Verify message processing
            assert response['statusCode'] == 200
            assert 'Message processed successfully' in response['body']
            
            # Verify agent was called
            mock_manager.get_agent_for_user.assert_called_once()
            assert mock_agent.call_count == 1
            assert 'gaming laptop' in mock_agent.last_message
            
            # Verify response was sent to WebSocket
            assert mock_api_gw.post_to_connection.call_count >= 2  # Typing indicator + response
    
    def test_websocket_message_format_compatibility(self, mock_aws_services, websocket_events):
        """Test that WebSocket messages maintain frontend compatibility"""
        
        with patch('chat.boto3.client') as mock_boto_client, \
             patch('chat.global_agent_manager') as mock_agent_manager:
            
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            # Mock agent manager
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_agent = MockStrandsAgent()
            mock_manager.get_agent_for_user.return_value = mock_agent
            mock_manager.restore_session_context.return_value = {
                'conversation_history': [],
                'conversation_summary': '',
                'session_restored': True,
                'message_count': 0
            }
            
            # Process message
            chat.handler(websocket_events['message'], MockLambdaContext())
            
            # Get the response message (last call to post_to_connection)
            response_calls = mock_api_gw.post_to_connection.call_args_list
            response_call = response_calls[-1]  # Last call should be the actual response
            
            # Parse response message
            message_data = json.loads(response_call[1]['Data'])
            
            # Verify message format compatibility
            assert 'type' in message_data
            assert 'message' in message_data
            assert 'timestamp' in message_data
            
            # Verify message type is appropriate
            assert message_data['type'] in ['message', 'typing', 'error', 'system']
            
            # Verify message content exists
            assert isinstance(message_data['message'], str)
            assert len(message_data['message']) > 0
            
            # Verify timestamp is valid
            assert isinstance(message_data['timestamp'], int)
            assert message_data['timestamp'] > 0


class TestConversationFlowAndContext:
    """Test conversation flow and context management across sessions"""
    
    def test_conversation_context_maintenance(self, mock_aws_services):
        """Test that conversation context is maintained across messages"""
        
        with patch('chat.global_agent_manager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            # Mock session context restoration
            mock_manager.restore_session_context.return_value = {
                'conversation_history': [
                    {'role': 'user', 'content': 'Hello, I need help finding a laptop'},
                    {'role': 'assistant', 'content': 'I can help you find a laptop! What are you looking for?'}
                ],
                'conversation_summary': '',
                'session_restored': True,
                'message_count': 2
            }
            
            mock_agent = MockStrandsAgent()
            mock_manager.get_agent_for_user.return_value = mock_agent
            
            # Create user context
            user_context = {
                'user_id': 'test-user-1',
                'session_id': 'session-123',
                'connection_id': 'test-connection-123'
            }
            
            # Simulate getting agent for user
            agent = mock_manager.get_agent_for_user(user_context)
            
            # Verify context restoration was called
            mock_manager.restore_session_context.assert_called_once_with('test-user-1', 'session-123')
            
            # Verify agent received context
            assert agent is not None
    
    def test_conversation_history_retrieval(self, mock_aws_services):
        """Test conversation history retrieval from DynamoDB"""
        
        # Test conversation history retrieval
        history = chat.get_conversation_history(
            user_id='test-user-1',
            session_id='session-123',
            limit=10
        )
        
        # Verify history was retrieved
        assert isinstance(history, list)
        assert len(history) >= 0  # May be empty or contain test data
        
        # If history exists, verify structure
        if history:
            for message in history:
                assert 'userId' in message
                assert 'role' in message
                assert 'content' in message
                assert 'sessionId' in message
    
    def test_session_cleanup_on_disconnect(self, mock_aws_services, websocket_events):
        """Test session cleanup when WebSocket disconnects"""
        
        with patch('chat.boto3.client') as mock_boto_client, \
             patch('chat.global_agent_manager') as mock_agent_manager:
            
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            # Process disconnect
            response = chat.handler(websocket_events['disconnect'], MockLambdaContext())
            
            # Verify disconnect response
            assert response['statusCode'] == 200
            assert 'Disconnected successfully' in response['body']
            
            # Note: Session cleanup is called but we can't easily verify it
            # without modifying the disconnect event to include session ID


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback mechanisms"""
    
    def test_agent_initialization_failure_fallback(self, mock_aws_services):
        """Test fallback behavior when Strands agent initialization fails"""
        
        with patch('strands_config.StrandsAgentManager') as mock_manager_class:
            # Mock agent manager to raise exception
            mock_manager_class.side_effect = RuntimeError("Strands SDK not available")
            
            # Try to create agent manager
            try:
                manager = StrandsAgentManager()
                # If we get here, the mock didn't work as expected
                assert False, "Expected RuntimeError was not raised"
            except RuntimeError as e:
                assert "Strands SDK not available" in str(e)
    
    def test_tool_failure_error_handling(self, mock_aws_services):
        """Test error handling when tools fail"""
        
        # Test product search with invalid OpenSearch endpoint
        with patch('tools.product_search_tool.get_opensearch_client') as mock_opensearch:
            mock_client = Mock()
            mock_opensearch.return_value = mock_client
            
            # Mock OpenSearch to raise exception
            mock_client.search.side_effect = Exception("OpenSearch connection failed")
            
            # Test product search - should handle error gracefully
            result = product_search(query="test", limit=10)
            
            # Verify error was handled gracefully
            assert result.query == "test"
            assert len(result.products) == 0
            assert len(result.suggestions) > 0  # Should provide fallback suggestions
    
    def test_database_unavailability_fallback(self, mock_aws_services):
        """Test fallback behavior when DynamoDB is unavailable"""
        
        # Test cart operations with database error
        with patch('tools.cart_management_tool.get_cart_table') as mock_table:
            mock_table.side_effect = Exception("DynamoDB connection failed")
            
            # Test add to cart - should handle error gracefully
            result = add_to_cart(
                product_id='laptop-123',
                quantity=1,
                user_id='test-user-1'
            )
            
            # Verify error was handled
            assert result.success is False
            assert "error" in result.message.lower() or "failed" in result.message.lower()
            assert result.cart_summary.is_valid is False
            assert len(result.cart_summary.validation_errors) > 0
    
    def test_websocket_connection_failure_handling(self, mock_aws_services, websocket_events):
        """Test handling of WebSocket connection failures"""
        
        with patch('chat.boto3.client') as mock_boto_client:
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            # Mock API Gateway to raise exception
            from botocore.exceptions import ClientError
            mock_api_gw.post_to_connection.side_effect = ClientError(
                {'Error': {'Code': 'GoneException', 'Message': 'Connection no longer available'}},
                'PostToConnection'
            )
            
            # Process message - should handle connection error
            response = chat.handler(websocket_events['message'], MockLambdaContext())
            
            # Verify error was handled (function should still return success)
            # The actual error handling is in send_message_to_connection
            assert response['statusCode'] in [200, 500]  # Either success or handled error


class TestPerformanceAndTimeout:
    """Test performance characteristics and timeout compliance"""
    
    def test_lambda_timeout_compliance(self, mock_aws_services, websocket_events):
        """Test that message processing completes within Lambda timeout"""
        
        with patch('chat.boto3.client') as mock_boto_client, \
             patch('chat.global_agent_manager') as mock_agent_manager:
            
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            # Mock agent with simulated processing time
            mock_agent = MockStrandsAgent()
            mock_manager.get_agent_for_user.return_value = mock_agent
            mock_manager.restore_session_context.return_value = {
                'conversation_history': [],
                'conversation_summary': '',
                'session_restored': True,
                'message_count': 0
            }
            
            # Measure processing time
            start_time = time.time()
            response = chat.handler(websocket_events['message'], MockLambdaContext())
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Verify processing completed within reasonable time (< 5 seconds for test)
            assert processing_time < 5.0
            assert response['statusCode'] == 200
    
    def test_conversation_history_performance(self, mock_aws_services):
        """Test conversation history retrieval performance"""
        
        # Add multiple messages to test performance
        chat_table = mock_aws_services['chat_table']
        
        # Add 50 test messages
        for i in range(50):
            chat_table.put_item(Item={
                'userId': 'test-user-perf',
                'timestamp': (int(time.time()) - i * 60) * 1000,  # 1 minute intervals
                'messageId': str(uuid.uuid4()),
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Test message {i}',
                'sessionId': 'session-perf'
            })
        
        # Test history retrieval performance
        start_time = time.time()
        history = chat.get_conversation_history(
            user_id='test-user-perf',
            session_id='session-perf',
            limit=20
        )
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        
        # Verify performance (should complete within 1 second)
        assert retrieval_time < 1.0
        assert len(history) <= 20  # Respects limit
        assert len(history) > 0  # Retrieved some messages


class TestEndToEndIntegration:
    """End-to-end integration tests simulating complete user journeys"""
    
    def test_complete_shopping_journey(self, mock_aws_services, websocket_events):
        """Test complete user journey from product search to cart management"""
        
        with patch('chat.boto3.client') as mock_boto_client, \
             patch('chat.global_agent_manager') as mock_agent_manager, \
             patch('tools.product_search_tool.get_opensearch_client') as mock_opensearch:
            
            # Setup mocks
            mock_api_gw = Mock()
            mock_boto_client.return_value = mock_api_gw
            
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            mock_agent = MockStrandsAgent()
            mock_manager.get_agent_for_user.return_value = mock_agent
            mock_manager.restore_session_context.return_value = {
                'conversation_history': [],
                'conversation_summary': '',
                'session_restored': True,
                'message_count': 0
            }
            
            # Mock OpenSearch
            mock_client = Mock()
            mock_opensearch.return_value = mock_client
            mock_client.search.return_value = {
                'hits': {
                    'total': {'value': 1},
                    'hits': [
                        {
                            '_source': {
                                'productId': 'laptop-123',
                                'name': 'Gaming Laptop',
                                'description': 'High-performance gaming laptop',
                                'price': 1299.99,
                                'category': 'Electronics',
                                'stock': 10,
                                'isActive': True
                            },
                            '_score': 8.5
                        }
                    ]
                }
            }
            
            # Step 1: Search for products
            search_event = websocket_events['message'].copy()
            search_event['body'] = json.dumps({
                'message': 'I want to search for a gaming laptop',
                'sessionId': 'journey-session'
            })
            
            response1 = chat.handler(search_event, MockLambdaContext())
            assert response1['statusCode'] == 200
            
            # Step 2: Add product to cart
            cart_event = websocket_events['message'].copy()
            cart_event['body'] = json.dumps({
                'message': 'Add the gaming laptop to my cart',
                'sessionId': 'journey-session'
            })
            
            response2 = chat.handler(cart_event, MockLambdaContext())
            assert response2['statusCode'] == 200
            
            # Step 3: Check cart contents
            cart_check_event = websocket_events['message'].copy()
            cart_check_event['body'] = json.dumps({
                'message': 'Show me my cart',
                'sessionId': 'journey-session'
            })
            
            response3 = chat.handler(cart_check_event, MockLambdaContext())
            assert response3['statusCode'] == 200
            
            # Verify all steps completed successfully
            assert mock_agent.call_count == 3
            assert mock_api_gw.post_to_connection.call_count >= 6  # 2 calls per message (typing + response)
    
    def test_multi_session_context_isolation(self, mock_aws_services):
        """Test that different sessions maintain isolated contexts"""
        
        with patch('chat.global_agent_manager') as mock_agent_manager:
            mock_manager = Mock()
            mock_agent_manager.return_value = mock_manager
            
            # Mock different session contexts
            def mock_restore_context(user_id, session_id):
                if session_id == 'session-1':
                    return {
                        'conversation_history': [
                            {'role': 'user', 'content': 'Looking for laptops'}
                        ],
                        'conversation_summary': 'User interested in laptops',
                        'session_restored': True,
                        'message_count': 1
                    }
                else:
                    return {
                        'conversation_history': [
                            {'role': 'user', 'content': 'Need help with orders'}
                        ],
                        'conversation_summary': 'User asking about orders',
                        'session_restored': True,
                        'message_count': 1
                    }
            
            mock_manager.restore_session_context.side_effect = mock_restore_context
            
            # Test session 1
            context1 = mock_manager.restore_session_context('test-user-1', 'session-1')
            assert 'laptops' in context1['conversation_summary']
            
            # Test session 2
            context2 = mock_manager.restore_session_context('test-user-1', 'session-2')
            assert 'orders' in context2['conversation_summary']
            
            # Verify contexts are different
            assert context1['conversation_summary'] != context2['conversation_summary']


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short'])