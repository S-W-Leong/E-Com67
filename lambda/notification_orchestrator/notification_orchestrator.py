"""
E-Com67 Notification Orchestrator Function

This Lambda function orchestrates multi-channel notifications by routing
messages to appropriate channels based on user preferences and notification type.

Features:
- Multi-channel notification routing (email, SMS)
- User preference processing
- Delivery scheduling and retry logic
- Notification analytics and reporting
- Template management system
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

# Initialize AWS services
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="E-Com67")

# Configuration
EMAIL_FUNCTION_NAME = os.environ.get('EMAIL_FUNCTION_NAME', 'e-com67-email-notification')
NOTIFICATION_PREFERENCES_TABLE = os.environ.get('NOTIFICATION_PREFERENCES_TABLE', 'e-com67-notification-preferences')
NOTIFICATION_ANALYTICS_TABLE = os.environ.get('NOTIFICATION_ANALYTICS_TABLE', 'e-com67-notification-analytics')

# Default notification preferences
DEFAULT_PREFERENCES = {
    'email': {
        'order_confirmation': True,
        'order_status_update': True,
        'promotional': False,
        'system_maintenance': True
    },
    'sms': {
        'order_confirmation': False,
        'order_status_update': True,
        'promotional': False,
        'system_maintenance': False
    }
}


@tracer.capture_method
def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """
    Get user notification preferences from DynamoDB.
    
    Args:
        user_id: User identifier
        
    Returns:
        User notification preferences or defaults
    """
    try:
        table = dynamodb.Table(NOTIFICATION_PREFERENCES_TABLE)
        response = table.get_item(Key={'userId': user_id})
        
        if 'Item' in response:
            preferences = response['Item'].get('preferences', DEFAULT_PREFERENCES)
            logger.info(f"Retrieved preferences for user {user_id}")
            return preferences
        else:
            logger.info(f"No preferences found for user {user_id}, using defaults")
            return DEFAULT_PREFERENCES
            
    except Exception as e:
        logger.error(f"Error retrieving preferences for user {user_id}: {str(e)}")
        return DEFAULT_PREFERENCES


@tracer.capture_method
def should_send_notification(
    notification_type: str,
    channel: str,
    user_preferences: Dict[str, Any]
) -> bool:
    """
    Determine if notification should be sent based on user preferences.
    
    Args:
        notification_type: Type of notification (e.g., 'order_confirmation')
        channel: Notification channel ('email' or 'sms')
        user_preferences: User's notification preferences
        
    Returns:
        True if notification should be sent
    """
    try:
        channel_prefs = user_preferences.get(channel, {})
        return channel_prefs.get(notification_type, False)
    except Exception as e:
        logger.error(f"Error checking notification preferences: {str(e)}")
        # Default to sending critical notifications
        return notification_type in ['order_confirmation', 'order_status_update']


@tracer.capture_method
def send_email_notification(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send email notification by invoking the email function.
    
    Args:
        notification_data: Notification payload
        
    Returns:
        Email sending result
    """
    try:
        response = lambda_client.invoke(
            FunctionName=EMAIL_FUNCTION_NAME,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(notification_data)
        )
        
        logger.info(f"Email notification queued for {notification_data.get('recipientEmail')}")
        
        return {
            'success': True,
            'channel': 'email',
            'status': 'queued'
        }
        
    except Exception as e:
        logger.error(f"Failed to queue email notification: {str(e)}")
        return {
            'success': False,
            'channel': 'email',
            'error': str(e)
        }


