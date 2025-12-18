"""
Tests for Payment Lambda Function

Tests payment processing functionality including Stripe integration,
Step Functions integration, and webhook handling.
"""

import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add lambda directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'payment'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layers', 'utils', 'python'))

# Mock AWS services before importing
with patch('boto3.resource'), patch('boto3.client'):
    from payment import handler, PaymentService


class TestPaymentService:
    """Test PaymentService class methods"""
    
    @patch('payment.get_stripe_api_key')
    @patch('payment.stripe')
    def test_create_payment_intent_success(self, mock_stripe, mock_get_api_key):
        """Test successful payment intent creation"""
        # Setup mocks
        mock_get_api_key.return_value = 'sk_test_123'
        mock_payment_intent = Mock()
        mock_payment_intent.id = 'pi_test_123'
        mock_payment_intent.client_secret = 'pi_test_123_secret'
        mock_payment_intent.status = 'requires_payment_method'
        mock_payment_intent.amount = 2999
        mock_payment_intent.currency = 'usd'
        mock_stripe.PaymentIntent.create.return_value = mock_payment_intent
        
        payment_data = {
            'totalAmount': 29.99,
            'currency': 'usd',
            'userId': 'user123',
            'orderId': 'order123'
        }
        
        result = PaymentService.create_payment_intent(payment_data)
        
        # Verify Stripe API call
        mock_stripe.PaymentIntent.create.assert_called_once_with(
            amount=2999,
            currency='usd',
            metadata={
                'userId': 'user123',
                'orderId': 'order123',
                'source': 'e-com67-platform'
            },
            automatic_payment_methods={'enabled': True},
            capture_method='automatic'
        )
        
        # Verify result
        assert result['paymentIntentId'] == 'pi_test_123'
        assert result['clientSecret'] == 'pi_test_123_secret'
        assert result['status'] == 'requires_payment_method'
        assert result['amount'] == 2999
        assert result['currency'] == 'usd'
    
    @patch('payment.get_stripe_api_key')
    def test_create_payment_intent_no_api_key(self, mock_get_api_key):
        """Test payment intent creation with missing API key"""
        mock_get_api_key.return_value = None
        
        payment_data = {
            'totalAmount': 29.99,
            'userId': 'user123'
        }
        
        with pytest.raises(Exception) as exc_info:
            PaymentService.create_payment_intent(payment_data)
        
        assert "Stripe API key not configured" in str(exc_info.value)
    
    @patch('payment.get_stripe_api_key')
    @patch('payment.stripe')
    def test_process_payment_success(self, mock_stripe, mock_get_api_key):
        """Test successful payment processing for Step Functions"""
        # Setup mocks
        mock_get_api_key.return_value = 'sk_test_123'
        mock_payment_intent = Mock()
        mock_payment_intent.id = 'pi_test_123'
        mock_payment_intent.client_secret = 'pi_test_123_secret'
        mock_payment_intent.status = 'requires_payment_method'
        mock_payment_intent.amount = 2999
        mock_payment_intent.currency = 'usd'
        mock_stripe.PaymentIntent.create.return_value = mock_payment_intent
        
        payment_data = {
            'totalAmount': 29.99,
            'userId': 'user123',
            'orderId': 'order123'
        }
        
        result = PaymentService.process_payment(payment_data)
        
        # Verify successful result
        assert result['success'] is True
        assert result['paymentId'] == 'pi_test_123'
        assert result['paymentStatus'] == 'succeeded'
        assert result['amount'] == 29.99
        assert result['userId'] == 'user123'
        assert result['orderId'] == 'order123'
        assert 'processedAt' in result
    
    @patch('payment.get_stripe_api_key')
    @patch('payment.stripe')
    def test_process_payment_failure(self, mock_stripe, mock_get_api_key):
        """Test payment processing failure"""
        # Setup mocks
        mock_get_api_key.return_value = 'sk_test_123'
        mock_stripe.PaymentIntent.create.side_effect = Exception("Payment failed")
        
        payment_data = {
            'totalAmount': 29.99,
            'userId': 'user123',
            'orderId': 'order123'
        }
        
        result = PaymentService.process_payment(payment_data)
        
        # Verify failure result
        assert result['success'] is False
        assert result['error'] == "Failed to create payment intent: Payment failed"
        assert result['errorCode'] == 'PAYMENT_FAILED'
        assert result['userId'] == 'user123'
        assert result['orderId'] == 'order123'
        assert 'failedAt' in result
    
    @patch('payment.get_stripe_api_key')
    @patch('payment.stripe')
    @patch('payment.PaymentService._update_order_payment_status')
    def test_handle_webhook_payment_succeeded(self, mock_update_status, mock_stripe, mock_get_api_key):
        """Test webhook handling for successful payment"""
        mock_get_api_key.return_value = 'sk_test_123'
        
        webhook_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'metadata': {
                        'orderId': 'order123'
                    }
                }
            }
        }
        
        result = PaymentService.handle_webhook(webhook_data)
        
        # Verify webhook processing
        assert result['success'] is True
        assert result['eventType'] == 'payment_intent.succeeded'
        assert result['paymentIntentId'] == 'pi_test_123'
        assert 'processedAt' in result
        
        # Verify order status update was called
        mock_update_status.assert_called_once_with('order123', 'paid', 'pi_test_123')
    
    @patch('payment.get_stripe_api_key')
    @patch('payment.stripe')
    @patch('payment.PaymentService._update_order_payment_status')
    def test_handle_webhook_payment_failed(self, mock_update_status, mock_stripe, mock_get_api_key):
        """Test webhook handling for failed payment"""
        mock_get_api_key.return_value = 'sk_test_123'
        
        webhook_data = {
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'metadata': {
                        'orderId': 'order123'
                    }
                }
            }
        }
        
        result = PaymentService.handle_webhook(webhook_data)
        
        # Verify webhook processing
        assert result['success'] is True
        assert result['eventType'] == 'payment_intent.payment_failed'
        assert result['paymentIntentId'] == 'pi_test_123'
        
        # Verify order status update was called
        mock_update_status.assert_called_once_with('order123', 'payment_failed', 'pi_test_123')


