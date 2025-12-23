"""
E-Com67 Email Notification Function

This Lambda function handles email notifications using Amazon SES.
It generates HTML emails from templates and sends them to customers.

Features:
- HTML email generation from templates
- Email personalization with dynamic content
- SES integration for reliable delivery
- Bounce and complaint handling
- Delivery monitoring and tracking
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

# Initialize AWS services
ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'ap-southeast-1'))
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="E-Com67")

# Configuration
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'mt-swleong@axrail.com')
SENDER_NAME = os.environ.get('SENDER_NAME', 'E-Com67 Platform')


@tracer.capture_method
def generate_order_confirmation_email(order_data: Dict[str, Any]) -> str:
    """
    Generate HTML email for order confirmation.
    
    Args:
        order_data: Order information including items, total, and customer details
        
    Returns:
        HTML email content
    """
    order_id = order_data.get('orderId', 'N/A')
    customer_name = order_data.get('customerName', 'Valued Customer')
    items = order_data.get('items', [])
    total_amount = order_data.get('totalAmount', 0)
    order_date = order_data.get('timestamp', datetime.now().timestamp())
    
    # Format order date
    order_date_str = datetime.fromtimestamp(order_date).strftime('%B %d, %Y at %I:%M %p')
    
    # Generate items HTML
    items_html = ""
    for item in items:
        item_name = item.get('name', 'Unknown Product')
        item_quantity = item.get('quantity', 1)
        item_price = item.get('price', 0)
        item_total = item_quantity * item_price
        
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{item_name}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item_quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${item_price:.2f}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${item_total:.2f}</td>
        </tr>
        """
    
    # Generate complete HTML email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Confirmation</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
            <h1 style="color: #007bff; margin: 0;">E-Com67</h1>
        </div>
        
        <div style="background-color: #fff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px;">
            <h2 style="color: #28a745; margin-top: 0;">Order Confirmation</h2>
            
            <p>Dear {customer_name},</p>
            
            <p>Thank you for your order! We're excited to confirm that we've received your order and it's being processed.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Order Number:</strong> {order_id}</p>
                <p style="margin: 5px 0;"><strong>Order Date:</strong> {order_date_str}</p>
            </div>
            
            <h3 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Order Details</h3>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Product</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #dee2e6;">Quantity</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Price</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    <tr style="background-color: #f8f9fa; font-weight: bold;">
                        <td colspan="3" style="padding: 15px; text-align: right; border-top: 2px solid #dee2e6;">Total Amount:</td>
                        <td style="padding: 15px; text-align: right; border-top: 2px solid #dee2e6; color: #28a745;">${total_amount:.2f}</td>
                    </tr>
                </tfoot>
            </table>
            
            <div style="background-color: #e7f3ff; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                <p style="margin: 0;"><strong>What's Next?</strong></p>
                <p style="margin: 10px 0 0 0;">We'll send you another email once your order has been shipped with tracking information.</p>
            </div>
            
            <p>If you have any questions about your order, please don't hesitate to contact our customer support team.</p>
            
            <p>Thank you for shopping with E-Com67!</p>
            
            <p style="margin-top: 30px;">
                Best regards,<br>
                <strong>The E-Com67 Team</strong>
            </p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 12px;">
            <p>This is an automated email. Please do not reply to this message.</p>
            <p>&copy; 2025 E-Com67 Platform. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