@tracer.capture_method
def send_sms_notification(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send SMS notification using Amazon SNS.
    
    Args:
        notification_data: Notification payload
        
    Returns:
        SMS sending result
    """
    try:
        phone_number = notification_data.get('recipientPhone')
        if not phone_number:
            return {
                'success': False,
                'channel': 'sms',
                'error': 'No phone number provided'
            }
        
        # Generate SMS message based on notification type
        message = generate_sms_message(notification_data)
        
        # Send SMS via SNS
        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        logger.info(f"SMS notification sent to {phone_number}", extra={
            "message_id": response['MessageId']
        })
        
        return {
            'success': True,
            'channel': 'sms',
            'messageId': response['MessageId']
        }
        
    except Exception as e:
        logger.error(f"Failed to send SMS notification: {str(e)}")
        return {
            'success': False,
            'channel': 'sms',
            'error': str(e)
        }


@tracer.capture_method
def generate_sms_message(notification_data: Dict[str, Any]) -> str:
    """
    Generate SMS message content based on notification type.

    Handles two data formats:
    1. Direct invocation with nested orderData
    2. SNS message from order_processor with flat structure

    Args:
        notification_data: Notification payload

    Returns:
        SMS message text
    """
    notification_type = notification_data.get('notificationType') or notification_data.get('type')

    # Handle both nested orderData format and flat SNS message format
    order_data = notification_data.get('orderData', {})
    # For flat SNS format, orderId/totalAmount are at top level
    order_id = order_data.get('orderId') or notification_data.get('orderId', 'N/A')
    total_amount = order_data.get('totalAmount') or notification_data.get('totalAmount', 0)

    if notification_type == 'order_confirmation':
        return f"E-Com67: Order {order_id} confirmed! Total: ${total_amount:.2f}. Thank you for your purchase!"

    elif notification_type == 'order_status_update':
        status = order_data.get('status', 'PROCESSING')
        if status == 'SHIPPED':
            tracking_number = order_data.get('trackingNumber', '')
            if tracking_number:
                return f"E-Com67: Order {order_id} shipped! Tracking: {tracking_number}"
            else:
                return f"E-Com67: Order {order_id} has been shipped!"
        elif status == 'DELIVERED':
            return f"E-Com67: Order {order_id} delivered! We hope you enjoy your purchase."
        else:
            return f"E-Com67: Order {order_id} status updated to {status}."

    else:
        return f"E-Com67: You have a new notification regarding order {order_id}."


@tracer.capture_method
def record_notification_analytics(
    user_id: str,
    notification_type: str,
    channels: List[str],
    results: List[Dict[str, Any]]
) -> None:
    """
    Record notification analytics for reporting.
    
    Args:
        user_id: User identifier
        notification_type: Type of notification
        channels: List of channels used
        results: Results from each channel
    """
    try:
        table = dynamodb.Table(NOTIFICATION_ANALYTICS_TABLE)
        
        # Create analytics record
        analytics_record = {
            'notificationId': f"{user_id}#{int(datetime.now().timestamp() * 1000)}",
            'userId': user_id,
            'notificationType': notification_type,
            'timestamp': int(datetime.now().timestamp()),
            'channels': channels,
            'results': results,
            'totalChannels': len(channels),
            'successfulChannels': len([r for r in results if r.get('success', False)]),
            'failedChannels': len([r for r in results if not r.get('success', False)])
        }
        
        table.put_item(Item=analytics_record)
        
        logger.info(f"Recorded notification analytics for user {user_id}")
        
        # Update metrics
        metrics.add_metric(name="NotificationSent", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ChannelsUsed", unit=MetricUnit.Count, value=len(channels))
        
        for result in results:
            if result.get('success'):
                metrics.add_metric(
                    name=f"{result['channel'].title()}NotificationSuccess",
                    unit=MetricUnit.Count,
                    value=1
                )
            else:
                metrics.add_metric(
                    name=f"{result['channel'].title()}NotificationFailure",
                    unit=MetricUnit.Count,
                    value=1
                )
        
    except Exception as e:
        logger.error(f"Failed to record notification analytics: {str(e)}")


@tracer.capture_method
def process_notification_with_retry(
    notification_data: Dict[str, Any],
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Process notification with retry logic for failed channels.
    
    Args:
        notification_data: Notification payload
        max_retries: Maximum number of retry attempts
        
    Returns:
        List of results from each channel attempt
    """
    user_id = notification_data.get('userId')
    notification_type = notification_data.get('notificationType')
    
    # Get user preferences
    user_preferences = get_user_preferences(user_id)
    
    # Determine which channels to use
    channels_to_use = []
    if should_send_notification(notification_type, 'email', user_preferences):
        channels_to_use.append('email')
    if should_send_notification(notification_type, 'sms', user_preferences):
        channels_to_use.append('sms')
    
    if not channels_to_use:
        logger.info(f"No channels enabled for user {user_id} and notification type {notification_type}")
        return []
    
    results = []
    
    # Process each channel
    for channel in channels_to_use:
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                if channel == 'email':
                    result = send_email_notification(notification_data)
                elif channel == 'sms':
                    result = send_sms_notification(notification_data)
                else:
                    result = {
                        'success': False,
                        'channel': channel,
                        'error': f'Unsupported channel: {channel}'
                    }
                
                if result.get('success'):
                    success = True
                    results.append(result)
                    logger.info(f"Successfully sent {channel} notification to user {user_id}")
                else:
                    retry_count += 1
                    if retry_count <= max_retries:
                        logger.warning(f"Retrying {channel} notification for user {user_id} (attempt {retry_count})")
                    else:
                        results.append(result)
                        logger.error(f"Failed to send {channel} notification to user {user_id} after {max_retries} retries")
                
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"Exception in {channel} notification for user {user_id}, retrying: {str(e)}")
                else:
                    results.append({
                        'success': False,
                        'channel': channel,
                        'error': str(e)
                    })
                    logger.error(f"Exception in {channel} notification for user {user_id} after {max_retries} retries: {str(e)}")
    
    return results


