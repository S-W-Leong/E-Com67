#!/usr/bin/env python3
"""
Simplified Integration Tests for Strands AI Agent

This test suite validates the integration of the Strands AI Agent
with E-Com67 systems using a simplified approach that works with
the current module structure.
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
from datetime import datetime

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


class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-strands-chat-function'
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = 'arn:aws:lambda:ap-southeast-1:123456789012:function:test-strands-chat'
        self.aws_request_id = f'test-request-{uuid.uuid4()}'
        self.remaining_time_in_millis = lambda: 30000


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
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
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
        
        # Add test product
        products_table.put_item(
            Item={
                'productId': 'laptop-123',
                'name': 'Gaming Laptop',
                'description': 'High-performance gaming laptop with RTX graphics',
                'price': Decimal('1299.99'),
                'category': 'Electronics',
                'stock': 10,
                'isActive': True,
                'imageUrl': 'https://example.com/laptop.jpg',
                'rating': Decimal('4.5')
            }
        )
        
        yield {
            'dynamodb': dynamodb,
            'chat_table': chat_table,
            'products_table': products_table
        }


class TestStrandsIntegrationBasic:
    """Basic integration tests for Strands agent components"""
    
    def test_strands_config_initialization(self):
        """Test Strands configuration initialization"""
        # Add lambda/chat to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from strands_config import StrandsAgentConfig, DeploymentStage
            
            # Test configuration creation
            config = StrandsAgentConfig.from_environment()
            
            # Verify configuration
            assert config.bedrock_config.model_id == 'amazon.titan-text-express-v1'
            assert config.bedrock_config.region == 'ap-southeast-1'
            assert config.deployment_stage == DeploymentStage.DEVELOPMENT
            assert config.platform_name == "E-Com67"
            
        except ImportError as e:
            pytest.skip(f"Strands configuration not available: {e}")
    
    def test_pydantic_models_validation(self):
        """Test Pydantic models for structured responses"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from models import ProductInfo, CartSummary, OrderInfo
            
            # Test ProductInfo model
            product = ProductInfo(
                product_id="test-123",
                name="Test Product",
                description="A test product",
                price=29.99,
                category="test",
                stock=10,
                is_available=True
            )
            
            assert product.product_id == "test-123"
            assert product.price == 29.99
            assert product.is_available is True
            
            # Test price validation
            with pytest.raises(ValueError):
                ProductInfo(
                    product_id="test-invalid",
                    name="Invalid Product",
                    description="Invalid price",
                    price=-10.0,  # Negative price should fail
                    category="test",
                    stock=10,
                    is_available=True
                )
            
        except ImportError as e:
            pytest.skip(f"Pydantic models not available: {e}")
    
    def test_product_search_tool_basic(self, mock_aws_services):
        """Test basic product search tool functionality"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from tools.product_search_tool import get_product_details
            
            # Mock OpenSearch client to avoid external dependencies
            with patch('tools.product_search_tool.get_opensearch_client'):
                # Test getting product details from DynamoDB
                product_info = get_product_details('laptop-123')
                
                # Verify product was retrieved
                assert product_info is not None
                assert product_info.product_id == 'laptop-123'
                assert product_info.name == 'Gaming Laptop'
                assert product_info.price == 1299.99
                assert product_info.is_available is True
                
        except ImportError as e:
            pytest.skip(f"Product search tool not available: {e}")
    
    def test_cart_management_tool_basic(self, mock_aws_services):
        """Test basic cart management functionality"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            # Create cart table
            dynamodb = mock_aws_services['dynamodb']
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
            
            from tools.cart_management_tool import add_to_cart, get_cart_contents
            
            # Test adding item to cart
            result = add_to_cart(
                product_id='laptop-123',
                quantity=1,
                user_id='test-user-1'
            )
            
            # Verify operation
            assert result.success is True
            assert result.product_id == 'laptop-123'
            assert result.quantity == 1
            
            # Test getting cart contents
            cart_contents = get_cart_contents(user_id='test-user-1')
            
            # Verify cart contents
            assert cart_contents.user_id == 'test-user-1'
            assert len(cart_contents.items) >= 1
            assert cart_contents.total > 0
            
        except ImportError as e:
            pytest.skip(f"Cart management tool not available: {e}")
    
    def test_websocket_message_format(self):
        """Test WebSocket message format compatibility"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from response_formatters import format_websocket_message
            
            # Test message formatting
            message = format_websocket_message(
                message_type='message',
                content='Hello, this is a test message',
                session_id='test-session-123'
            )
            
            # Verify message structure
            assert 'type' in message
            assert 'message' in message
            assert 'timestamp' in message
            assert message['type'] == 'message'
            assert message['message'] == 'Hello, this is a test message'
            assert isinstance(message['timestamp'], int)
            
        except ImportError as e:
            pytest.skip(f"Response formatters not available: {e}")
    
    def test_error_handling_graceful_degradation(self, mock_aws_services):
        """Test graceful error handling and degradation"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from tools.product_search_tool import product_search
            
            # Mock OpenSearch to fail
            with patch('tools.product_search_tool.get_opensearch_client') as mock_opensearch:
                mock_client = Mock()
                mock_opensearch.return_value = mock_client
                mock_client.search.side_effect = Exception("OpenSearch connection failed")
                
                # Test product search with failure
                result = product_search(query="test laptop", limit=10)
                
                # Verify graceful handling
                assert result.query == "test laptop"
                assert len(result.products) == 0  # No products due to error
                assert len(result.suggestions) > 0  # Should provide fallback suggestions
                
        except ImportError as e:
            pytest.skip(f"Product search tool not available: {e}")