class TestPaymentHandler:
    """Test payment Lambda handler"""
    
    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context"""
        context = Mock()
        context.function_name = "test-payment"
        context.memory_limit_in_mb = 128
        context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-payment"
        context.aws_request_id = "test-request-id"
        return context
    
    def test_step_functions_invocation(self, lambda_context):
        """Test Step Functions invocation for payment processing"""
        event = {
            'source': 'step-functions',
            'input': {
                'totalAmount': 29.99,
                'userId': 'user123',
                'orderId': 'order123'
            }
        }
        
        with patch.object(PaymentService, 'process_payment') as mock_process:
            mock_process.return_value = {
                'success': True,
                'paymentId': 'pi_test_123',
                'paymentStatus': 'succeeded',
                'amount': 29.99,
                'userId': 'user123',
                'orderId': 'order123',
                'processedAt': 1234567890
            }
            
            result = handler(event, lambda_context)
            
            # Verify Step Functions response
            assert result['success'] is True
            assert result['paymentId'] == 'pi_test_123'
            assert result['paymentStatus'] == 'succeeded'
            
            # Verify service method was called
            mock_process.assert_called_once_with(event['input'])
    
    def test_api_gateway_payment_intent_creation(self, lambda_context):
        """Test API Gateway invocation for payment intent creation"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'totalAmount': 29.99,
                'currency': 'usd',
                'userId': 'user123'
            })
        }
        
        with patch.object(PaymentService, 'create_payment_intent') as mock_create:
            mock_create.return_value = {
                'paymentIntentId': 'pi_test_123',
                'clientSecret': 'pi_test_123_secret',
                'status': 'requires_payment_method',
                'amount': 2999,
                'currency': 'usd'
            }
            
            response = handler(event, lambda_context)
            
            # Verify API Gateway response
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['paymentIntentId'] == 'pi_test_123'
            assert body['clientSecret'] == 'pi_test_123_secret'
            
            # Verify service method was called
            expected_data = {
                'totalAmount': 29.99,
                'currency': 'usd',
                'userId': 'user123'
            }
            mock_create.assert_called_once_with(expected_data)
    
    def test_api_gateway_webhook_handling(self, lambda_context):
        """Test API Gateway webhook handling"""
        event = {
            'httpMethod': 'POST',
            'path': '/webhook',
            'body': json.dumps({
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': 'pi_test_123',
                        'metadata': {'orderId': 'order123'}
                    }
                }
            })
        }
        
        with patch.object(PaymentService, 'handle_webhook') as mock_webhook:
            mock_webhook.return_value = {
                'success': True,
                'eventType': 'payment_intent.succeeded',
                'paymentIntentId': 'pi_test_123',
                'processedAt': 1234567890
            }
            
            response = handler(event, lambda_context)
            
            # Verify webhook response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['eventType'] == 'payment_intent.succeeded'
            
            # Verify service method was called
            expected_data = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': 'pi_test_123',
                        'metadata': {'orderId': 'order123'}
                    }
                }
            }
            mock_webhook.assert_called_once_with(expected_data)
    
    def test_options_request(self, lambda_context):
        """Test CORS OPTIONS request"""
        event = {
            'httpMethod': 'OPTIONS'
        }
        
        response = handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_invalid_json(self, lambda_context):
        """Test invalid JSON in request body"""
        event = {
            'httpMethod': 'POST',
            'body': 'invalid json'
        }
        
        response = handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_JSON'
    
    def test_unsupported_method(self, lambda_context):
        """Test unsupported HTTP method"""
        event = {
            'httpMethod': 'PATCH'
        }
        
        response = handler(event, lambda_context)
        
        assert response['statusCode'] == 405
        body = json.loads(response['body'])
        assert body['error']['code'] == 'METHOD_NOT_ALLOWED'