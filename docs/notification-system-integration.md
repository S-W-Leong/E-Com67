# E-Com67 Notification System Integration Guide

## Overview

The E-Com67 notification system provides multi-channel notifications (email and SMS) for order-related events. This guide explains how to integrate the notification system with existing order processing workflows.

## Architecture

```
Order Processing → SNS Topic → Notification Orchestrator → Email/SMS Services
```

## Components

### 1. Email Notification Function
- **Function**: `e-com67-email-notification`
- **Purpose**: Generates and sends HTML emails using Amazon SES
- **Templates**: Order confirmation, status updates
- **Features**: HTML email generation, personalization, delivery tracking

### 2. Notification Orchestrator Function
- **Function**: `e-com67-notification-orchestrator`
- **Purpose**: Routes notifications to appropriate channels based on user preferences
- **Features**: Multi-channel routing, retry logic, analytics tracking

### 3. DynamoDB Tables
- **notification-preferences**: User notification preferences
- **notification-analytics**: Delivery tracking and reporting

## Integration Examples

### 1. Order Confirmation Notification

When an order is successfully processed, publish to the SNS topic:

```python
import boto3
import json

sns_client = boto3.client('sns')

# Order confirmation notification
notification_data = {
    'userId': 'user-123',
    'notificationType': 'order_confirmation',
    'recipientEmail': 'customer@example.com',
    'recipientPhone': '+1234567890',  # Optional
    'orderData': {
        'orderId': 'order-456',
        'customerName': 'John Doe',
        'items': [
            {
                'name': 'Product A',
                'quantity': 2,
                'price': 29.99
            }
        ],
        'totalAmount': 59.98,
        'timestamp': 1702555200
    }
}

# Publish to SNS topic
sns_client.publish(
    TopicArn='arn:aws:sns:region:account:e-com67-order-notifications',
    Message=json.dumps(notification_data)
)
```

### 2. Order Status Update Notification

When order status changes (shipped, delivered, etc.):

```python
# Order status update notification
notification_data = {
    'userId': 'user-123',
    'notificationType': 'order_status_update',
    'recipientEmail': 'customer@example.com',
    'recipientPhone': '+1234567890',
    'orderData': {
        'orderId': 'order-456',
        'customerName': 'John Doe',
        'status': 'SHIPPED',
        'trackingNumber': 'TRACK123456'
    }
}

sns_client.publish(
    TopicArn='arn:aws:sns:region:account:e-com67-order-notifications',
    Message=json.dumps(notification_data)
)
```

### 3. Direct Function Invocation

For immediate notifications, you can invoke the orchestrator directly:

```python
import boto3
import json

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='e-com67-notification-orchestrator',
    InvocationType='Event',  # Asynchronous
    Payload=json.dumps(notification_data)
)
```

## User Preferences Management

### Default Preferences
```json
{
    "email": {
        "order_confirmation": true,
        "order_status_update": true,
        "promotional": false,
        "system_maintenance": true
    },
    "sms": {
        "order_confirmation": false,
        "order_status_update": true,
        "promotional": false,
        "system_maintenance": false
    }
}
```

### Setting User Preferences
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('e-com67-notification-preferences')

# Update user preferences
table.put_item(
    Item={
        'userId': 'user-123',
        'preferences': {
            'email': {
                'order_confirmation': True,
                'order_status_update': True,
                'promotional': True
            },
            'sms': {
                'order_confirmation': False,
                'order_status_update': True
            }
        },
        'updatedAt': int(datetime.now().timestamp())
    }
)
```

## SES Configuration

### Required SES Setup
1. **Verify sender email domain** in Amazon SES
2. **Move out of sandbox** for production use
3. **Configure bounce/complaint handling**
4. **Set up reputation monitoring**

### Environment Variables
```bash
SENDER_EMAIL=noreply@e-com67.com
SENDER_NAME=E-Com67 Platform
```

## Monitoring and Analytics

### CloudWatch Metrics
- `EmailNotificationSuccess`
- `EmailNotificationFailure`
- `SmsNotificationSuccess`
- `SmsNotificationFailure`
- `NotificationSent`
- `ChannelsUsed`

### Analytics Queries
```python
# Get notification analytics for a user
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('e-com67-notification-analytics')

response = table.query(
    IndexName='userId-timestamp-index',
    KeyConditionExpression='userId = :userId',
    ExpressionAttributeValues={
        ':userId': 'user-123'
    },
    ScanIndexForward=False,  # Latest first
    Limit=10
)

analytics = response['Items']
```

## Error Handling

### Retry Logic
- **Email failures**: 3 retries with exponential backoff
- **SMS failures**: 3 retries with exponential backoff
- **Dead letter queue**: Failed notifications after all retries

### Common Issues
1. **SES not configured**: Verify domain and move out of sandbox
2. **Invalid phone numbers**: Ensure E.164 format for SMS
3. **User preferences not found**: System uses defaults
4. **Lambda timeout**: Increase timeout for large email templates

## Testing

### Unit Tests
```bash
python -m pytest tests/test_notification_system.py -v
```

### Integration Testing
```python
# Test notification end-to-end
import boto3
import json

# Invoke orchestrator with test data
lambda_client = boto3.client('lambda')
test_event = {
    'userId': 'test-user',
    'notificationType': 'order_confirmation',
    'recipientEmail': 'test@example.com',
    'orderData': {
        'orderId': 'test-order',
        'customerName': 'Test User',
        'totalAmount': 99.99
    }
}

response = lambda_client.invoke(
    FunctionName='e-com67-notification-orchestrator',
    Payload=json.dumps(test_event)
)
```

## Deployment

The notification system is deployed as part of the CDK compute stack:

```bash
# Deploy the updated stack
cdk deploy E-Com67-ComputeStack
```

## Future Enhancements

1. **Push notifications** for mobile apps
2. **Webhook notifications** for third-party integrations
3. **Advanced templating** with dynamic content
4. **A/B testing** for notification effectiveness
5. **Delivery scheduling** for optimal timing