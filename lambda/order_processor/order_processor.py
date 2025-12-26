"""
Order Processor Lambda Function

Handles asynchronous order fulfillment triggered by SQS messages.
Implements order creation, inventory updates, and notification sending.
"""

import json
import os
import uuid
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

# Import utilities from layer
from utils.validators import ValidationError
from utils.exceptions import BusinessLogicError
from utils.formatters import format_timestamp

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="E-Com67")

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
sqs = boto3.client('sqs')
cognito = boto3.client('cognito-idp')

def get_orders_table():
    """Get orders table with lazy initialization"""
    return dynamodb.Table(os.environ['ORDERS_TABLE_NAME'])

def get_products_table():
    """Get products table with lazy initialization"""
    return dynamodb.Table(os.environ['PRODUCTS_TABLE_NAME'])

def get_cart_table():
    """Get cart table with lazy initialization"""
    return dynamodb.Table(os.environ['CART_TABLE_NAME'])


@tracer.capture_method
def get_user_email_from_cognito(user_id: str) -> Optional[str]:
    """
    Retrieve user's email address from Cognito User Pool.

    Args:
        user_id: The Cognito user ID (sub)

    Returns:
        User's email address or None if not found
    """
    user_pool_id = os.environ.get('USER_POOL_ID')

    if not user_pool_id:
        logger.warning("USER_POOL_ID not configured, cannot lookup user email")
        return None

    try:
        # Use admin_get_user to retrieve user attributes
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )

        # Extract email from user attributes
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                logger.info("Retrieved email from Cognito", extra={"user_id": user_id})
                return attr['Value']

        logger.warning("Email attribute not found for user", extra={"user_id": user_id})
        return None

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            logger.warning("User not found in Cognito", extra={"user_id": user_id})
        else:
            logger.error("Failed to get user from Cognito", extra={
                "user_id": user_id,
                "error": str(e)
            })
        return None


