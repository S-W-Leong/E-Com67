"""
Tests for Orders Lambda Function

Tests order retrieval and management functionality including:
- User order history queries with pagination
- Order status tracking and updates
- Order detail retrieval with complete information
- Order search and filtering
"""

import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import base64

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'orders'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layers', 'utils', 'python'))

# Mock AWS services before importing
with patch('boto3.resource'):
    from orders import handler, OrdersService


class TestOrdersService:
    """Test OrdersService class methods"""
    
    @patch('orders.get_orders_table')
    def test_get_user_orders_success(self, mock_orders_table):
        """Test successful user order retrieval"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB query response
        mock_table.query.return_value = {
            'Items': [
                {
                    'orderId': 'order123',
                    'userId': 'user123',
                    'items': [{'productId': 'prod1', 'name': 'Test Product', 'price': Decimal('29.99'), 'quantity': 2}],
                    'subtotal': Decimal('59.98'),
                    'taxAmount': Decimal('4.80'),
                    'totalAmount': Decimal('64.78'),
                    'status': 'completed',
                    'timestamp': 1234567890,
                    'createdAt': 1234567890,
                    'updatedAt': 1234567890
                },
                {
                    'orderId': 'order456',
                    'userId': 'user123',
                    'items': [{'productId': 'prod2', 'name': 'Another Product', 'price': Decimal('19.99'), 'quantity': 1}],
                    'subtotal': Decimal('19.99'),
                    'taxAmount': Decimal('1.60'),
                    'totalAmount': Decimal('21.59'),
                    'status': 'processing',
                    'timestamp': 1234567800,
                    'createdAt': 1234567800,
                    'updatedAt': 1234567800
                }
            ]
        }
        
        result = OrdersService.get_user_orders('user123', limit=20)
        
        # Verify result structure
        assert 'orders' in result
        assert 'nextToken' in result
        assert 'hasMore' in result
        assert 'totalReturned' in result
        
        # Verify orders data
        orders = result['orders']
        assert len(orders) == 2
        assert orders[0]['orderId'] == 'order123'
        assert orders[0]['userId'] == 'user123'
        assert orders[0]['status'] == 'completed'
        assert isinstance(orders[0]['totalAmount'], float)  # Decimal converted to float
        assert 'createdAtFormatted' in orders[0]
        assert 'updatedAtFormatted' in orders[0]
        
        # Verify pagination
        assert result['hasMore'] is False
        assert result['nextToken'] is None
        assert result['totalReturned'] == 2
        
        # Verify DynamoDB query parameters
        mock_table.query.assert_called_once()
        call_args = mock_table.query.call_args[1]
        assert call_args['IndexName'] == 'userId-timestamp-index'
        assert call_args['ScanIndexForward'] is False  # Newest first
        assert call_args['Limit'] == 20
    
    @patch('orders.get_orders_table')
    def test_get_user_orders_with_pagination(self, mock_orders_table):
        """Test user order retrieval with pagination"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB query response with pagination
        mock_table.query.return_value = {
            'Items': [
                {
                    'orderId': 'order123',
                    'userId': 'user123',
                    'items': [],
                    'subtotal': Decimal('59.98'),
                    'taxAmount': Decimal('4.80'),
                    'totalAmount': Decimal('64.78'),
                    'status': 'completed',
                    'timestamp': 1234567890,
                    'createdAt': 1234567890,
                    'updatedAt': 1234567890
                }
            ],
            'LastEvaluatedKey': {
                'userId': 'user123',
                'timestamp': 1234567890,
                'orderId': 'order123'
            }
        }
        
        result = OrdersService.get_user_orders('user123', limit=1)
        
        # Verify pagination token is created
        assert result['hasMore'] is True
        assert result['nextToken'] is not None
        
        # Verify token can be decoded
        decoded_token = json.loads(base64.b64decode(result['nextToken']).decode('utf-8'))
        assert 'userId' in decoded_token
        assert 'timestamp' in decoded_token
        assert 'orderId' in decoded_token
    
    @patch('orders.get_orders_table')
    def test_get_user_orders_with_invalid_pagination_token(self, mock_orders_table):
        """Test user order retrieval with invalid pagination token"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        from orders import BadRequestError
        
        with pytest.raises(BadRequestError, match="Invalid pagination token"):
            OrdersService.get_user_orders('user123', limit=20, last_evaluated_key='invalid_token')
    
    @patch('orders.get_orders_table')
    def test_get_order_details_success(self, mock_orders_table):
        """Test successful order detail retrieval"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB get_item response
        mock_table.get_item.return_value = {
            'Item': {
                'orderId': 'order123',
                'userId': 'user123',
                'items': [
                    {
                        'productId': 'prod1',
                        'name': 'Test Product',
                        'price': Decimal('29.99'),
                        'quantity': 2
                    }
                ],
                'subtotal': Decimal('59.98'),
                'taxAmount': Decimal('4.80'),
                'totalAmount': Decimal('64.78'),
                'status': 'completed',
                'paymentId': 'pi_test_123',
                'shippingAddress': {'street': '123 Main St'},
                'timestamp': 1234567890,
                'createdAt': 1234567890,
                'updatedAt': 1234567890
            }
        }
        
        result = OrdersService.get_order_details('order123', 'user123')
        
        # Verify order details
        assert result['orderId'] == 'order123'
        assert result['userId'] == 'user123'
        assert result['status'] == 'completed'
        assert isinstance(result['totalAmount'], float)  # Decimal converted to float
        assert 'createdAtFormatted' in result
        assert 'updatedAtFormatted' in result
        assert 'statusHistory' in result
        assert result['paymentId'] == 'pi_test_123'
        assert result['shippingAddress']['street'] == '123 Main St'
        
        # Verify DynamoDB get_item was called
        mock_table.get_item.assert_called_once_with(Key={'orderId': 'order123'})
    
    @patch('orders.get_orders_table')
    def test_get_order_details_not_found(self, mock_orders_table):
        """Test order detail retrieval for non-existent order"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB get_item response (no item found)
        mock_table.get_item.return_value = {}
        
        from orders import NotFoundError
        
        with pytest.raises(NotFoundError, match="Order not found"):
            OrdersService.get_order_details('nonexistent', 'user123')
    
    @patch('orders.get_orders_table')
    def test_get_order_details_unauthorized(self, mock_orders_table):
        """Test order detail retrieval for order belonging to different user"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB get_item response with different user
        mock_table.get_item.return_value = {
            'Item': {
                'orderId': 'order123',
                'userId': 'different_user',
                'status': 'completed'
            }
        }
        
        from orders import NotFoundError
        
        with pytest.raises(NotFoundError, match="Order not found"):
            OrdersService.get_order_details('order123', 'user123')
    
    @patch('orders.get_orders_table')
    def test_update_order_status_success(self, mock_orders_table):
        """Test successful order status update"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock get_item for authorization check
        mock_table.get_item.return_value = {
            'Item': {
                'orderId': 'order123',
                'userId': 'user123',
                'status': 'processing'
            }
        }
        
        # Mock update_item response
        mock_table.update_item.return_value = {
            'Attributes': {
                'orderId': 'order123',
                'userId': 'user123',
                'status': 'cancelled',
                'items': [],
                'subtotal': Decimal('59.98'),
                'taxAmount': Decimal('4.80'),
                'totalAmount': Decimal('64.78'),
                'timestamp': 1234567890,
                'createdAt': 1234567890,
                'updatedAt': 1234567900
            }
        }
        
        result = OrdersService.update_order_status('order123', 'cancelled', 'user123', admin_update=False)
        
        # Verify result
        assert result['orderId'] == 'order123'
        assert result['status'] == 'cancelled'
        assert isinstance(result['totalAmount'], float)  # Decimal converted to float
        assert 'createdAtFormatted' in result
        assert 'updatedAtFormatted' in result
        
        # Verify DynamoDB operations
        mock_table.get_item.assert_called_once_with(Key={'orderId': 'order123'})
        mock_table.update_item.assert_called_once()
    
    @patch('orders.get_orders_table')
    def test_update_order_status_invalid_status(self, mock_orders_table):
        """Test order status update with invalid status"""
        from orders import BadRequestError
        
        with pytest.raises(BadRequestError, match="Invalid status"):
            OrdersService.update_order_status('order123', 'invalid_status', 'user123')
    
    @patch('orders.get_orders_table')
    def test_update_order_status_admin_update(self, mock_orders_table):
        """Test admin order status update (skips authorization check)"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock update_item response
        mock_table.update_item.return_value = {
            'Attributes': {
                'orderId': 'order123',
                'userId': 'user123',
                'status': 'shipped',
                'items': [],
                'subtotal': Decimal('59.98'),
                'taxAmount': Decimal('4.80'),
                'totalAmount': Decimal('64.78'),
                'timestamp': 1234567890,
                'createdAt': 1234567890,
                'updatedAt': 1234567900
            }
        }
        
        result = OrdersService.update_order_status('order123', 'shipped', admin_update=True)
        
        # Verify result
        assert result['status'] == 'shipped'
        
        # Verify get_item was NOT called (admin bypass)
        mock_table.get_item.assert_not_called()
        mock_table.update_item.assert_called_once()
    
    @patch('orders.get_orders_table')
    def test_search_orders_with_status_filter(self, mock_orders_table):
        """Test order search with status filter"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB query response
        mock_table.query.return_value = {
            'Items': [
                {
                    'orderId': 'order123',
                    'userId': 'user123',
                    'status': 'completed',
                    'items': [],
                    'subtotal': Decimal('59.98'),
                    'taxAmount': Decimal('4.80'),
                    'totalAmount': Decimal('64.78'),
                    'timestamp': 1234567890,
                    'createdAt': 1234567890,
                    'updatedAt': 1234567890
                }
            ]
        }
        
        result = OrdersService.search_orders('user123', status_filter='completed')
        
        # Verify result
        assert len(result['orders']) == 1
        assert result['orders'][0]['status'] == 'completed'
        assert result['filters']['status'] == 'completed'
        
        # Verify DynamoDB query with filter
        mock_table.query.assert_called_once()
        call_args = mock_table.query.call_args[1]
        assert 'FilterExpression' in call_args
        assert '#status = :status' in call_args['FilterExpression']
        assert call_args['ExpressionAttributeValues'][':status'] == 'completed'
    
    @patch('orders.get_orders_table')
    def test_search_orders_with_date_range(self, mock_orders_table):
        """Test order search with date range filter"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        # Mock DynamoDB query response
        mock_table.query.return_value = {
            'Items': [
                {
                    'orderId': 'order123',
                    'userId': 'user123',
                    'status': 'completed',
                    'items': [],
                    'subtotal': Decimal('59.98'),
                    'taxAmount': Decimal('4.80'),
                    'totalAmount': Decimal('64.78'),
                    'timestamp': 1234567890,
                    'createdAt': 1234567890,
                    'updatedAt': 1234567890
                }
            ]
        }
        
        date_from = 1234567800
        date_to = 1234567900
        
        result = OrdersService.search_orders('user123', date_from=date_from, date_to=date_to)
        
        # Verify result
        assert len(result['orders']) == 1
        assert result['filters']['dateFrom'] == date_from
        assert result['filters']['dateTo'] == date_to
        
        # Verify DynamoDB query with date filters
        mock_table.query.assert_called_once()
        call_args = mock_table.query.call_args[1]
        assert 'FilterExpression' in call_args
        assert '#timestamp >= :date_from AND #timestamp <= :date_to' in call_args['FilterExpression']
        assert call_args['ExpressionAttributeValues'][':date_from'] == date_from
        assert call_args['ExpressionAttributeValues'][':date_to'] == date_to
    
    def test_convert_decimals_to_float(self):
        """Test Decimal to float conversion utility"""
        items = [
            {
                'orderId': 'order123',
                'subtotal': Decimal('59.98'),
                'taxAmount': Decimal('4.80'),
                'totalAmount': Decimal('64.78'),
                'items': [
                    {
                        'price': Decimal('29.99'),
                        'quantity': 2
                    }
                ]
            }
        ]
        
        result = OrdersService._convert_decimals_to_float(items)
        
        # Verify all Decimal objects are converted to float
        assert isinstance(result[0]['subtotal'], float)
        assert isinstance(result[0]['taxAmount'], float)
        assert isinstance(result[0]['totalAmount'], float)
        assert isinstance(result[0]['items'][0]['price'], float)
        assert result[0]['subtotal'] == 59.98
        assert result[0]['items'][0]['price'] == 29.99
    
    def test_get_order_status_history(self):
        """Test order status history retrieval (placeholder implementation)"""
        result = OrdersService._get_order_status_history('order123')
        
        # Currently returns empty list (future enhancement)
        assert result == []


