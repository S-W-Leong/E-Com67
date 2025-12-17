"""
Simple test for Product CRUD Function to validate basic functionality
"""

import json
import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import MagicMock, patch

# Set up test environment
os.environ['PRODUCTS_TABLE_NAME'] = 'test-products'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'test-product-crud'
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'Test'
os.environ['LOG_LEVEL'] = 'INFO'

# Import the function under test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'product_crud'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'layers', 'utils', 'python'))


@pytest.fixture
def lambda_context():
    """Create a mock Lambda context"""
    context = MagicMock()
    context.function_name = 'test-product-crud'
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-product-crud'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing"""
    with mock_aws():
        # Import here to ensure mocking is active
        from product_crud import handler
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create products table
        table = dynamodb.create_table(
            TableName='test-products',
            KeySchema=[
                {'AttributeName': 'productId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'productId', 'AttributeType': 'S'},
                {'AttributeName': 'category', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'category-index',
                    'KeySchema': [
                        {'AttributeName': 'category', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        # Patch the products_table in the module
        with patch('product_crud.products_table', table):
            yield handler


def test_create_product_success(dynamodb_table, lambda_context):
    """Test successful product creation"""
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'name': 'Test Product',
            'description': 'A test product',
            'price': 29.99,
            'category': 'Electronics',
            'stock': 100
        })
    }
    
    response = dynamodb_table(event, lambda_context)
    
    assert response['statusCode'] == 201
    body = json.loads(response['body'])
    assert body['name'] == 'Test Product'
    assert body['price'] == 29.99
    assert 'productId' in body
    assert 'createdAt' in body


def test_get_product_not_found(dynamodb_table, lambda_context):
    """Test product retrieval for non-existent product"""
    event = {
        'httpMethod': 'GET',
        'pathParameters': {'id': 'non-existent-id'}
    }
    
    response = dynamodb_table(event, lambda_context)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error']['code'] == 'PRODUCT_NOT_FOUND'


def test_list_products_empty(dynamodb_table, lambda_context):
    """Test product listing when no products exist"""
    event = {
        'httpMethod': 'GET'
    }
    
    response = dynamodb_table(event, lambda_context)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['count'] == 0
    assert len(body['products']) == 0


def test_create_product_validation_error(dynamodb_table, lambda_context):
    """Test product creation with invalid data"""
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'name': 'Test Product',
            # Missing required fields
            'price': -10  # Invalid price
        })
    }
    
    response = dynamodb_table(event, lambda_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'VALIDATION_ERROR'


def test_cors_options_request(dynamodb_table, lambda_context):
    """Test CORS OPTIONS request handling"""
    event = {
        'httpMethod': 'OPTIONS'
    }
    
    response = dynamodb_table(event, lambda_context)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers']