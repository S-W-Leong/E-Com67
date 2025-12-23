"""
Property-based tests for the Chat Lambda function.

Tests universal properties that should hold across all valid inputs
for the AI chat functionality.
"""

import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock
from decimal import Decimal
import os
import sys
from hypothesis import given, strategies as st, settings

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


class MockLambdaContext:
    """Mock Lambda context for testing"""
    def __init__(self):
        self.function_name = 'test-function'
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        self.aws_request_id = 'test-request-id'


# Hypothesis strategies for generating test data
connection_ids = st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
user_messages = st.text(min_size=1, max_size=500).filter(lambda x: x.strip())
session_ids = st.uuids().map(str)
domain_names = st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'))).map(lambda x: f"{x}.execute-api.us-east-1.amazonaws.com")


@given(connection_ids, domain_names)
@settings(max_examples=20)
def test_websocket_connect_always_returns_success(connection_id, domain_name):
    """
    **Feature: e-com67-platform, Property 24: Chat Connection Establishment**
    
    Property: For any WebSocket connection request, the system should establish 
    a connection and return a success response.
    **Validates: Requirements 7.1**
    """
    event = {
        'requestContext': {
            'routeKey': '$connect',
            'connectionId': connection_id,
            'domainName': domain_name,
            'stage': 'prod'
        }
    }
    
    with patch('chat.apigateway_management') as mock_api_gw, \
         patch('chat.boto3.client') as mock_boto_client:
        
        mock_api_gw.post_to_connection = MagicMock()
        mock_boto_client.return_value = mock_api_gw
        
        response = chat.handler(event, MockLambdaContext())
        
        # Property: Connection always succeeds
        assert response['statusCode'] == 200
        assert 'Connected successfully' in response['body']
        
        # Property: Welcome message is always sent
        mock_api_gw.post_to_connection.assert_called_once()
        call_args = mock_api_gw.post_to_connection.call_args
        assert call_args[1]['ConnectionId'] == connection_id
        
        message_data = json.loads(call_args[1]['Data'])
        assert message_data['type'] == 'welcome'
        assert 'Welcome to E-Com67' in message_data['message']


@given(connection_ids, domain_names)
@settings(max_examples=20)
def test_websocket_disconnect_always_returns_success(connection_id, domain_name):
    """
    **Feature: e-com67-platform, Property 24: Chat Connection Management**
    
    Property: For any WebSocket disconnection request, the system should 
    handle the disconnection gracefully and return a success response.
    **Validates: Requirements 7.1**
    """
    event = {
        'requestContext': {
            'routeKey': '$disconnect',
            'connectionId': connection_id,
            'domainName': domain_name,
            'stage': 'prod'
        }
    }
    
    with patch('chat.boto3.client'):
        response = chat.handler(event, MockLambdaContext())
        
        # Property: Disconnection always succeeds
        assert response['statusCode'] == 200
        assert 'Disconnected successfully' in response['body']


@given(user_messages, session_ids)
@settings(max_examples=10)
@mock_aws
def test_message_processing_always_generates_response(user_message, session_id):
    """
    **Feature: e-com67-platform, Property 25: Message Processing Context**
    
    Property: For any valid user message, the AI assistant should process 
    the message and generate a response.
    **Validates: Requirements 7.2**
    """
    # Create mock DynamoDB tables
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
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
    
    event = {
        'requestContext': {
            'routeKey': 'sendMessage',
            'connectionId': 'test-connection-123',
            'domainName': 'test-api.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'message': user_message,
            'sessionId': session_id
        })
    }
    
    with patch('chat.apigateway_management') as mock_api_gw, \
         patch('chat.bedrock_runtime') as mock_bedrock, \
         patch('chat.boto3.client') as mock_boto_client, \
         patch('chat.chat_history_table', chat_table), \
         patch('chat.products_table', products_table):
        
        mock_api_gw.post_to_connection = MagicMock()
        mock_boto_client.return_value = mock_api_gw
        
        # Mock Bedrock response
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': f'I understand you said: {user_message[:50]}...'}]
            }).encode())
        }
        
        response = chat.handler(event, MockLambdaContext())
        
        # Property: Message processing always succeeds
        assert response['statusCode'] == 200
        assert 'Message processed successfully' in response['body']
        
        # Property: Response is always sent back to user
        mock_api_gw.post_to_connection.assert_called()
        call_args = mock_api_gw.post_to_connection.call_args
        assert call_args[1]['ConnectionId'] == 'test-connection-123'
        
        message_data = json.loads(call_args[1]['Data'])
        assert message_data['type'] == 'message'
        assert message_data['sessionId'] == session_id
        assert len(message_data['message']) > 0
        
        # Property: Bedrock is always invoked for AI response
        mock_bedrock.invoke_model.assert_called_once()


@given(st.integers(min_value=200, max_value=599), st.dictionaries(st.text(), st.text()))
@settings(max_examples=50)
def test_create_response_format_consistency(status_code, body_dict):
    """
    **Feature: e-com67-platform, Property: Response Format Consistency**
    
    Property: For any status code and body dictionary, create_response should 
    return a properly formatted Lambda response.
    **Validates: General system reliability**
    """
    response = chat.create_response(status_code, body_dict)
    
    # Property: Response always has correct structure
    assert isinstance(response, dict)
    assert 'statusCode' in response
    assert 'body' in response
    
    # Property: Status code is preserved
    assert response['statusCode'] == status_code
    
    # Property: Body is valid JSON
    parsed_body = json.loads(response['body'])
    assert parsed_body == body_dict


@given(st.text(min_size=1, max_size=100))
@settings(max_examples=30)
def test_extract_user_id_consistency(principal_id):
    """
    **Feature: e-com67-platform, Property: User ID Extraction Consistency**
    
    Property: For any event with authorizer context, extract_user_id should 
    return the principal ID, otherwise return 'anonymous'.
    **Validates: Authentication handling**
    """
    # Test with authorizer context
    event_with_auth = {
        'requestContext': {
            'authorizer': {
                'principalId': principal_id
            }
        }
    }
    
    # Test without authorizer context
    event_without_auth = {
        'requestContext': {}
    }
    
    # Property: Principal ID is extracted when present
    assert chat.extract_user_id(event_with_auth) == principal_id
    
    # Property: Anonymous is returned when no auth context
    assert chat.extract_user_id(event_without_auth) == 'anonymous'


if __name__ == '__main__':
    pytest.main([__file__])