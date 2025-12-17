"""
Property-Based Tests for Product CRUD Function

Tests the correctness properties defined in the design document.
"""

import json
import os
import pytest
import boto3
from moto import mock_aws
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.strategies import composite

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
def dynamodb_handler(aws_credentials):
    """Create a mock DynamoDB table and return patched handler"""
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


# Property-based test generators
@composite
def valid_product_data(draw):
    """Generate valid product data for property-based testing"""
    return {
        'name': draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        'description': draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip())),
        'price': draw(st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)),
        'category': draw(st.sampled_from(['Electronics', 'Books', 'Clothing', 'Home', 'Sports'])),
        'stock': draw(st.integers(min_value=0, max_value=1000)),
        'tags': draw(st.lists(st.text(min_size=1, max_size=20), max_size=5)),
        'imageUrl': draw(st.text(max_size=200))
    }


@composite
def invalid_product_data(draw):
    """Generate invalid product data for property-based testing"""
    invalid_cases = [
        # Missing required fields
        {'description': 'Missing name', 'price': 10.0, 'category': 'Electronics'},
        {'name': 'Missing description', 'price': 10.0, 'category': 'Electronics'},
        {'name': 'Missing price', 'description': 'Desc', 'category': 'Electronics'},
        {'name': 'Missing category', 'description': 'Desc', 'price': 10.0},
        # Invalid price
        {'name': 'Invalid price', 'description': 'Desc', 'price': -1.0, 'category': 'Electronics'},
        # Invalid stock
        {'name': 'Invalid stock', 'description': 'Desc', 'price': 10.0, 'category': 'Electronics', 'stock': -1},
    ]
    
    return draw(st.sampled_from(invalid_cases))


@given(product_data=valid_product_data())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_product_creation_uniqueness(dynamodb_handler, lambda_context, product_data):
    """
    **Feature: e-com67-platform, Property 5: Product Creation Uniqueness**
    For any valid product data, product creation should generate a unique product ID and store the product successfully
    **Validates: Requirements 2.1**
    """
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(product_data)
    }
    
    response = dynamodb_handler(event, lambda_context)
    
    # Should create successfully
    assert response['statusCode'] == 201
    
    body = json.loads(response['body'])
    
    # Should have unique product ID
    assert 'productId' in body
    assert body['productId'] is not None
    assert len(body['productId']) > 0
    
    # Should store all provided data correctly
    assert body['name'] == product_data['name']
    assert body['description'] == product_data['description']
    assert abs(body['price'] - product_data['price']) < 0.01  # Float comparison
    assert body['category'] == product_data['category']
    
    # Should have timestamps
    assert 'createdAt' in body
    assert 'updatedAt' in body
    assert body['createdAt'] == body['updatedAt']  # Should be same on creation


@given(invalid_data=invalid_product_data())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_product_validation_rejection(dynamodb_handler, lambda_context, invalid_data):
    """
    **Feature: e-com67-platform, Property 7: Product Update Validation**
    For any invalid product data, the system should reject creation with appropriate error
    **Validates: Requirements 2.3**
    """
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(invalid_data)
    }
    
    response = dynamodb_handler(event, lambda_context)
    
    # Should reject invalid data
    assert response['statusCode'] == 400
    
    body = json.loads(response['body'])
    assert 'error' in body
    assert body['error']['code'] == 'VALIDATION_ERROR'


@given(product_data=valid_product_data())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_product_retrieval_consistency(dynamodb_handler, lambda_context, product_data):
    """
    **Feature: e-com67-platform, Property 6: Product Listing Consistency**
    For any created product, retrieval should return the same data that was stored
    **Validates: Requirements 2.2**
    """
    # Create product
    create_event = {
        'httpMethod': 'POST',
        'body': json.dumps(product_data)
    }
    
    create_response = dynamodb_handler(create_event, lambda_context)
    assert create_response['statusCode'] == 201
    
    created_product = json.loads(create_response['body'])
    product_id = created_product['productId']
    
    # Retrieve product
    get_event = {
        'httpMethod': 'GET',
        'pathParameters': {'id': product_id}
    }
    
    get_response = dynamodb_handler(get_event, lambda_context)
    assert get_response['statusCode'] == 200
    
    retrieved_product = json.loads(get_response['body'])
    
    # Should return same data
    assert retrieved_product['productId'] == product_id
    assert retrieved_product['name'] == product_data['name']
    assert retrieved_product['description'] == product_data['description']
    assert abs(retrieved_product['price'] - product_data['price']) < 0.01
    assert retrieved_product['category'] == product_data['category']


