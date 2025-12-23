"""
Unit tests for the Chat Lambda function.

Tests basic chat functionality including connection handling,
message processing, and AI response generation.
"""

import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
from decimal import Decimal
import os
import sys


class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.aws_request_id = 'test-request-id'

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'chat'))

# Mock environment variables
os.environ['CHAT_HISTORY_TABLE_NAME'] = 'test-chat-history'
os.environ['PRODUCTS_TABLE_NAME'] = 'test-products'
os.environ['BEDROCK_MODEL_ID'] = 'amazon.titan-text-express-v1'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'E-Com67-Test'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'chat-test'

import chat


@pytest.fixture
def websocket_connect_event():
    """Sample WebSocket connect event"""
    return {
        'requestContext': {
            'routeKey': '$connect',
            'connectionId': 'test-connection-123',
            'domainName': 'test-api.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        }
    }


@pytest.fixture
def websocket_message_event():
    """Sample WebSocket message event"""
    return {
        'requestContext': {
            'routeKey': 'sendMessage',
            'connectionId': 'test-connection-123',
            'domainName': 'test-api.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'message': 'Hello, I need help finding a laptop',
            'sessionId': 'test-session-456'
        })
    }


@pytest.fixture
def websocket_disconnect_event():
    """Sample WebSocket disconnect event"""
    return {
        'requestContext': {
            'routeKey': '$disconnect',
            'connectionId': 'test-connection-123',
            'domainName': 'test-api.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        }
    }


@mock_aws
def test_handle_connect(websocket_connect_event):
    """Test WebSocket connection handling"""
    # Create mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Mock API Gateway Management API
    with patch('chat.apigateway_management') as mock_api_gw:
        mock_api_gw.post_to_connection = MagicMock()
        
        # Mock the global apigateway_management assignment
        with patch('chat.boto3.client') as mock_boto_client:
            mock_boto_client.return_value = mock_api_gw
            
            response = chat.handler(websocket_connect_event, MockLambdaContext())
            
            assert response['statusCode'] == 200
            assert 'Connected successfully' in response['body']
            
            # Verify welcome message was sent
            mock_api_gw.post_to_connection.assert_called_once()
            call_args = mock_api_gw.post_to_connection.call_args
            assert call_args[1]['ConnectionId'] == 'test-connection-123'
            
            # Parse the message data
            message_data = json.loads(call_args[1]['Data'])
            assert message_data['type'] == 'welcome'
            assert 'Welcome to E-Com67' in message_data['message']


@mock_aws
def test_handle_disconnect(websocket_disconnect_event):
    """Test WebSocket disconnection handling"""
    with patch('chat.boto3.client'):
        response = chat.handler(websocket_disconnect_event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        assert 'Disconnected successfully' in response['body']


@mock_aws
def test_handle_send_message_basic(websocket_message_event):
    """Test basic message handling without Bedrock"""
    # Create mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create chat history table
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
    
    # Add a test product
    products_table.put_item(
        Item={
            'productId': 'laptop-123',
            'name': 'Gaming Laptop',
            'description': 'High-performance gaming laptop with RTX graphics',
            'price': Decimal('1299.99'),
            'category': 'Electronics'
        }
    )
    
    # Mock API Gateway Management API and Bedrock
    with patch('chat.apigateway_management') as mock_api_gw, \
         patch('chat.bedrock_runtime') as mock_bedrock, \
         patch('chat.boto3.client') as mock_boto_client:
        
        mock_api_gw.post_to_connection = MagicMock()
        mock_boto_client.return_value = mock_api_gw
        
        # Mock Bedrock response
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': 'I can help you find a great laptop! Based on our catalog, I recommend the Gaming Laptop for $1299.99.'}]
            }).encode())
        }
        
        response = chat.handler(websocket_message_event, MockLambdaContext())
        
        assert response['statusCode'] == 200
        assert 'Message processed successfully' in response['body']
        
        # Verify message was sent back to user
        mock_api_gw.post_to_connection.assert_called()
        call_args = mock_api_gw.post_to_connection.call_args
        assert call_args[1]['ConnectionId'] == 'test-connection-123'
        
        # Parse the response message
        message_data = json.loads(call_args[1]['Data'])
        assert message_data['type'] == 'message'
        assert 'laptop' in message_data['message'].lower()
        
        # Verify Bedrock was called
        mock_bedrock.invoke_model.assert_called_once()


def test_extract_user_id():
    """Test user ID extraction from event"""
    event_with_auth = {
        'requestContext': {
            'authorizer': {
                'principalId': 'user-123'
            }
        }
    }
    
    event_without_auth = {
        'requestContext': {}
    }
    
    assert chat.extract_user_id(event_with_auth) == 'user-123'
    assert chat.extract_user_id(event_without_auth) == 'anonymous'


@mock_aws
def test_get_relevant_products():
    """Test product retrieval for RAG context"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
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
    
    # Add test products
    products_table.put_item(
        Item={
            'productId': 'laptop-123',
            'name': 'Gaming Laptop',
            'description': 'High-performance gaming laptop',
            'price': Decimal('1299.99'),
            'category': 'Electronics'
        }
    )
    
    products_table.put_item(
        Item={
            'productId': 'phone-456',
            'name': 'Smartphone',
            'description': 'Latest smartphone with great camera',
            'price': Decimal('799.99'),
            'category': 'Electronics'
        }
    )
    
    # Mock the products_table in the chat module
    with patch('chat.products_table', products_table):
        # Test product search
        products = chat.get_relevant_products('laptop')
        assert len(products) >= 1
        assert any('laptop' in p.get('name', '').lower() for p in products)


def test_create_response():
    """Test response creation utility"""
    response = chat.create_response(200, {'message': 'success'})
    
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['message'] == 'success'


if __name__ == '__main__':
    pytest.main([__file__])