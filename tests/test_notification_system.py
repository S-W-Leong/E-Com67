"""
Tests for E-Com67 Notification System

This module contains unit tests for the notification system components:
- Email notification function
- Notification orchestrator function
- Multi-channel notification routing
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the functions to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'email_notification'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda', 'notification_orchestrator'))

from email_notification import handler as email_handler, generate_order_confirmation_email, generate_order_status_update_email
from notification_orchestrator import handler as orchestrator_handler, get_user_preferences, should_send_notification


class TestEmailNotificationFunction:
    """Test cases for email notification function"""
    
    def test_generate_order_confirmation_email(self):
        """Test order confirmation email generation"""
        order_data = {
            'orderId': 'test-order-123',
            'customerName': 'John Doe',
            'items': [
                {'name': 'Test Product 1', 'quantity': 2, 'price': 25.99},
                {'name': 'Test Product 2', 'quantity': 1, 'price': 49.99}
            ],
            'totalAmount': 101.97,
            'timestamp': datetime.now().timestamp()
        }
        
        html_content = generate_order_confirmation_email(order_data)
        
        # Verify email contains expected content
        assert 'Order Confirmation' in html_content
        assert 'test-order-123' in html_content
        assert 'John Doe' in html_content
        assert 'Test Product 1' in html_content
        assert 'Test Product 2' in html_content
        assert '$101.97' in html_content
        assert 'E-Com67' in html_content
    
    def test_generate_order_status_update_email(self):
        """Test order status update email generation"""
        order_data = {
            'orderId': 'test-order-456',
            'customerName': 'Jane Smith',
            'status': 'SHIPPED',
            'trackingNumber': 'TRACK123456'
        }
        
        html_content = generate_order_status_update_email(order_data)
        
        # Verify email contains expected content
        assert 'Order Has Been Shipped' in html_content
        assert 'test-order-456' in html_content
        assert 'Jane Smith' in html_content
        assert 'SHIPPED' in html_content
        assert 'TRACK123456' in html_content
    
    @patch('email_notification.ses_client')
    def test_email_handler_success(self, mock_ses_client):
        """Test successful email sending"""
        # Mock SES response
        mock_ses_client.send_email.return_value = {
            'MessageId': 'test-message-id-123'
        }
        
        event = {
            'notificationType': 'order_confirmation',
            'recipientEmail': 'test@example.com',
            'orderData': {
                'orderId': 'test-order-789',
                'customerName': 'Test Customer',
                'items': [{'name': 'Test Product', 'quantity': 1, 'price': 29.99}],
                'totalAmount': 29.99
            }
        }
        
        context = Mock()
        response = email_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Email sent successfully'
        assert body['messageId'] == 'test-message-id-123'
        assert body['recipient'] == 'test@example.com'
        
        # Verify SES was called
        mock_ses_client.send_email.assert_called_once()
    
    def test_email_handler_validation_error(self):
        """Test email handler with missing required fields"""
        event = {
            'recipientEmail': 'test@example.com'
            # Missing notificationType
        }
        
        context = Mock()
        response = email_handler(event, context)
        
        # Verify error response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'notificationType is required' in body['message']


class TestNotificationOrchestratorFunction:
    """Test cases for notification orchestrator function"""
    
    def test_get_user_preferences_default(self):
        """Test getting default user preferences when none exist"""
        with patch('notification_orchestrator.dynamodb') as mock_dynamodb:
            # Mock DynamoDB response - no item found
            mock_table = Mock()
            mock_table.get_item.return_value = {}
            mock_dynamodb.Table.return_value = mock_table
            
            preferences = get_user_preferences('test-user-123')
            
            # Verify default preferences are returned
            assert 'email' in preferences
            assert 'sms' in preferences
            assert preferences['email']['order_confirmation'] is True
            assert preferences['sms']['order_confirmation'] is False
    
    def test_should_send_notification(self):
        """Test notification sending decision logic"""
        user_preferences = {
            'email': {
                'order_confirmation': True,
                'promotional': False
            },
            'sms': {
                'order_confirmation': False,
                'order_status_update': True
            }
        }
        
        # Test cases
        assert should_send_notification('order_confirmation', 'email', user_preferences) is True
        assert should_send_notification('promotional', 'email', user_preferences) is False
        assert should_send_notification('order_confirmation', 'sms', user_preferences) is False
        assert should_send_notification('order_status_update', 'sms', user_preferences) is True
    
    @patch('notification_orchestrator.lambda_client')
    @patch('notification_orchestrator.get_user_preferences')
    @patch('notification_orchestrator.record_notification_analytics')
    def test_orchestrator_handler_success(self, mock_analytics, mock_preferences, mock_lambda_client):
        """Test successful notification orchestration"""
        # Mock user preferences - email enabled
        mock_preferences.return_value = {
            'email': {'order_confirmation': True},
            'sms': {'order_confirmation': False}
        }
        
        # Mock Lambda invocation
        mock_lambda_client.invoke.return_value = {'StatusCode': 202}
        
        event = {
            'userId': 'test-user-456',
            'notificationType': 'order_confirmation',
            'recipientEmail': 'test@example.com',
            'orderData': {
                'orderId': 'test-order-999',
                'customerName': 'Test User',
                'totalAmount': 75.50
            }
        }
        
        context = Mock()
        response = orchestrator_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'Notification processed' in body['message']
        assert body['userId'] == 'test-user-456'
        assert body['notificationType'] == 'order_confirmation'
        
        # Verify Lambda was invoked for email
        mock_lambda_client.invoke.assert_called_once()
        
        # Verify analytics were recorded
        mock_analytics.assert_called_once()
    
    def test_orchestrator_handler_validation_error(self):
        """Test orchestrator handler with missing required fields"""
        event = {
            'notificationType': 'order_confirmation'
            # Missing userId
        }
        
        context = Mock()
        response = orchestrator_handler(event, context)
        
        # Verify error response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Bad Request'
        assert 'userId is required' in body['message']


class TestNotificationIntegration:
    """Integration tests for notification system"""
    
    @patch('notification_orchestrator.lambda_client')
    @patch('notification_orchestrator.sns_client')
    @patch('notification_orchestrator.get_user_preferences')
    @patch('notification_orchestrator.record_notification_analytics')
    def test_multi_channel_notification(self, mock_analytics, mock_preferences, mock_sns, mock_lambda):
        """Test multi-channel notification processing"""
        # Mock user preferences - both channels enabled
        mock_preferences.return_value = {
            'email': {'order_status_update': True},
            'sms': {'order_status_update': True}
        }
        
        # Mock successful responses
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_sns.publish.return_value = {'MessageId': 'sms-message-id-123'}
        
        event = {
            'userId': 'test-user-789',
            'notificationType': 'order_status_update',
            'recipientEmail': 'test@example.com',
            'recipientPhone': '+1234567890',
            'orderData': {
                'orderId': 'test-order-111',
                'customerName': 'Multi Channel User',
                'status': 'SHIPPED',
                'trackingNumber': 'TRACK789'
            }
        }
        
        context = Mock()
        response = orchestrator_handler(event, context)
        
        # Verify successful response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Should have processed 2 channels (email + SMS)
        assert body['results']['successful'] >= 1  # At least one should succeed
        
        # Verify both services were called
        mock_lambda.invoke.assert_called()  # Email function
        mock_sns.publish.assert_called()    # SMS service


if __name__ == '__main__':
    pytest.main([__file__])