@given(
    original_data=valid_product_data(),
    update_data=valid_product_data()
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_product_update_consistency(dynamodb_handler, lambda_context, original_data, update_data):
    """
    **Feature: e-com67-platform, Property 7: Product Update Validation**
    For any valid product update data, the system should validate changes and update the product record correctly
    **Validates: Requirements 2.3**
    """
    # Create original product
    create_event = {
        'httpMethod': 'POST',
        'body': json.dumps(original_data)
    }
    
    create_response = dynamodb_handler(create_event, lambda_context)
    assert create_response['statusCode'] == 201
    
    created_product = json.loads(create_response['body'])
    product_id = created_product['productId']
    original_created_at = created_product['createdAt']
    
    # Update product
    update_event = {
        'httpMethod': 'PUT',
        'pathParameters': {'id': product_id},
        'body': json.dumps(update_data)
    }
    
    update_response = dynamodb_handler(update_event, lambda_context)
    assert update_response['statusCode'] == 200
    
    updated_product = json.loads(update_response['body'])
    
    # Should maintain product ID and creation time
    assert updated_product['productId'] == product_id
    assert updated_product['createdAt'] == original_created_at
    
    # Should update the data
    assert updated_product['name'] == update_data['name']
    assert updated_product['description'] == update_data['description']
    assert abs(updated_product['price'] - update_data['price']) < 0.01
    assert updated_product['category'] == update_data['category']
    
    # Should update timestamp
    assert updated_product['updatedAt'] >= original_created_at


@given(product_data=valid_product_data())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_product_deletion_cleanup(dynamodb_handler, lambda_context, product_data):
    """
    **Feature: e-com67-platform, Property 8: Product Deletion Cleanup**
    For any product deletion request, the system should remove the product and handle existing cart references appropriately
    **Validates: Requirements 2.4**
    """
    # Create product
    create_event = {
        'httpMethod': 'POST',
        'body': json.dumps(product_data)
    }
    
    create_response = dynamodb_handler(create_event, lambda_context)
    assert create_response['statusCode'] == 201
    
    created_product = json.loads(create_response['body'])
    product_id = created_product['productId']
    
    # Delete product
    delete_event = {
        'httpMethod': 'DELETE',
        'pathParameters': {'id': product_id}
    }
    
    delete_response = dynamodb_handler(delete_event, lambda_context)
    assert delete_response['statusCode'] == 200
    
    # Product should not appear in listings (soft delete)
    list_event = {'httpMethod': 'GET'}
    list_response = dynamodb_handler(list_event, lambda_context)
    assert list_response['statusCode'] == 200
    
    list_body = json.loads(list_response['body'])
    product_ids = [p['productId'] for p in list_body['products']]
    assert product_id not in product_ids


@given(products_data=st.lists(valid_product_data(), min_size=1, max_size=10))
@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_category_filtering_consistency(dynamodb_handler, lambda_context, products_data):
    """
    **Feature: e-com67-platform, Property 6: Product Listing Consistency**
    For any product listing request with category filter, the system should return only products matching the criteria
    **Validates: Requirements 2.2**
    """
    # Create products
    created_products = []
    for product_data in products_data:
        create_event = {
            'httpMethod': 'POST',
            'body': json.dumps(product_data)
        }
        
        create_response = dynamodb_handler(create_event, lambda_context)
        assert create_response['statusCode'] == 201
        
        created_product = json.loads(create_response['body'])
        created_products.append(created_product)
    
    # Get unique categories from created products
    categories = list(set(p['category'] for p in created_products))
    
    for category in categories:
        # List products by category
        list_event = {
            'httpMethod': 'GET',
            'queryStringParameters': {'category': category}
        }
        
        list_response = dynamodb_handler(list_event, lambda_context)
        assert list_response['statusCode'] == 200
        
        list_body = json.loads(list_response['body'])
        
        # All returned products should match the category
        for product in list_body['products']:
            assert product['category'] == category
        
        # Should return at least the products we created in that category
        expected_count = len([p for p in created_products if p['category'] == category])
        assert list_body['count'] >= expected_count
        
        # Verify that our created products are in the results
        created_product_ids = {p['productId'] for p in created_products if p['category'] == category}
        returned_product_ids = {p['productId'] for p in list_body['products']}
        assert created_product_ids.issubset(returned_product_ids)