class TestOrdersHandler:
    """Test orders Lambda handler and API endpoints"""
    
    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context"""
        context = Mock()
        context.function_name = "test-orders"
        context.memory_limit_in_mb = 128
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-orders"
        context.aws_request_id = "test-request-id"
        return context
    
    @pytest.fixture
    def api_gateway_event_base(self):
        """Base API Gateway event structure"""
        return {
            'httpMethod': 'GET',
            'path': '/orders',
            'pathParameters': None,
            'queryStringParameters': None,
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer test-token'
            },
            'body': None,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123',
                        'email': 'test@example.com'
                    }
                }
            }
        }
    
    def test_get_orders_success(self, lambda_context, api_gateway_event_base):
        """Test successful GET /orders endpoint"""
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'limit': '10'}
        
        with patch.object(OrdersService, 'get_user_orders') as mock_get_orders:
            mock_get_orders.return_value = {
                'orders': [
                    {
                        'orderId': 'order123',
                        'userId': 'user123',
                        'status': 'completed',
                        'totalAmount': 64.78,
                        'createdAtFormatted': '2023-12-17 10:30:00 UTC'
                    }
                ],
                'nextToken': None,
                'hasMore': False,
                'totalReturned': 1
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['orders'][0]['orderId'] == 'order123'
            assert body['totalReturned'] == 1
            
            # Verify service method was called with correct parameters
            mock_get_orders.assert_called_once_with('user123', 10, None)
    
    def test_get_orders_with_pagination(self, lambda_context, api_gateway_event_base):
        """Test GET /orders with pagination token"""
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {
            'limit': '5',
            'nextToken': 'test_pagination_token'
        }
        
        with patch.object(OrdersService, 'get_user_orders') as mock_get_orders:
            mock_get_orders.return_value = {
                'orders': [],
                'nextToken': None,
                'hasMore': False,
                'totalReturned': 0
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            
            # Verify service method was called with pagination token
            mock_get_orders.assert_called_once_with('user123', 5, 'test_pagination_token')
    
    def test_get_orders_invalid_limit(self, lambda_context, api_gateway_event_base):
        """Test GET /orders with invalid limit parameter"""
        event = api_gateway_event_base.copy()
        event['queryStringParameters'] = {'limit': '150'}  # Exceeds max limit
        
        response = handler(event, lambda_context)
        
        # Verify bad request response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Limit must be between 1 and 100' in body['message']
    
    def test_get_order_details_success(self, lambda_context, api_gateway_event_base):
        """Test successful GET /orders/{orderId} endpoint"""
        event = api_gateway_event_base.copy()
        event['path'] = '/orders/order123'
        event['pathParameters'] = {'order_id': 'order123'}
        
        with patch.object(OrdersService, 'get_order_details') as mock_get_details:
            mock_get_details.return_value = {
                'orderId': 'order123',
                'userId': 'user123',
                'status': 'completed',
                'totalAmount': 64.78,
                'items': [
                    {
                        'productId': 'prod1',
                        'name': 'Test Product',
                        'price': 29.99,
                        'quantity': 2
                    }
                ],
                'createdAtFormatted': '2023-12-17 10:30:00 UTC',
                'statusHistory': []
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['orderId'] == 'order123'
            assert body['status'] == 'completed'
            assert len(body['items']) == 1
            
            # Verify service method was called
            mock_get_details.assert_called_once_with('order123', 'user123')
    
    def test_get_order_details_not_found(self, lambda_context, api_gateway_event_base):
        """Test GET /orders/{orderId} for non-existent order"""
        event = api_gateway_event_base.copy()
        event['path'] = '/orders/nonexistent'
        event['pathParameters'] = {'order_id': 'nonexistent'}
        
        with patch.object(OrdersService, 'get_order_details') as mock_get_details:
            from orders import NotFoundError
            mock_get_details.side_effect = NotFoundError("Order not found")
            
            response = handler(event, lambda_context)
            
            # Verify not found response
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert 'Order not found' in body['message']
    
    def test_update_order_status_success(self, lambda_context, api_gateway_event_base):
        """Test successful PUT /orders/{orderId}/status endpoint"""
        event = api_gateway_event_base.copy()
        event['httpMethod'] = 'PUT'
        event['path'] = '/orders/order123/status'
        event['pathParameters'] = {'order_id': 'order123'}
        event['body'] = json.dumps({'status': 'cancelled'})
        
        with patch.object(OrdersService, 'update_order_status') as mock_update_status:
            mock_update_status.return_value = {
                'orderId': 'order123',
                'userId': 'user123',
                'status': 'cancelled',
                'totalAmount': 64.78,
                'updatedAtFormatted': '2023-12-17 10:35:00 UTC'
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['orderId'] == 'order123'
            assert body['status'] == 'cancelled'
            
            # Verify service method was called
            mock_update_status.assert_called_once_with('order123', 'cancelled', 'user123', admin_update=False)
    
    def test_update_order_status_invalid_json(self, lambda_context, api_gateway_event_base):
        """Test PUT /orders/{orderId}/status with invalid JSON"""
        event = api_gateway_event_base.copy()
        event['httpMethod'] = 'PUT'
        event['path'] = '/orders/order123/status'
        event['pathParameters'] = {'order_id': 'order123'}
        event['body'] = 'invalid json'
        
        response = handler(event, lambda_context)
        
        # Verify bad request response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body['message']
    
    def test_update_order_status_invalid_status(self, lambda_context, api_gateway_event_base):
        """Test PUT /orders/{orderId}/status with invalid status"""
        event = api_gateway_event_base.copy()
        event['httpMethod'] = 'PUT'
        event['path'] = '/orders/order123/status'
        event['pathParameters'] = {'order_id': 'order123'}
        event['body'] = json.dumps({'status': 'shipped'})  # Only 'cancelled' allowed for customers
        
        response = handler(event, lambda_context)
        
        # Verify bad request response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Customers can only cancel orders' in body['message']
    
    def test_search_orders_success(self, lambda_context, api_gateway_event_base):
        """Test successful GET /orders/search endpoint"""
        event = api_gateway_event_base.copy()
        event['path'] = '/orders/search'
        event['queryStringParameters'] = {
            'status': 'completed',
            'dateFrom': '1234567800',
            'dateTo': '1234567900',
            'limit': '10'
        }
        
        with patch.object(OrdersService, 'search_orders') as mock_search:
            mock_search.return_value = {
                'orders': [
                    {
                        'orderId': 'order123',
                        'userId': 'user123',
                        'status': 'completed',
                        'totalAmount': 64.78
                    }
                ],
                'nextToken': None,
                'hasMore': False,
                'totalReturned': 1,
                'filters': {
                    'status': 'completed',
                    'dateFrom': 1234567800,
                    'dateTo': 1234567900
                }
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body['orders']) == 1
            assert body['filters']['status'] == 'completed'
            
            # Verify service method was called with correct parameters
            mock_search.assert_called_once_with('user123', 'completed', 1234567800, 1234567900, 10, None)
    
    def test_missing_user_id_in_token(self, lambda_context, api_gateway_event_base):
        """Test API endpoints with missing user ID in JWT token"""
        event = api_gateway_event_base.copy()
        event['requestContext']['authorizer']['claims'] = {}  # No 'sub' claim
        
        response = handler(event, lambda_context)
        
        # Verify bad request response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'User ID not found in token' in body['message']
    
    def test_unexpected_error_handling(self, lambda_context, api_gateway_event_base):
        """Test unexpected error handling in handler"""
        event = api_gateway_event_base.copy()
        
        with patch.object(OrdersService, 'get_user_orders') as mock_get_orders:
            mock_get_orders.side_effect = Exception("Unexpected error")
            
            response = handler(event, lambda_context)
            
            # Verify internal server error response
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'Internal server error' in body['error']