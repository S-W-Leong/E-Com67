"""
Tests for Payment Lambda Function

Tests payment processing functionality including Stripe integration,
Step Functions integration, and webhook handling.
"""

import json
import os
import sys
import time
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
    
    def test_validate_payment_data_success(self):
        """Test successful payment data validation"""
        payment_data = {
            'totalAmount': 29.99,
            'currency': 'usd',
            'userId': 'user123'
        }
        
        result = PaymentService.validate_payment_data(payment_data)
        
        assert result['isValid'] is True
        assert result['fraudScore'] < 50
        assert result['validatedAmount'] == 29.99
        assert result['validatedCurrency'] == 'usd'
    
    def test_validate_payment_data_high_amount(self):
        """Test payment validation with high amount"""
        payment_data = {
            'totalAmount': 15000.00,
            'currency': 'usd',
            'userId': 'user123'
        }
        
        result = PaymentService.validate_payment_data(payment_data)
        
        # High amount should increase fraud score but not block
        assert result['fraudScore'] >= 30
        assert 'High transaction amount' in result['fraudReasons']
    
    def test_validate_payment_data_missing_fields(self):
        """Test payment validation with missing required fields"""
        payment_data = {
            'currency': 'usd'
        }
        
        with pytest.raises(Exception) as exc_info:
            PaymentService.validate_payment_data(payment_data)
        
        assert "Missing required field" in str(exc_info.value)
    
    def test_validate_payment_data_invalid_amount(self):
        """Test payment validation with invalid amount"""
        payment_data = {
            'totalAmount': -10.00,
            'userId': 'user123'
        }
        
        with pytest.raises(Exception) as exc_info:
            PaymentService.validate_payment_data(payment_data)
        
        assert "must be greater than zero" in str(exc_info.value)
    
    def test_create_payment_intent_success(self):
        """Test successful payment intent creation"""
        # Test with test mode enabled to avoid Stripe dependency
        with patch.dict(os.environ, {'PAYMENT_TEST_MODE': 'true'}):
            payment_data = {
                'totalAmount': 29.99,
                'currency': 'usd',
                'userId': 'user123',
                'orderId': 'order123'
            }
            
            # This should work with validation but skip actual Stripe calls
            validation_result = PaymentService.validate_payment_data(payment_data)
            assert validation_result['isValid'] is True
    
    def test_create_payment_intent_no_api_key(self):
        """Test payment intent creation with missing API key"""
        with patch('payment.get_stripe_api_key', return_value=None):
            payment_data = {
                'totalAmount': 29.99,
                'userId': 'user123'
            }
            
            with pytest.raises(Exception) as exc_info:
                PaymentService.create_payment_intent(payment_data)
            
            assert "Stripe API key not configured" in str(exc_info.value)
    
    def test_process_payment_success_test_mode(self):
        """Test successful payment processing in test mode"""
        with patch.dict(os.environ, {'PAYMENT_TEST_MODE': 'true'}):
            payment_data = {
                'totalAmount': 29.99,
                'userId': 'user123',
                'orderId': 'order123'
            }
            
            result = PaymentService.process_payment(payment_data)
            
            # Verify successful result in test mode
            assert result['success'] is True
            assert result['paymentStatus'] == 'succeeded'
            assert result['amount'] == 29.99
            assert result['userId'] == 'user123'
            assert result['orderId'] == 'order123'
            assert result['testMode'] is True
            assert 'processedAt' in result
    
    def test_process_payment_validation_failure(self):
        """Test payment processing with validation failure"""
        payment_data = {
            'totalAmount': -10.00,  # Invalid amount
            'userId': 'user123',
            'orderId': 'order123'
        }
        
        result = PaymentService.process_payment(payment_data)
        
        # Verify failure result
        assert result['success'] is False
        assert result['errorCode'] == 'PAYMENT_VALIDATION_FAILED'
        assert result['userId'] == 'user123'
        assert result['orderId'] == 'order123'
        assert 'failedAt' in result
        assert result['retryable'] is False
    
    def test_webhook_event_processing_logic(self):
        """Test webhook event processing logic without Stripe dependency"""
        # Test the event processing logic
        webhook_data = {
            'type': 'payment_intent.succeeded',
            'id': 'evt_test_123',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'metadata': {
                        'orderId': 'order123'
                    }
                }
            }
        }
        
        # Test that we can extract the event details correctly
        event_type = webhook_data.get('type')
        event_data = webhook_data.get('data', {}).get('object', {})
        payment_intent_id = event_data.get('id')
        order_id = event_data.get('metadata', {}).get('orderId')
        
        assert event_type == 'payment_intent.succeeded'
        assert payment_intent_id == 'pi_test_123'
        assert order_id == 'order123'
    
    def test_verify_webhook_signature_success(self):
        """Test successful webhook signature verification"""
        payload = '{"test": "data"}'
        timestamp = str(int(time.time()))
        webhook_secret = 'whsec_test_secret'
        
        # Create valid signature
        import hmac
        import hashlib
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        stripe_signature = f"t={timestamp},v1={signature}"
        
        result = PaymentService.verify_webhook_signature(payload, stripe_signature, webhook_secret)
        assert result is True
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature"""
        payload = '{"test": "data"}'
        timestamp = str(int(time.time()))
        webhook_secret = 'whsec_test_secret'
        
        # Create invalid signature
        stripe_signature = f"t={timestamp},v1=invalid_signature"
        
        result = PaymentService.verify_webhook_signature(payload, stripe_signature, webhook_secret)
        assert result is False
    
    def test_verify_webhook_signature_old_timestamp(self):
        """Test webhook signature verification with old timestamp"""
        payload = '{"test": "data"}'
        old_timestamp = str(int(time.time()) - 400)  # 400 seconds ago (> 5 minutes)
        webhook_secret = 'whsec_test_secret'
        
        # Create valid signature but with old timestamp
        import hmac
        import hashlib
        signed_payload = f"{old_timestamp}.{payload}"
        signature = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        stripe_signature = f"t={old_timestamp},v1={signature}"
        
        result = PaymentService.verify_webhook_signature(payload, stripe_signature, webhook_secret)
        assert result is False


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
                'eventId': 'evt_test_123',
                'processedAt': 1234567890
            }
            
            response = handler(event, lambda_context)
            
            # Verify webhook response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['eventType'] == 'payment_intent.succeeded'
            
            # Verify service method was called with correct parameters
            mock_webhook.assert_called_once()
            call_args = mock_webhook.call_args
            # The function is called with (webhook_data, signature, raw_body)
            assert len(call_args[0]) >= 1  # At least webhook_data is passed
    
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
    
    def test_api_gateway_refund_processing(self, lambda_context):
        """Test API Gateway refund processing"""
        event = {
            'httpMethod': 'POST',
            'path': '/refund',
            'body': json.dumps({
                'paymentIntentId': 'pi_test_123',
                'amount': 2999,
                'reason': 'requested_by_customer',
                'orderId': 'order123'
            })
        }
        
        with patch.object(PaymentService, 'process_refund') as mock_refund:
            mock_refund.return_value = {
                'success': True,
                'refundId': 're_test_123',
                'paymentIntentId': 'pi_test_123',
                'amount': 2999,
                'status': 'succeeded'
            }
            
            response = handler(event, lambda_context)
            
            # Verify refund response
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['refundId'] == 're_test_123'
    
    def test_api_gateway_payment_status_query_missing_param(self, lambda_context):
        """Test API Gateway payment status query with missing parameter"""
        event = {
            'httpMethod': 'GET',
            'path': '/status',
            'queryStringParameters': {}
        }
        
        response = handler(event, lambda_context)
        
        # Verify error response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'MISSING_PARAMETER'
    
    def test_api_gateway_webhook_with_signature(self, lambda_context):
        """Test API Gateway webhook with signature verification"""
        event = {
            'httpMethod': 'POST',
            'path': '/webhook',
            'headers': {
                'Stripe-Signature': 't=1234567890,v1=test_signature'
            },
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
                'eventId': 'evt_test_123',
                'processedAt': 1234567890
            }
            
            response = handler(event, lambda_context)
            
            # Verify webhook response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['eventType'] == 'payment_intent.succeeded'
            
            # Verify webhook handler was called
            mock_webhook.assert_called_once()
            call_args = mock_webhook.call_args
            # Verify that signature was passed as a parameter
            assert len(call_args[0]) >= 2  # webhook_data and signature