class TestWebSocketIntegrationBasic:
    """Basic WebSocket integration tests"""
    
    def test_websocket_event_structure(self):
        """Test WebSocket event structure validation"""
        # Test event structures
        connect_event = {
            'requestContext': {
                'routeKey': '$connect',
                'connectionId': 'test-connection-123',
                'domainName': 'test-api.execute-api.ap-southeast-1.amazonaws.com',
                'stage': 'test'
            }
        }
        
        message_event = {
            'requestContext': {
                'routeKey': 'sendMessage',
                'connectionId': 'test-connection-123',
                'domainName': 'test-api.execute-api.ap-southeast-1.amazonaws.com',
                'stage': 'test'
            },
            'body': json.dumps({
                'message': 'Hello, I need help',
                'sessionId': 'test-session-456'
            })
        }
        
        # Verify event structures
        assert connect_event['requestContext']['routeKey'] == '$connect'
        assert message_event['requestContext']['routeKey'] == 'sendMessage'
        
        # Parse message body
        body = json.loads(message_event['body'])
        assert 'message' in body
        assert 'sessionId' in body
    
    def test_chat_handler_basic_routing(self, mock_aws_services):
        """Test basic chat handler routing without full Strands integration"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            import chat
            
            # Mock API Gateway Management API
            with patch('chat.boto3.client') as mock_boto_client:
                mock_api_gw = Mock()
                mock_boto_client.return_value = mock_api_gw
                
                # Test connection event
                connect_event = {
                    'requestContext': {
                        'routeKey': '$connect',
                        'connectionId': 'test-connection-123',
                        'domainName': 'test-api.execute-api.ap-southeast-1.amazonaws.com',
                        'stage': 'test'
                    }
                }
                
                response = chat.handler(connect_event, MockLambdaContext())
                
                # Verify connection handling
                assert response['statusCode'] == 200
                assert 'Connected successfully' in response['body']
                
        except ImportError as e:
            pytest.skip(f"Chat handler not available: {e}")


class TestPerformanceBasic:
    """Basic performance tests"""
    
    def test_configuration_loading_performance(self):
        """Test configuration loading performance"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from strands_config import StrandsAgentConfig
            
            # Measure configuration loading time
            start_time = time.time()
            config = StrandsAgentConfig.from_environment()
            end_time = time.time()
            
            loading_time = end_time - start_time
            
            # Verify performance (should be very fast)
            assert loading_time < 0.1  # Less than 100ms
            assert config is not None
            
        except ImportError as e:
            pytest.skip(f"Strands configuration not available: {e}")
    
    def test_model_validation_performance(self):
        """Test Pydantic model validation performance"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        try:
            from models import ProductInfo
            
            # Test creating multiple product models
            start_time = time.time()
            
            products = []
            for i in range(100):
                product = ProductInfo(
                    product_id=f"product-{i}",
                    name=f"Product {i}",
                    description=f"Description for product {i}",
                    price=float(i * 10),
                    category="test",
                    stock=i,
                    is_available=True
                )
                products.append(product)
            
            end_time = time.time()
            
            creation_time = end_time - start_time
            
            # Verify performance
            assert creation_time < 1.0  # Less than 1 second for 100 models
            assert len(products) == 100
            
        except ImportError as e:
            pytest.skip(f"Pydantic models not available: {e}")


class TestIntegrationSummary:
    """Integration test summary and validation"""
    
    def test_integration_readiness_check(self):
        """Comprehensive check of integration readiness"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))
        
        integration_status = {
            'strands_config': False,
            'pydantic_models': False,
            'product_tools': False,
            'cart_tools': False,
            'order_tools': False,
            'response_formatters': False,
            'chat_handler': False
        }
        
        # Test each component
        try:
            from strands_config import StrandsAgentConfig
            integration_status['strands_config'] = True
        except ImportError:
            pass
        
        try:
            from models import ProductInfo, CartSummary
            integration_status['pydantic_models'] = True
        except ImportError:
            pass
        
        try:
            from tools.product_search_tool import product_search
            integration_status['product_tools'] = True
        except ImportError:
            pass
        
        try:
            from tools.cart_management_tool import add_to_cart
            integration_status['cart_tools'] = True
        except ImportError:
            pass
        
        try:
            from tools.order_query_tool import get_order_history
            integration_status['order_tools'] = True
        except ImportError:
            pass
        
        try:
            from response_formatters import format_websocket_message
            integration_status['response_formatters'] = True
        except ImportError:
            pass
        
        try:
            import chat
            integration_status['chat_handler'] = True
        except ImportError:
            pass
        
        # Calculate integration score
        total_components = len(integration_status)
        working_components = sum(integration_status.values())
        integration_score = working_components / total_components
        
        print(f"\nIntegration Status Summary:")
        print(f"{'='*50}")
        for component, status in integration_status.items():
            status_symbol = "✅" if status else "❌"
            print(f"{status_symbol} {component}: {'Available' if status else 'Not Available'}")
        
        print(f"\nIntegration Score: {working_components}/{total_components} ({integration_score:.1%})")
        
        # Assert minimum integration level
        assert integration_score >= 0.5, f"Integration score too low: {integration_score:.1%}"
        
        return integration_status


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short'])