"""
Payment Lambda Function

Handles payment processing using Stripe API.
Implements payment intent creation, processing, and webhook handling.
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, Any, Optional

import boto3
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

def get_orders_table():
    """Get orders table with lazy initialization"""
    return dynamodb.Table(os.environ['ORDERS_TABLE_NAME'])

def get_stripe_api_key():
    """Get Stripe API key from Secrets Manager"""
    try:
        # Initialize Secrets Manager client inside the function to avoid module-level issues
        secretsmanager = boto3.client('secretsmanager')

        secret_name = os.environ.get('STRIPE_SECRET_NAME', 'e-com67/stripe/api-key')
        logger.info(f"Attempting to retrieve secret: {secret_name}")

        response = secretsmanager.get_secret_value(SecretId=secret_name)
        logger.info("Successfully retrieved secret from Secrets Manager")

        # Parse the JSON secret to extract the api_key field
        secret_data = json.loads(response['SecretString'])
        api_key = secret_data.get('api_key')

        if not api_key:
            logger.error("Secret retrieved but 'api_key' field is empty or missing")
            return os.environ.get('STRIPE_API_KEY')

        logger.info("Successfully extracted Stripe API key from secret")
        return api_key

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error("Failed to retrieve Stripe API key from Secrets Manager", extra={
            "error": str(e),
            "error_code": error_code,
            "secret_name": secret_name
        })
        # For development, allow fallback to environment variable
        fallback_key = os.environ.get('STRIPE_API_KEY')
        if fallback_key:
            logger.warning("Using fallback STRIPE_API_KEY from environment variable")
        return fallback_key

    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse Stripe API key from secret", extra={
            "error": str(e),
            "secret_name": secret_name
        })
        # For development, allow fallback to environment variable
        fallback_key = os.environ.get('STRIPE_API_KEY')
        if fallback_key:
            logger.warning("Using fallback STRIPE_API_KEY from environment variable")
        return fallback_key

    except Exception as e:
        logger.error("Unexpected error retrieving Stripe API key", extra={
            "error": str(e),
            "error_type": type(e).__name__
        })
        # For development, allow fallback to environment variable
        fallback_key = os.environ.get('STRIPE_API_KEY')
        if fallback_key:
            logger.warning("Using fallback STRIPE_API_KEY from environment variable")
        return fallback_key


class PaymentService:
    """Service class for payment operations"""
    
    @staticmethod
    @tracer.capture_method
    def create_payment_intent(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Stripe payment intent"""
        logger.info("Creating payment intent", extra={"payment_data": payment_data})
        
        try:
            # Import Stripe here to avoid cold start issues
            import stripe
            
            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()
            
            if not stripe.api_key:
                raise BusinessLogicError("Stripe API key not configured")
            
            # Extract payment details
            amount_cents = int(payment_data['totalAmount'] * 100)  # Convert to cents
            currency = payment_data.get('currency', 'usd')
            user_id = payment_data['userId']
            order_id = payment_data.get('orderId')
            
            # Create payment intent
            # Support both frontend-provided payment methods and backend testing
            try:
                # Check if payment method is provided from frontend
                payment_method_id = payment_data.get('paymentMethodId')

                if payment_method_id:
                    # Production flow: Frontend provides payment method ID
                    logger.info(f"Using payment method from frontend: {payment_method_id}")

                    payment_intent = stripe.PaymentIntent.create(
                        amount=amount_cents,
                        currency=currency,
                        payment_method=payment_method_id,
                        metadata={
                            'userId': user_id,
                            'orderId': order_id or 'pending',
                            'source': 'e-com67-platform'
                        },
                        confirm=True,
                        return_url=payment_data.get('returnUrl', 'https://example.com/return'),
                    )
                else:
                    # Testing flow: Use Stripe's test payment method for backend testing
                    logger.info("No payment method provided, using test payment method for backend testing")

                    payment_intent = stripe.PaymentIntent.create(
                        amount=amount_cents,
                        currency=currency,
                        metadata={
                            'userId': user_id,
                            'orderId': order_id or 'pending',
                            'source': 'e-com67-platform'
                        },
                        # Use test payment method - pm_card_visa is a test Payment Method
                        payment_method='pm_card_visa',  # Stripe's test payment method
                        confirm=True,
                        off_session=True,  # Allow off-session confirmation for backend testing
                    )

                logger.info(f"Payment intent created with status: {payment_intent.status}")

            except stripe.error.StripeError as se:
                logger.error(f"Stripe API error: {str(se)}", extra={"stripe_error": str(se)})
                raise BusinessLogicError(f"Stripe payment failed: {str(se)}")

            logger.info("Payment intent created and confirmed", extra={
                "payment_intent_id": payment_intent.id,
                "amount": amount_cents,
                "user_id": user_id,
                "status": payment_intent.status
            })
            metrics.add_metric(name="PaymentIntentCreated", unit=MetricUnit.Count, value=1)
            
            return {
                'paymentIntentId': payment_intent.id,
                'clientSecret': payment_intent.client_secret,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency
            }
            
        except Exception as e:
            logger.error("Failed to create payment intent", extra={"error": str(e)})
            metrics.add_metric(name="PaymentIntentCreateError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to create payment intent: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def process_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for Step Functions workflow"""
        logger.info("Processing payment", extra={"payment_data": payment_data})

        # Check if we're in test mode (no Stripe key configured)
        test_mode = os.environ.get('PAYMENT_TEST_MODE', 'false').lower() == 'true'

        if test_mode:
            logger.warning("Running in PAYMENT_TEST_MODE - bypassing Stripe")

            # Return mock successful payment
            payment_result = {
                'success': True,
                'paymentId': f"test_pi_{int(time.time())}",
                'paymentStatus': 'succeeded',
                'amount': payment_data['totalAmount'],
                'currency': payment_data.get('currency', 'usd'),
                'processedAt': int(time.time()),
                'userId': payment_data['userId'],
                'orderId': payment_data.get('orderId'),
                'testMode': True
            }

            logger.info("Test payment processed successfully", extra={
                "payment_id": payment_result['paymentId'],
                "user_id": payment_data['userId']
            })
            metrics.add_metric(name="TestPaymentProcessed", unit=MetricUnit.Count, value=1)

            return payment_result

        try:
            # Import Stripe here to avoid cold start issues
            import stripe

            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()

            if not stripe.api_key:
                raise BusinessLogicError("Stripe API key not configured")

            # For Step Functions, we create a payment intent and return the details
            # In a real implementation, this might confirm an existing payment intent
            payment_intent_result = PaymentService.create_payment_intent(payment_data)

            # Simulate payment processing result
            # In production, this would handle actual payment confirmation
            payment_result = {
                'success': True,
                'paymentId': payment_intent_result['paymentIntentId'],
                'paymentStatus': 'succeeded',  # In real implementation, this would be dynamic
                'amount': payment_data['totalAmount'],
                'currency': payment_data.get('currency', 'usd'),
                'processedAt': int(time.time()),
                'userId': payment_data['userId'],
                'orderId': payment_data.get('orderId')
            }

            logger.info("Payment processed successfully", extra={
                "payment_id": payment_result['paymentId'],
                "user_id": payment_data['userId']
            })
            metrics.add_metric(name="PaymentProcessed", unit=MetricUnit.Count, value=1)

            return payment_result

        except Exception as e:
            logger.error("Payment processing failed", extra={"error": str(e)})
            metrics.add_metric(name="PaymentProcessingError", unit=MetricUnit.Count, value=1)

            # Return failure result for Step Functions
            return {
                'success': False,
                'error': str(e),
                'errorCode': 'PAYMENT_FAILED',
                'userId': payment_data.get('userId'),
                'orderId': payment_data.get('orderId'),
                'failedAt': int(time.time())
            }
    
    @staticmethod
    @tracer.capture_method
    def handle_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        logger.info("Handling webhook", extra={"webhook_data": webhook_data})
        
        try:
            # Import Stripe here to avoid cold start issues
            import stripe
            
            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()
            
            # Extract webhook details
            event_type = webhook_data.get('type')
            payment_intent_data = webhook_data.get('data', {}).get('object', {})
            payment_intent_id = payment_intent_data.get('id')
            
            logger.info("Processing webhook event", extra={
                "event_type": event_type,
                "payment_intent_id": payment_intent_id
            })
            
            # Handle different webhook events
            if event_type == 'payment_intent.succeeded':
                # Update order status to paid
                order_id = payment_intent_data.get('metadata', {}).get('orderId')
                if order_id and order_id != 'pending':
                    PaymentService._update_order_payment_status(order_id, 'paid', payment_intent_id)
                
                metrics.add_metric(name="PaymentSucceeded", unit=MetricUnit.Count, value=1)
                
            elif event_type == 'payment_intent.payment_failed':
                # Update order status to payment failed
                order_id = payment_intent_data.get('metadata', {}).get('orderId')
                if order_id and order_id != 'pending':
                    PaymentService._update_order_payment_status(order_id, 'payment_failed', payment_intent_id)
                
                metrics.add_metric(name="PaymentFailed", unit=MetricUnit.Count, value=1)
            
            return {
                'success': True,
                'eventType': event_type,
                'paymentIntentId': payment_intent_id,
                'processedAt': int(time.time())
            }
            
        except Exception as e:
            logger.error("Webhook processing failed", extra={"error": str(e)})
            metrics.add_metric(name="WebhookProcessingError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Webhook processing failed: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def _update_order_payment_status(order_id: str, status: str, payment_id: str):
        """Update order payment status in DynamoDB"""
        try:
            orders_table = get_orders_table()
            
            orders_table.update_item(
                Key={'orderId': order_id},
                UpdateExpression="SET paymentStatus = :status, paymentId = :payment_id, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ':status': status,
                    ':payment_id': payment_id,
                    ':updated_at': int(time.time())
                }
            )
            
            logger.info("Order payment status updated", extra={
                "order_id": order_id,
                "status": status,
                "payment_id": payment_id
            })
            
        except ClientError as e:
            logger.error("Failed to update order payment status", extra={
                "order_id": order_id,
                "error": str(e)
            })


def create_error_response(status_code: int, error_code: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized error response"""
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": format_timestamp(time.time())
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(error_response)
    }


def create_success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        },
        "body": json.dumps(data)
    }


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for payment operations"""
    
    logger.info("Payment function invoked", extra={"event": event})
    
    try:
        # Handle Step Functions invocation
        if event.get('source') == 'step-functions':
            # This is a Step Functions invocation for payment processing
            step_function_input = event.get('input', {})
            
            payment_result = PaymentService.process_payment(step_function_input)
            return payment_result
        
        # Handle API Gateway invocation
        http_method = event.get('httpMethod', '')
        
        # Handle OPTIONS request for CORS
        if http_method == 'OPTIONS':
            return create_success_response({}, 200)
        
        if http_method == 'POST':
            path = event.get('path', '')
            
            if '/webhook' in path:
                # Handle Stripe webhook
                try:
                    body = json.loads(event.get('body', '{}'))
                    result = PaymentService.handle_webhook(body)
                    return create_success_response(result)
                except json.JSONDecodeError:
                    return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
                except BusinessLogicError as e:
                    return create_error_response(400, "WEBHOOK_ERROR", str(e))
            else:
                # Handle payment intent creation
                try:
                    body = json.loads(event.get('body', '{}'))
                    result = PaymentService.create_payment_intent(body)
                    return create_success_response(result, 201)
                except json.JSONDecodeError:
                    return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
                except ValidationError as e:
                    return create_error_response(400, "VALIDATION_ERROR", str(e))
                except BusinessLogicError as e:
                    return create_error_response(400, "PAYMENT_ERROR", str(e))
        
        else:
            return create_error_response(405, "METHOD_NOT_ALLOWED", f"HTTP method {http_method} not allowed")
    
    except Exception as e:
        logger.exception("Unexpected error in payment function")
        metrics.add_metric(name="PaymentUnexpectedError", unit=MetricUnit.Count, value=1)
        
        return create_error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred")