"""
Tests for Order Processor Lambda Function

Tests order processing functionality including order creation,
inventory updates, cart clearing, and notification sending.
"""

import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'order_processor'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layers', 'utils', 'python'))

# Mock AWS services before importing
with patch('boto3.resource'), patch('boto3.client'):
    from order_processor import handler, OrderProcessorService


class TestOrderProcessorService:
    """Test OrderProcessorService class methods"""
    
    @patch('order_processor.get_orders_table')
    @patch('order_processor.OrderProcessorService._update_inventory')
    @patch('order_processor.OrderProcessorService._clear_user_cart')
    @patch('order_processor.OrderProcessorService._send_order_notifications')
    @patch('order_processor.OrderProcessorService._update_order_status')
    def test_process_order_success(self, mock_update_status, mock_send_notifications, 
                                 mock_clear_cart, mock_update_inventory, mock_orders_table):
        """Test successful order processing"""
        # Setup mocks
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        mock_update_inventory.return_value = [
            {'productId': 'prod1', 'quantityOrdered': 2, 'newStock': 98, 'success': True}
        ]
        mock_clear_cart.return_value = True
        mock_send_notifications.return_value = True
        
        order_data = {
            'userId': 'user123',
            'orderId': 'order123',
            'items': [
                {
                    'productId': 'prod1',
                    'name': 'Test Product',
                    'price': 29.99,
                    'quantity': 2
                }
            ],
            'paymentId': 'pi_test_123'
        }
        
        result = OrderProcessorService.process_order(order_data)
        
        # Verify result
        assert result['success'] is True
        assert result['orderId'] == 'order123'
        assert result['userId'] == 'user123'
        assert result['inventoryUpdated'] == [
            {'productId': 'prod1', 'quantityOrdered': 2, 'newStock': 98, 'success': True}
        ]
        assert result['cartCleared'] is True
        assert result['notificationSent'] is True
        assert 'processedAt' in result
        
        # Verify order record was created
        mock_table.put_item.assert_called_once()
        
        # Verify status updates
        mock_update_status.assert_called_with('order123', 'completed')
    
    @patch('order_processor.get_orders_table')
    def test_create_order_record(self, mock_orders_table):
        """Test order record creation"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        order_id = 'order123'
        user_id = 'user123'
        items = [
            {'productId': 'prod1', 'name': 'Test Product', 'price': 29.99, 'quantity': 2}
        ]
        order_data = {'shippingAddress': {'street': '123 Main St'}}
        payment_id = 'pi_test_123'
        
        result = OrderProcessorService._create_order_record(
            order_id, user_id, items, order_data, payment_id
        )
        
        # Verify order record structure
        assert result['orderId'] == order_id
        assert result['userId'] == user_id
        assert result['items'] == items
        assert result['subtotal'] == 59.98  # 29.99 * 2
        assert result['taxAmount'] == 4.80  # 8% of subtotal (rounded)
        assert result['totalAmount'] == 64.78  # subtotal + tax
        assert result['status'] == 'processing'
        assert result['paymentId'] == payment_id
        assert result['paymentStatus'] == 'paid'
        assert 'timestamp' in result
        assert 'createdAt' in result
        assert 'updatedAt' in result
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
    
    @patch('order_processor.get_products_table')
    @patch('order_processor.OrderProcessorService._send_low_stock_alert')
    def test_update_inventory_success(self, mock_send_alert, mock_products_table):
        """Test successful inventory update"""
        mock_table = Mock()
        mock_products_table.return_value = mock_table
        
        # Mock successful update response
        mock_table.update_item.return_value = {
            'Attributes': {'stock': Decimal('98')}
        }
        
        items = [
            {'productId': 'prod1', 'quantity': 2}
        ]
        
        result = OrderProcessorService._update_inventory(items)
        
        # Verify result
        assert len(result) == 1
        assert result[0]['productId'] == 'prod1'
        assert result[0]['quantityOrdered'] == 2
        assert result[0]['newStock'] == 98
        assert result[0]['success'] is True
        
        # Verify DynamoDB update was called
        mock_table.update_item.assert_called_once()
        
        # Verify no low stock alert (stock > 10)
        mock_send_alert.assert_not_called()
    
    @patch('order_processor.get_products_table')
    @patch('order_processor.OrderProcessorService._send_low_stock_alert')
    def test_update_inventory_low_stock_alert(self, mock_send_alert, mock_products_table):
        """Test inventory update with low stock alert"""
        mock_table = Mock()
        mock_products_table.return_value = mock_table
        
        # Mock update response with low stock
        mock_table.update_item.return_value = {
            'Attributes': {'stock': Decimal('5')}
        }
        
        items = [
            {'productId': 'prod1', 'quantity': 2}
        ]
        
        result = OrderProcessorService._update_inventory(items)
        
        # Verify low stock alert was sent
        mock_send_alert.assert_called_once_with('prod1', 5)
    
    @patch('order_processor.get_products_table')
    def test_update_inventory_insufficient_stock(self, mock_products_table):
        """Test inventory update with insufficient stock"""
        mock_table = Mock()
        mock_products_table.return_value = mock_table
        
        # Mock conditional check failure (insufficient stock)
        from botocore.exceptions import ClientError
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException'}},
            'UpdateItem'
        )
        
        items = [
            {'productId': 'prod1', 'quantity': 10}
        ]
        
        result = OrderProcessorService._update_inventory(items)
        
        # Verify failure result
        assert len(result) == 1
        assert result[0]['productId'] == 'prod1'
        assert result[0]['quantityOrdered'] == 10
        assert result[0]['success'] is False
        assert result[0]['error'] == 'Insufficient stock'
    
    @patch('order_processor.get_cart_table')
    def test_clear_user_cart_success(self, mock_cart_table):
        """Test successful cart clearing"""
        mock_table = Mock()
        mock_cart_table.return_value = mock_table
        
        # Mock cart query response
        mock_table.query.return_value = {
            'Items': [
                {'userId': 'user123', 'productId': 'prod1'},
                {'userId': 'user123', 'productId': 'prod2'}
            ]
        }
        
        # Mock batch writer
        mock_batch_writer = Mock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_batch_writer
        
        result = OrderProcessorService._clear_user_cart('user123')
        
        # Verify success
        assert result is True
        
        # Verify batch delete was called for each item
        assert mock_batch_writer.delete_item.call_count == 2
    
    @patch('order_processor.get_cart_table')
    def test_clear_user_cart_empty(self, mock_cart_table):
        """Test clearing empty cart"""
        mock_table = Mock()
        mock_cart_table.return_value = mock_table
        
        # Mock empty cart response
        mock_table.query.return_value = {'Items': []}
        
        result = OrderProcessorService._clear_user_cart('user123')
        
        # Verify success (empty cart is considered successful)
        assert result is True
    
    @patch('order_processor.sns')
    @patch('order_processor.os.environ.get')
    def test_send_order_notifications_success(self, mock_env_get, mock_sns):
        """Test successful order notification sending"""
        mock_env_get.return_value = 'arn:aws:sns:us-east-1:123456789012:order-notifications'
        
        order_record = {
            'orderId': 'order123',
            'userId': 'user123',
            'totalAmount': 64.78,
            'items': [{'productId': 'prod1'}],
            'timestamp': 1234567890
        }
        
        result = OrderProcessorService._send_order_notifications(order_record)
        
        # Verify success
        assert result is True
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        call_args = mock_sns.publish.call_args
        assert call_args[1]['TopicArn'] == 'arn:aws:sns:us-east-1:123456789012:order-notifications'
        assert 'order_confirmation' in call_args[1]['Message']
    
    @patch('order_processor.sns')
    @patch('order_processor.os.environ.get')
    def test_send_low_stock_alert(self, mock_env_get, mock_sns):
        """Test low stock alert sending"""
        mock_env_get.return_value = 'arn:aws:sns:us-east-1:123456789012:admin-notifications'
        
        OrderProcessorService._send_low_stock_alert('prod1', 5)
        
        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        call_args = mock_sns.publish.call_args
        assert call_args[1]['TopicArn'] == 'arn:aws:sns:us-east-1:123456789012:admin-notifications'
        assert 'low_stock_alert' in call_args[1]['Message']
    
    @patch('order_processor.get_orders_table')
    def test_update_order_status(self, mock_orders_table):
        """Test order status update"""
        mock_table = Mock()
        mock_orders_table.return_value = mock_table
        
        OrderProcessorService._update_order_status('order123', 'completed')
        
        # Verify update_item was called
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert call_args[1]['Key'] == {'orderId': 'order123'}
        assert ':status' in call_args[1]['ExpressionAttributeValues']
        assert call_args[1]['ExpressionAttributeValues'][':status'] == 'completed'


class TestOrderProcessorHandler:
    """Test order processor Lambda handler"""
    
    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context"""
        context = Mock()
        context.function_name = "test-order-processor"
        context.memory_limit_in_mb = 128
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-order-processor"
        context.aws_request_id = "test-request-id"
        return context
    
    def test_sqs_message_processing_success(self, lambda_context):
        """Test successful SQS message processing"""
        event = {
            'Records': [
                {
                    'messageId': 'msg123',
                    'body': json.dumps({
                        'userId': 'user123',
                        'orderId': 'order123',
                        'items': [
                            {
                                'productId': 'prod1',
                                'name': 'Test Product',
                                'price': 29.99,
                                'quantity': 2
                            }
                        ],
                        'paymentId': 'pi_test_123'
                    })
                }
            ]
        }
        
        with patch.object(OrderProcessorService, 'process_order') as mock_process:
            mock_process.return_value = {
                'success': True,
                'orderId': 'order123',
                'userId': 'user123',
                'inventoryUpdated': [],
                'cartCleared': True,
                'notificationSent': True,
                'processedAt': 1234567890
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'Successfully processed 1 orders' in body['message']
            
            # Verify service method was called
            expected_order_data = {
                'userId': 'user123',
                'orderId': 'order123',
                'items': [
                    {
                        'productId': 'prod1',
                        'name': 'Test Product',
                        'price': 29.99,
                        'quantity': 2
                    }
                ],
                'paymentId': 'pi_test_123'
            }
            mock_process.assert_called_once_with(expected_order_data)
    
    def test_sqs_message_processing_multiple_records(self, lambda_context):
        """Test processing multiple SQS records"""
        event = {
            'Records': [
                {
                    'messageId': 'msg123',
                    'body': json.dumps({
                        'userId': 'user123',
                        'orderId': 'order123',
                        'items': [],
                        'paymentId': 'pi_test_123'
                    })
                },
                {
                    'messageId': 'msg456',
                    'body': json.dumps({
                        'userId': 'user456',
                        'orderId': 'order456',
                        'items': [],
                        'paymentId': 'pi_test_456'
                    })
                }
            ]
        }
        
        with patch.object(OrderProcessorService, 'process_order') as mock_process:
            mock_process.return_value = {
                'success': True,
                'orderId': 'order123',
                'userId': 'user123',
                'processedAt': 1234567890
            }
            
            response = handler(event, lambda_context)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert 'Successfully processed 2 orders' in body['message']
            
            # Verify service method was called twice
            assert mock_process.call_count == 2
    
    def test_sqs_message_invalid_json(self, lambda_context):
        """Test SQS message with invalid JSON"""
        event = {
            'Records': [
                {
                    'messageId': 'msg123',
                    'body': 'invalid json'
                }
            ]
        }
        
        with pytest.raises(json.JSONDecodeError):
            handler(event, lambda_context)
    
    def test_sqs_message_processing_failure(self, lambda_context):
        """Test SQS message processing failure"""
        event = {
            'Records': [
                {
                    'messageId': 'msg123',
                    'body': json.dumps({
                        'userId': 'user123',
                        'orderId': 'order123',
                        'items': [],
                        'paymentId': 'pi_test_123'
                    })
                }
            ]
        }
        
        with patch.object(OrderProcessorService, 'process_order') as mock_process:
            from utils.exceptions import BusinessLogicError
            mock_process.side_effect = BusinessLogicError("Order processing failed")
            
            with pytest.raises(BusinessLogicError):
                handler(event, lambda_context)