@tracer.capture_method
def generate_order_status_update_email(order_data: Dict[str, Any]) -> str:
    """
    Generate HTML email for order status updates.
    
    Args:
        order_data: Order information including status and tracking details
        
    Returns:
        HTML email content
    """
    order_id = order_data.get('orderId', 'N/A')
    customer_name = order_data.get('customerName', 'Valued Customer')
    status = order_data.get('status', 'PROCESSING')
    tracking_number = order_data.get('trackingNumber', '')
    
    # Status-specific messages
    status_messages = {
        'PROCESSING': {
            'title': 'Order is Being Processed',
            'message': 'Your order is currently being prepared for shipment.',
            'color': '#007bff'
        },
        'SHIPPED': {
            'title': 'Order Has Been Shipped',
            'message': 'Great news! Your order is on its way to you.',
            'color': '#17a2b8'
        },
        'DELIVERED': {
            'title': 'Order Delivered',
            'message': 'Your order has been successfully delivered. We hope you enjoy your purchase!',
            'color': '#28a745'
        },
        'CANCELLED': {
            'title': 'Order Cancelled',
            'message': 'Your order has been cancelled as requested.',
            'color': '#dc3545'
        }
    }
    
    status_info = status_messages.get(status, status_messages['PROCESSING'])
    
    # Add tracking information if available
    tracking_html = ""
    if tracking_number and status == 'SHIPPED':
        tracking_html = f"""
        <div style="background-color: #e7f3ff; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
            <p style="margin: 0;"><strong>Tracking Number:</strong> {tracking_number}</p>
            <p style="margin: 10px 0 0 0;">You can track your package using this tracking number.</p>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Status Update</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
            <h1 style="color: #007bff; margin: 0;">E-Com67</h1>
        </div>
        
        <div style="background-color: #fff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px;">
            <h2 style="color: {status_info['color']}; margin-top: 0;">{status_info['title']}</h2>
            
            <p>Dear {customer_name},</p>
            
            <p>{status_info['message']}</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Order Number:</strong> {order_id}</p>
                <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: {status_info['color']};">{status}</span></p>
            </div>
            
            {tracking_html}
            
            <p>If you have any questions about your order, please don't hesitate to contact our customer support team.</p>
            
            <p style="margin-top: 30px;">
                Best regards,<br>
                <strong>The E-Com67 Team</strong>
            </p>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 12px;">
            <p>This is an automated email. Please do not reply to this message.</p>
            <p>&copy; 2025 E-Com67 Platform. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content


@tracer.capture_method
def send_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email using Amazon SES.
    
    Args:
        recipient_email: Recipient's email address
        subject: Email subject line
        html_content: HTML email content
        text_content: Plain text email content (optional)
        
    Returns:
        SES response with message ID
        
    Raises:
        Exception: If email sending fails
    """
    try:
        # Prepare email message
        message = {
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_content,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        # Add plain text version if provided
        if text_content:
            message['Body']['Text'] = {
                'Data': text_content,
                'Charset': 'UTF-8'
            }
        
        # Send email via SES
        response = ses_client.send_email(
            Source=f"{SENDER_NAME} <{SENDER_EMAIL}>",
            Destination={
                'ToAddresses': [recipient_email]
            },
            Message=message
        )
        
        logger.info(f"Email sent successfully to {recipient_email}", extra={
            "message_id": response['MessageId'],
            "recipient": recipient_email,
            "subject": subject
        })
        
        metrics.add_metric(name="EmailSent", unit=MetricUnit.Count, value=1)
        
        return {
            'success': True,
            'messageId': response['MessageId'],
            'recipient': recipient_email
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}", extra={
            "error": str(e),
            "recipient": recipient_email,
            "subject": subject
        })
        
        metrics.add_metric(name="EmailFailed", unit=MetricUnit.Count, value=1)
        
        raise


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for email notification processing.
    
    Event format:
    {
        "notificationType": "order_confirmation" | "order_status_update",
        "recipientEmail": "customer@example.com",
        "orderData": {
            "orderId": "order-uuid",
            "customerName": "John Doe",
            "items": [...],
            "totalAmount": 99.99,
            "status": "PROCESSING",
            ...
        }
    }
    
    Args:
        event: Lambda event containing notification details
        context: Lambda context
        
    Returns:
        Response with email sending status
    """
    try:
        logger.info("Processing email notification request", extra={"event": event})
        
        # Extract notification details
        notification_type = event.get('notificationType')
        recipient_email = event.get('recipientEmail')
        order_data = event.get('orderData', {})
        
        # Validate required fields
        if not notification_type:
            raise ValueError("notificationType is required")
        if not recipient_email:
            raise ValueError("recipientEmail is required")
        
        # Generate email content based on notification type
        if notification_type == 'order_confirmation':
            subject = f"Order Confirmation - {order_data.get('orderId', 'N/A')}"
            html_content = generate_order_confirmation_email(order_data)
            
        elif notification_type == 'order_status_update':
            status = order_data.get('status', 'PROCESSING')
            subject = f"Order Status Update - {status}"
            html_content = generate_order_status_update_email(order_data)
            
        else:
            raise ValueError(f"Unsupported notification type: {notification_type}")
        
        # Send email
        result = send_email(recipient_email, subject, html_content)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Email sent successfully',
                'messageId': result['messageId'],
                'recipient': result['recipient']
            })
        }
        
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
        logger.error(f"Error processing email notification: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'Failed to send email notification'
            })
        }