@tracer.capture_method
def extract_notification_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract notification data from various event sources.

    Handles:
    - Direct invocation: event contains notification data directly
    - SNS trigger: event contains Records with SNS envelope

    Args:
        event: Raw Lambda event

    Returns:
        Extracted notification data
    """
    # Check if this is an SNS event (has Records array with Sns data)
    if 'Records' in event and len(event['Records']) > 0:
        record = event['Records'][0]

        # SNS event format
        if 'Sns' in record:
            sns_message = record['Sns'].get('Message', '{}')
            try:
                notification_data = json.loads(sns_message)
                logger.info("Extracted notification from SNS event", extra={
                    "message_id": record['Sns'].get('MessageId'),
                    "subject": record['Sns'].get('Subject')
                })
                return notification_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SNS message: {str(e)}")
                raise ValueError(f"Invalid JSON in SNS message: {str(e)}")

        # EventBridge or other event source with Records
        elif 'body' in record:
            try:
                return json.loads(record['body'])
            except json.JSONDecodeError:
                return record

    # Direct invocation - event is the notification data
    return event


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for notification orchestration.

    Supports multiple invocation sources:

    1. Direct invocation format:
    {
        "userId": "user-uuid",
        "notificationType": "order_confirmation" | "order_status_update" | "promotional" | "system_maintenance",
        "recipientEmail": "customer@example.com",
        "recipientPhone": "+1234567890",  // Optional
        "orderData": {
            "orderId": "order-uuid",
            "customerName": "John Doe",
            "items": [...],
            "totalAmount": 99.99,
            "status": "PROCESSING",
            ...
        }
    }

    2. SNS trigger format (from order_processor):
    {
        "Records": [{
            "Sns": {
                "Message": "{\"type\":\"order_confirmation\",\"orderId\":\"...\",\"userId\":\"...\",...}"
            }
        }]
    }

    Args:
        event: Lambda event containing notification details
        context: Lambda context

    Returns:
        Response with notification processing results
    """
    try:
        logger.info("Processing notification orchestration request", extra={"event": event})

        # Extract notification data from event (handles SNS envelope)
        notification_data = extract_notification_from_event(event)
        logger.info("Extracted notification data", extra={"notification_data": notification_data})

        # Extract notification details
        # Support both 'userId' and SNS message format with 'type' field
        user_id = notification_data.get('userId')
        notification_type = notification_data.get('notificationType') or notification_data.get('type')

        # Validate required fields
        if not user_id:
            raise ValueError("userId is required")
        if not notification_type:
            raise ValueError("notificationType is required")
        
        # Normalize notification data to ensure consistent field names
        # SNS messages from order_processor use 'type' instead of 'notificationType'
        normalized_data = notification_data.copy()
        if 'notificationType' not in normalized_data and 'type' in normalized_data:
            normalized_data['notificationType'] = normalized_data['type']

        # Process notification with retry logic
        results = process_notification_with_retry(normalized_data)
        
        # Record analytics
        channels_used = [r['channel'] for r in results]
        record_notification_analytics(user_id, notification_type, channels_used, results)
        
        # Prepare response
        successful_channels = [r for r in results if r.get('success', False)]
        failed_channels = [r for r in results if not r.get('success', False)]
        
        response = {
            'statusCode': 200 if successful_channels else 500,
            'body': json.dumps({
                'message': f'Notification processed for {len(successful_channels)} of {len(results)} channels',
                'userId': user_id,
                'notificationType': notification_type,
                'results': {
                    'successful': len(successful_channels),
                    'failed': len(failed_channels),
                    'details': results
                }
            })
        }
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Bad Request',
                'message': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing notification orchestration: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to process notification'
            })
        }