class OrderProcessorService:
    """Service class for order processing operations"""
    
    @staticmethod
    @tracer.capture_method
    def process_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process order from SQS message"""
        logger.info("Processing order", extra={"order_data": order_data})
        
        try:
            # Extract order details from Step Functions payload structure
            user_id = order_data['userId']
            order_id = order_data.get('orderId') or str(uuid.uuid4())
            
            # Cart validation results are nested in the Step Functions payload
            cart_validation = order_data.get('cartValidation', {})
            cart_payload = cart_validation.get('Payload', {})
            items = cart_payload.get('items', [])
            
            # If items not found in cart validation, try root level (for backward compatibility)
            if not items:
                items = order_data.get('items', [])
            
            if not items:
                raise BusinessLogicError("No items found in order data. Cart validation may have failed.")
            
            payment_id = order_data.get('paymentId')
            payment_method_id = order_data.get('paymentMethodId')
            
            logger.info("Processing order", extra={
                "order_id": order_id,
                "user_id": user_id,
                "items_count": len(items),
                "has_payment_id": bool(payment_id),
                "has_payment_method_id": bool(payment_method_id)
            })
            
            # Create order record with cart validation data
            order_record = OrderProcessorService._create_order_record(
                order_id, user_id, items, order_data, payment_id or payment_method_id, cart_payload
            )
            
            # Update inventory
            inventory_updates = OrderProcessorService._update_inventory(items)
            
            # Clear user's cart
            cart_cleared = OrderProcessorService._clear_user_cart(user_id)
            
            # Send notifications (pass order_data to get recipientEmail and customer info)
            notification_sent = OrderProcessorService._send_order_notifications(order_record, order_data)
            
            # Update order status to completed
            OrderProcessorService._update_order_status(order_id, 'completed')
            
            logger.info("Order processed successfully", extra={
                "order_id": order_id,
                "user_id": user_id,
                "items_count": len(items)
            })
            metrics.add_metric(name="OrderProcessed", unit=MetricUnit.Count, value=1)
            
            return {
                'success': True,
                'orderId': order_id,
                'userId': user_id,
                'inventoryUpdated': inventory_updates,
                'cartCleared': cart_cleared,
                'notificationSent': notification_sent,
                'processedAt': int(time.time())
            }
            
        except Exception as e:
            logger.error("Order processing failed", extra={"error": str(e), "order_data": order_data})
            metrics.add_metric(name="OrderProcessingError", unit=MetricUnit.Count, value=1)
            
            # Update order status to failed if order_id exists
            order_id = order_data.get('orderId')
            if order_id:
                OrderProcessorService._update_order_status(order_id, 'failed', str(e))
            
            raise BusinessLogicError(f"Order processing failed: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def _create_order_record(order_id: str, user_id: str, items: List[Dict], order_data: Dict, payment_id: str, cart_data: Dict = None) -> Dict[str, Any]:
        """Create order record in DynamoDB"""
        logger.info("Creating order record", extra={"order_id": order_id, "user_id": user_id})
        
        current_time = int(time.time())
        
        # Use cart validation totals if available, otherwise calculate
        if cart_data and 'totalAmount' in cart_data:
            subtotal = Decimal(str(cart_data.get('subtotal', 0)))
            tax_amount = Decimal(str(cart_data.get('taxAmount', 0)))
            total_amount = Decimal(str(cart_data.get('totalAmount', 0)))
        else:
            # Fallback calculation
            subtotal = Decimal('0')
            for item in items:
                item_total = Decimal(str(item['price'])) * item['quantity']
                subtotal += item_total
            
            tax_rate = Decimal('0.08')  # 8% tax rate - would be configurable
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
        
        # Convert all numeric values to Decimal for DynamoDB compatibility
        items_for_db = OrderProcessorService._convert_items_to_decimal(items)
        
        order_record = {
            'orderId': order_id,
            'userId': user_id,
            'items': items_for_db,
            'subtotal': subtotal,
            'taxAmount': tax_amount,
            'totalAmount': total_amount,
            'status': 'processing',
            'paymentId': payment_id,
            'paymentStatus': 'paid',
            'shippingAddress': order_data.get('shippingAddress', {}),
            'timestamp': current_time,
            'createdAt': current_time,
            'updatedAt': current_time
        }
        
        try:
            get_orders_table().put_item(Item=order_record)
            
            logger.info("Order record created", extra={"order_id": order_id})
            metrics.add_metric(name="OrderRecordCreated", unit=MetricUnit.Count, value=1)
            
            # Convert Decimal objects for return
            order_record['subtotal'] = float(order_record['subtotal'])
            order_record['taxAmount'] = float(order_record['taxAmount'])
            order_record['totalAmount'] = float(order_record['totalAmount'])
            
            return order_record
            
        except ClientError as e:
            logger.error("Failed to create order record", extra={"order_id": order_id, "error": str(e)})
            raise BusinessLogicError(f"Failed to create order record: {str(e)}")
    
    @staticmethod
    def _convert_items_to_decimal(items: List[Dict]) -> List[Dict]:
        """Convert all numeric values in items to Decimal for DynamoDB compatibility"""
        converted_items = []
        
        for item in items:
            converted_item = {}
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    converted_item[key] = Decimal(str(value))
                else:
                    converted_item[key] = value
            converted_items.append(converted_item)
        
        return converted_items
    
    @staticmethod
    @tracer.capture_method
    def _update_inventory(items: List[Dict]) -> List[Dict[str, Any]]:
        """Update product inventory for ordered items"""
        logger.info("Updating inventory", extra={"items_count": len(items)})
        
        inventory_updates = []
        products_table = get_products_table()
        
        for item in items:
            product_id = item['productId']
            quantity_ordered = item['quantity']
            
            try:
                # Update product stock using atomic counter
                response = products_table.update_item(
                    Key={'productId': product_id},
                    UpdateExpression="ADD stock :quantity_decrease SET updatedAt = :updated_at",
                    ExpressionAttributeValues={
                        ':quantity_decrease': -quantity_ordered,
                        ':updated_at': int(time.time())
                    },
                    ConditionExpression=Attr('stock').gte(quantity_ordered),
                    ReturnValues='ALL_NEW'
                )
                
                updated_product = response['Attributes']
                new_stock = int(updated_product['stock'])
                
                inventory_updates.append({
                    'productId': product_id,
                    'quantityOrdered': quantity_ordered,
                    'newStock': new_stock,
                    'success': True
                })
                
                logger.info("Inventory updated", extra={
                    "product_id": product_id,
                    "quantity_ordered": quantity_ordered,
                    "new_stock": new_stock
                })
                
                # Check for low stock and send alert if needed
                if new_stock <= 10:  # Low stock threshold
                    OrderProcessorService._send_low_stock_alert(product_id, new_stock)
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    logger.error("Insufficient stock for product", extra={
                        "product_id": product_id,
                        "quantity_ordered": quantity_ordered
                    })
                    inventory_updates.append({
                        'productId': product_id,
                        'quantityOrdered': quantity_ordered,
                        'success': False,
                        'error': 'Insufficient stock'
                    })
                else:
                    logger.error("Failed to update inventory", extra={
                        "product_id": product_id,
                        "error": str(e)
                    })
                    inventory_updates.append({
                        'productId': product_id,
                        'quantityOrdered': quantity_ordered,
                        'success': False,
                        'error': str(e)
                    })
        
        metrics.add_metric(name="InventoryUpdated", unit=MetricUnit.Count, value=len(inventory_updates))
        return inventory_updates
    
    @staticmethod
    @tracer.capture_method
    def _clear_user_cart(user_id: str) -> bool:
        """Clear user's cart after successful order"""
        logger.info("Clearing user cart", extra={"user_id": user_id})
        
        try:
            cart_table = get_cart_table()
            
            # Get all cart items for user
            response = cart_table.query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            
            cart_items = response.get('Items', [])
            
            if not cart_items:
                logger.info("Cart already empty", extra={"user_id": user_id})
                return True
            
            # Delete all cart items
            with cart_table.batch_writer() as batch:
                for item in cart_items:
                    batch.delete_item(
                        Key={
                            'userId': item['userId'],
                            'productId': item['productId']
                        }
                    )
            
            logger.info("Cart cleared", extra={"user_id": user_id, "items_removed": len(cart_items)})
            metrics.add_metric(name="CartClearedAfterOrder", unit=MetricUnit.Count, value=1)
            
            return True
            
        except ClientError as e:
            logger.error("Failed to clear cart", extra={"user_id": user_id, "error": str(e)})
            return False
    
    @staticmethod
    @tracer.capture_method
    def _send_order_notifications(order_record: Dict[str, Any], order_data: Dict[str, Any]) -> bool:
        """Send order confirmation notifications.

        Args:
            order_record: The created order record with order details
            order_data: Original order data from checkout flow (may contain phone, shippingAddress, etc.)

        Returns:
            True if notification was sent successfully
        """
        logger.info("Sending order notifications", extra={"order_id": order_record['orderId']})

        try:
            # Get SNS topic ARN from environment
            topic_arn = os.environ.get('ORDER_NOTIFICATIONS_TOPIC_ARN')

            if not topic_arn:
                logger.warning("Order notifications topic ARN not configured")
                return False

            # Get user email from Cognito using the userId
            user_id = order_record['userId']
            recipient_email = get_user_email_from_cognito(user_id)

            if not recipient_email:
                logger.warning("Could not retrieve email for user from Cognito", extra={
                    "order_id": order_record['orderId'],
                    "user_id": user_id
                })

            # Extract customer name from order_data or shipping address
            shipping_address = order_data.get('shippingAddress', {})
            customer_name = (
                order_data.get('customerName') or
                shipping_address.get('name') or
                shipping_address.get('fullName') or
                'Valued Customer'
            )

            # Prepare notification message with full data for email/SMS generation
            notification_message = {
                'notificationType': 'order_confirmation',
                'userId': user_id,
                'recipientEmail': recipient_email,
                'recipientPhone': order_data.get('recipientPhone') or order_data.get('phone'),
                'orderData': {
                    'orderId': order_record['orderId'],
                    'customerName': customer_name,
                    'items': order_record.get('items', []),
                    'subtotal': order_record.get('subtotal', 0),
                    'taxAmount': order_record.get('taxAmount', 0),
                    'totalAmount': order_record['totalAmount'],
                    'status': order_record.get('status', 'processing'),
                    'timestamp': order_record['timestamp'],
                    'shippingAddress': shipping_address
                }
            }

            # Send to SNS topic
            sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(notification_message, default=str),  # default=str handles Decimal
                Subject=f"Order Confirmation - {order_record['orderId']}",
                MessageAttributes={
                    'notificationType': {
                        'DataType': 'String',
                        'StringValue': 'order_confirmation'
                    },
                    'userId': {
                        'DataType': 'String',
                        'StringValue': order_record['userId']
                    }
                }
            )

            logger.info("Order notification sent", extra={
                "order_id": order_record['orderId'],
                "has_email": bool(recipient_email)
            })
            metrics.add_metric(name="OrderNotificationSent", unit=MetricUnit.Count, value=1)

            return True

        except Exception as e:
            logger.error("Failed to send order notification", extra={
                "order_id": order_record['orderId'],
                "error": str(e)
            })
            return False
    
    @staticmethod
    @tracer.capture_method
    def _send_low_stock_alert(product_id: str, current_stock: int):
        """Send low stock alert notification"""
        logger.info("Sending low stock alert", extra={"product_id": product_id, "stock": current_stock})
        
        try:
            # Get SNS topic ARN for admin notifications
            topic_arn = os.environ.get('ADMIN_NOTIFICATIONS_TOPIC_ARN')
            
            if not topic_arn:
                logger.warning("Admin notifications topic ARN not configured")
                return
            
            # Prepare alert message
            alert_message = {
                'type': 'low_stock_alert',
                'productId': product_id,
                'currentStock': current_stock,
                'threshold': 10,
                'timestamp': int(time.time())
            }
            
            # Send to SNS topic
            sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(alert_message),
                Subject=f"Low Stock Alert - Product {product_id}",
                MessageAttributes={
                    'alertType': {
                        'DataType': 'String',
                        'StringValue': 'low_stock'
                    },
                    'productId': {
                        'DataType': 'String',
                        'StringValue': product_id
                    }
                }
            )
            
            logger.info("Low stock alert sent", extra={"product_id": product_id})
            metrics.add_metric(name="LowStockAlertSent", unit=MetricUnit.Count, value=1)
            
        except Exception as e:
            logger.error("Failed to send low stock alert", extra={
                "product_id": product_id,
                "error": str(e)
            })
    
    @staticmethod
    @tracer.capture_method
    def _update_order_status(order_id: str, status: str, error_message: Optional[str] = None):
        """Update order status in DynamoDB"""
        logger.info("Updating order status", extra={"order_id": order_id, "status": status})
        
        try:
            update_expression = "SET #status = :status, updatedAt = :updated_at"
            expression_values = {
                ':status': status,
                ':updated_at': int(time.time())
            }
            expression_names = {'#status': 'status'}
            
            if error_message:
                update_expression += ", errorMessage = :error_message"
                expression_values[':error_message'] = error_message
            
            get_orders_table().update_item(
                Key={'orderId': order_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info("Order status updated", extra={"order_id": order_id, "status": status})
            
        except ClientError as e:
            logger.error("Failed to update order status", extra={
                "order_id": order_id,
                "status": status,
                "error": str(e)
            })


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for order processing from SQS"""
    
    logger.info("Order processor function invoked", extra={"event": event})
    
    try:
        # Process SQS records
        records = event.get('Records', [])
        
        for record in records:
            try:
                # Parse SQS message
                message_body = json.loads(record['body'])
                
                # Process the order
                result = OrderProcessorService.process_order(message_body)
                
                logger.info("Order processed from SQS", extra={
                    "order_id": result['orderId'],
                    "message_id": record.get('messageId')
                })
                
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in SQS message", extra={
                    "message_id": record.get('messageId'),
                    "error": str(e)
                })
                metrics.add_metric(name="InvalidSQSMessage", unit=MetricUnit.Count, value=1)
                
                # Send to dead letter queue (handled by SQS configuration)
                raise e
                
            except BusinessLogicError as e:
                logger.error("Business logic error processing order", extra={
                    "message_id": record.get('messageId'),
                    "error": str(e)
                })
                metrics.add_metric(name="OrderProcessingBusinessError", unit=MetricUnit.Count, value=1)
                
                # Send to dead letter queue (handled by SQS configuration)
                raise e
                
            except Exception as e:
                logger.exception("Unexpected error processing order")
                metrics.add_metric(name="OrderProcessingUnexpectedError", unit=MetricUnit.Count, value=1)
                
                # Send to dead letter queue (handled by SQS configuration)
                raise e
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(records)} orders'
            })
        }
        
    except Exception as e:
        logger.exception("Unexpected error in order processor function")
        metrics.add_metric(name="OrderProcessorUnexpectedError", unit=MetricUnit.Count, value=1)
        
        # Re-raise to trigger SQS retry mechanism
        raise e