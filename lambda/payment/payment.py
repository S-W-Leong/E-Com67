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
    def validate_payment_data(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment data and perform fraud detection"""
        logger.info("Validating payment data", extra={"user_id": payment_data.get('userId')})
        
        # Basic validation
        required_fields = ['totalAmount', 'userId']
        for field in required_fields:
            if field not in payment_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Amount validation
        amount = payment_data['totalAmount']
        if not isinstance(amount, (int, float, Decimal)):
            raise ValidationError("Total amount must be a number")
        
        if amount <= 0:
            raise ValidationError("Total amount must be greater than zero")
        
        if amount > 999999.99:  # $999,999.99 limit
            raise ValidationError("Total amount exceeds maximum allowed limit")
        
        # Basic fraud detection checks
        fraud_score = 0
        fraud_reasons = []
        
        # Check for unusually high amounts
        if amount > 10000:  # $10,000 threshold
            fraud_score += 30
            fraud_reasons.append("High transaction amount")
        
        # Check for rapid successive payments (would need session tracking in production)
        # This is a simplified check - in production, you'd check against recent transactions
        
        # Currency validation
        currency = payment_data.get('currency', 'usd').lower()
        allowed_currencies = ['usd', 'eur', 'gbp', 'aud', 'cad']
        if currency not in allowed_currencies:
            raise ValidationError(f"Currency {currency} not supported")
        
        validation_result = {
            'isValid': fraud_score < 50,  # Threshold for blocking
            'fraudScore': fraud_score,
            'fraudReasons': fraud_reasons,
            'validatedAmount': float(amount),
            'validatedCurrency': currency
        }
        
        logger.info("Payment validation completed", extra={
            "user_id": payment_data['userId'],
            "fraud_score": fraud_score,
            "is_valid": validation_result['isValid']
        })
        
        if fraud_score >= 50:
            metrics.add_metric(name="PaymentBlocked", unit=MetricUnit.Count, value=1)
            logger.warning("Payment blocked due to fraud detection", extra={
                "user_id": payment_data['userId'],
                "fraud_score": fraud_score,
                "reasons": fraud_reasons
            })
        
        return validation_result
    
    @staticmethod
    @tracer.capture_method
    def create_payment_intent(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Stripe payment intent with enhanced security"""
        logger.info("Creating payment intent", extra={"payment_data": payment_data})
        
        try:
            # Validate payment data first
            validation_result = PaymentService.validate_payment_data(payment_data)
            if not validation_result['isValid']:
                raise BusinessLogicError(f"Payment blocked: {', '.join(validation_result['fraudReasons'])}")
            
            # Import Stripe here to avoid cold start issues
            import stripe
            
            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()
            
            if not stripe.api_key:
                raise BusinessLogicError("Stripe API key not configured")
            
            # Extract validated payment details
            amount_cents = int(validation_result['validatedAmount'] * 100)  # Convert to cents
            currency = validation_result['validatedCurrency']
            user_id = payment_data['userId']
            order_id = payment_data.get('orderId')
            
            # Enhanced metadata for tracking and compliance
            metadata = {
                'userId': user_id,
                'orderId': order_id or 'pending',
                'source': 'e-com67-platform',
                'fraudScore': str(validation_result['fraudScore']),
                'timestamp': str(int(time.time())),
                'version': '1.0'
            }
            
            # Create payment intent with enhanced security features
            payment_intent_params = {
                'amount': amount_cents,
                'currency': currency,
                'metadata': metadata,
                'capture_method': 'automatic',  # PCI DSS compliant automatic capture
                'setup_future_usage': None,  # Don't store payment methods by default
            }
            
            # Check if payment method is provided from frontend
            payment_method_id = payment_data.get('paymentMethodId')
            
            if payment_method_id:
                # Production flow: Frontend provides payment method ID
                logger.info(f"Using payment method from frontend: {payment_method_id}")
                
                payment_intent_params.update({
                    'confirmation_method': 'automatic',
                    'payment_method': payment_method_id,
                    'confirm': True,
                    'return_url': payment_data.get('returnUrl', 'https://example.com/return'),
                    # Enable 3D Secure authentication when required
                    'payment_method_options': {
                        'card': {
                            'request_three_d_secure': 'automatic'  # Let Stripe decide when to use 3DS
                        }
                    }
                })
            else:
                # Frontend flow: Use automatic payment methods (no specific payment method provided)
                logger.info("No payment method provided, using automatic payment methods")
                payment_intent_params.update({
                    'automatic_payment_methods': {'enabled': True},
                })
            
            # Create the payment intent
            payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
            
            logger.info("Payment intent created", extra={
                "payment_intent_id": payment_intent.id,
                "amount": amount_cents,
                "user_id": user_id,
                "status": payment_intent.status,
                "requires_action": payment_intent.status == 'requires_action'
            })
            
            metrics.add_metric(name="PaymentIntentCreated", unit=MetricUnit.Count, value=1)
            
            # Track 3D Secure usage
            if payment_intent.status == 'requires_action':
                metrics.add_metric(name="Payment3DSRequired", unit=MetricUnit.Count, value=1)
            
            return {
                'paymentIntentId': payment_intent.id,
                'clientSecret': payment_intent.client_secret,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'requiresAction': payment_intent.status == 'requires_action',
                'nextAction': payment_intent.next_action if payment_intent.status == 'requires_action' else None
            }
            
        except stripe.error.CardError as e:
            # Card was declined
            logger.warning("Card declined", extra={
                "error": str(e),
                "decline_code": e.decline_code,
                "user_id": payment_data.get('userId')
            })
            metrics.add_metric(name="PaymentCardDeclined", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Card declined: {e.user_message}")
            
        except stripe.error.RateLimitError as e:
            # Rate limiting
            logger.error("Stripe rate limit exceeded", extra={"error": str(e)})
            metrics.add_metric(name="PaymentRateLimited", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError("Payment service temporarily unavailable. Please try again.")
            
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters
            logger.error("Invalid Stripe request", extra={"error": str(e)})
            metrics.add_metric(name="PaymentInvalidRequest", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError("Invalid payment request")
            
        except stripe.error.AuthenticationError as e:
            # Authentication failed
            logger.error("Stripe authentication failed", extra={"error": str(e)})
            metrics.add_metric(name="PaymentAuthError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError("Payment service configuration error")
            
        except stripe.error.APIConnectionError as e:
            # Network communication failed
            logger.error("Stripe API connection failed", extra={"error": str(e)})
            metrics.add_metric(name="PaymentConnectionError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError("Payment service temporarily unavailable")
            
        except stripe.error.StripeError as e:
            # Generic Stripe error
            logger.error("Stripe error", extra={"error": str(e)})
            metrics.add_metric(name="PaymentStripeError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Payment processing error: {str(e)}")
            
        except Exception as e:
            logger.error("Failed to create payment intent", extra={"error": str(e)})
            metrics.add_metric(name="PaymentIntentCreateError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to create payment intent: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def process_payment_with_retry(payment_data: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Process payment with retry logic for Step Functions workflow"""
        max_retries = 3
        base_delay = 2  # seconds
        
        logger.info("Processing payment with retry", extra={
            "payment_data": payment_data,
            "retry_count": retry_count,
            "max_retries": max_retries
        })
        
        try:
            return PaymentService.process_payment(payment_data)
        except Exception as e:
            if retry_count < max_retries:
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** retry_count)
                
                logger.warning("Payment failed, retrying", extra={
                    "error": str(e),
                    "retry_count": retry_count,
                    "delay_seconds": delay,
                    "user_id": payment_data.get('userId')
                })
                
                metrics.add_metric(name="PaymentRetryAttempt", unit=MetricUnit.Count, value=1)
                
                # In a real implementation, you'd use time.sleep(delay) here
                # For Step Functions, the retry is handled by the state machine
                return PaymentService.process_payment_with_retry(payment_data, retry_count + 1)
            else:
                logger.error("Payment failed after all retries", extra={
                    "error": str(e),
                    "retry_count": retry_count,
                    "user_id": payment_data.get('userId')
                })
                metrics.add_metric(name="PaymentFailedAfterRetries", unit=MetricUnit.Count, value=1)
                raise e
    
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

            # Validate payment data first
            validation_result = PaymentService.validate_payment_data(payment_data)
            if not validation_result['isValid']:
                raise BusinessLogicError(f"Payment validation failed: {', '.join(validation_result['fraudReasons'])}")

            # Check if we have an existing payment intent to confirm
            payment_intent_id = payment_data.get('paymentIntentId')
            
            if payment_intent_id:
                # Confirm existing payment intent
                logger.info("Confirming existing payment intent", extra={
                    "payment_intent_id": payment_intent_id
                })
                
                payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)
                
            else:
                # Create and confirm new payment intent
                payment_intent_result = PaymentService.create_payment_intent(payment_data)
                payment_intent_id = payment_intent_result['paymentIntentId']
                
                # Retrieve the payment intent to get current status
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Track payment status
            PaymentService._track_payment_status(payment_intent, payment_data.get('userId'))
            
            # Determine success based on payment intent status
            success = payment_intent.status in ['succeeded', 'requires_capture']
            
            payment_result = {
                'success': success,
                'paymentId': payment_intent.id,
                'paymentStatus': payment_intent.status,
                'amount': payment_data['totalAmount'],
                'currency': payment_data.get('currency', 'usd'),
                'processedAt': int(time.time()),
                'userId': payment_data['userId'],
                'orderId': payment_data.get('orderId'),
                'requiresAction': payment_intent.status == 'requires_action',
                'nextAction': payment_intent.next_action if payment_intent.status == 'requires_action' else None
            }

            if success:
                logger.info("Payment processed successfully", extra={
                    "payment_id": payment_result['paymentId'],
                    "user_id": payment_data['userId'],
                    "status": payment_intent.status
                })
                metrics.add_metric(name="PaymentProcessed", unit=MetricUnit.Count, value=1)
            else:
                logger.warning("Payment requires additional action", extra={
                    "payment_id": payment_result['paymentId'],
                    "user_id": payment_data['userId'],
                    "status": payment_intent.status
                })
                metrics.add_metric(name="PaymentRequiresAction", unit=MetricUnit.Count, value=1)

            return payment_result

        except (BusinessLogicError, ValidationError) as e:
            # Business logic and validation errors should not be retried
            logger.error("Payment business logic error", extra={"error": str(e)})
            metrics.add_metric(name="PaymentBusinessLogicError", unit=MetricUnit.Count, value=1)
            
            return {
                'success': False,
                'error': str(e),
                'errorCode': 'PAYMENT_VALIDATION_FAILED',
                'userId': payment_data.get('userId'),
                'orderId': payment_data.get('orderId'),
                'failedAt': int(time.time()),
                'retryable': False
            }
            
        except Exception as e:
            logger.error("Payment processing failed", extra={"error": str(e)})
            metrics.add_metric(name="PaymentProcessingError", unit=MetricUnit.Count, value=1)

            # Determine if error is retryable
            retryable = PaymentService._is_retryable_error(e)

            # Return failure result for Step Functions
            return {
                'success': False,
                'error': str(e),
                'errorCode': 'PAYMENT_FAILED',
                'userId': payment_data.get('userId'),
                'orderId': payment_data.get('orderId'),
                'failedAt': int(time.time()),
                'retryable': retryable
            }
    
    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        """Determine if an error is retryable"""
        import stripe
        
        # Network and temporary errors are retryable
        retryable_errors = (
            stripe.error.APIConnectionError,
            stripe.error.RateLimitError,
        )
        
        # Card errors and authentication errors are not retryable
        non_retryable_errors = (
            stripe.error.CardError,
            stripe.error.InvalidRequestError,
            stripe.error.AuthenticationError,
        )
        
        if isinstance(error, retryable_errors):
            return True
        elif isinstance(error, non_retryable_errors):
            return False
        else:
            # For unknown errors, allow retry
            return True
    
    @staticmethod
    def _track_payment_status(payment_intent, user_id: str):
        """Track payment status for monitoring and analytics"""
        status = payment_intent.status
        
        # Track different payment statuses
        status_metrics = {
            'succeeded': 'PaymentSucceeded',
            'requires_action': 'PaymentRequires3DS',
            'requires_payment_method': 'PaymentRequiresPaymentMethod',
            'requires_confirmation': 'PaymentRequiresConfirmation',
            'requires_capture': 'PaymentRequiresCapture',
            'canceled': 'PaymentCanceled',
            'processing': 'PaymentProcessing'
        }
        
        metric_name = status_metrics.get(status, 'PaymentUnknownStatus')
        metrics.add_metric(name=metric_name, unit=MetricUnit.Count, value=1)
        
        logger.info("Payment status tracked", extra={
            "payment_intent_id": payment_intent.id,
            "status": status,
            "user_id": user_id,
            "metric": metric_name
        })
    
    @staticmethod
    @tracer.capture_method
    def verify_webhook_signature(payload: str, signature: str, webhook_secret: str) -> bool:
        """Verify Stripe webhook signature for security"""
        try:
            import stripe
            import hmac
            import hashlib
            
            # Extract timestamp and signature from header
            elements = signature.split(',')
            timestamp = None
            signatures = []
            
            for element in elements:
                key, value = element.split('=', 1)
                if key == 't':
                    timestamp = value
                elif key == 'v1':
                    signatures.append(value)
            
            if not timestamp or not signatures:
                logger.error("Invalid webhook signature format")
                return False
            
            # Check timestamp (prevent replay attacks)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:  # 5 minutes tolerance
                logger.error("Webhook timestamp too old", extra={
                    "timestamp": timestamp,
                    "current_time": current_time
                })
                return False
            
            # Compute expected signature
            signed_payload = f"{timestamp}.{payload}"
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            for signature in signatures:
                if hmac.compare_digest(expected_signature, signature):
                    return True
            
            logger.error("Webhook signature verification failed")
            return False
            
        except Exception as e:
            logger.error("Webhook signature verification error", extra={"error": str(e)})
            return False
    
    @staticmethod
    @tracer.capture_method
    def handle_webhook(webhook_data: Dict[str, Any], signature: str = None, raw_payload: str = None) -> Dict[str, Any]:
        """Handle Stripe webhook events with signature verification"""
        logger.info("Handling webhook", extra={
            "event_type": webhook_data.get('type'),
            "event_id": webhook_data.get('id')
        })
        
        try:
            # Import Stripe here to avoid cold start issues
            import stripe
            
            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()
            
            # Verify webhook signature if provided
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            if webhook_secret and signature and raw_payload:
                if not PaymentService.verify_webhook_signature(raw_payload, signature, webhook_secret):
                    logger.error("Webhook signature verification failed")
                    metrics.add_metric(name="WebhookSignatureVerificationFailed", unit=MetricUnit.Count, value=1)
                    raise BusinessLogicError("Webhook signature verification failed")
                
                logger.info("Webhook signature verified successfully")
                metrics.add_metric(name="WebhookSignatureVerified", unit=MetricUnit.Count, value=1)
            else:
                logger.warning("Webhook signature verification skipped - no secret configured")
            
            # Extract webhook details
            event_type = webhook_data.get('type')
            event_id = webhook_data.get('id')
            
            # Process different webhook events
            result = PaymentService._process_webhook_event(webhook_data)
            
            logger.info("Webhook processed successfully", extra={
                "event_type": event_type,
                "event_id": event_id,
                "result": result
            })
            
            metrics.add_metric(name="WebhookProcessed", unit=MetricUnit.Count, value=1)
            
            return {
                'success': True,
                'eventType': event_type,
                'eventId': event_id,
                'processedAt': int(time.time()),
                'result': result
            }
            
        except BusinessLogicError as e:
            logger.error("Webhook business logic error", extra={"error": str(e)})
            metrics.add_metric(name="WebhookBusinessLogicError", unit=MetricUnit.Count, value=1)
            raise e
            
        except Exception as e:
            logger.error("Webhook processing failed", extra={"error": str(e)})
            metrics.add_metric(name="WebhookProcessingError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Webhook processing failed: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def _process_webhook_event(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific webhook event types"""
        event_type = webhook_data.get('type')
        event_data = webhook_data.get('data', {}).get('object', {})
        
        logger.info("Processing webhook event", extra={
            "event_type": event_type,
            "object_id": event_data.get('id')
        })
        
        # Payment Intent Events
        if event_type == 'payment_intent.succeeded':
            return PaymentService._handle_payment_succeeded(event_data)
            
        elif event_type == 'payment_intent.payment_failed':
            return PaymentService._handle_payment_failed(event_data)
            
        elif event_type == 'payment_intent.requires_action':
            return PaymentService._handle_payment_requires_action(event_data)
            
        elif event_type == 'payment_intent.canceled':
            return PaymentService._handle_payment_canceled(event_data)
        
        # Charge Events (for additional tracking)
        elif event_type == 'charge.succeeded':
            return PaymentService._handle_charge_succeeded(event_data)
            
        elif event_type == 'charge.failed':
            return PaymentService._handle_charge_failed(event_data)
        
        # Refund Events
        elif event_type == 'charge.refunded':
            return PaymentService._handle_charge_refunded(event_data)
        
        # Dispute Events
        elif event_type == 'charge.dispute.created':
            return PaymentService._handle_dispute_created(event_data)
        
        else:
            logger.info("Unhandled webhook event type", extra={"event_type": event_type})
            metrics.add_metric(name="WebhookUnhandledEvent", unit=MetricUnit.Count, value=1)
            return {'status': 'ignored', 'reason': 'unhandled_event_type'}
    
    @staticmethod
    def _handle_payment_succeeded(payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment"""
        payment_intent_id = payment_intent_data.get('id')
        order_id = payment_intent_data.get('metadata', {}).get('orderId')
        
        logger.info("Processing payment success", extra={
            "payment_intent_id": payment_intent_id,
            "order_id": order_id
        })
        
        if order_id and order_id != 'pending':
            PaymentService._update_order_payment_status(order_id, 'paid', payment_intent_id)
            
            # Trigger order fulfillment notification
            PaymentService._notify_order_paid(order_id, payment_intent_id)
        
        metrics.add_metric(name="WebhookPaymentSucceeded", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'order_marked_paid'}
    
    @staticmethod
    def _handle_payment_failed(payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment"""
        payment_intent_id = payment_intent_data.get('id')
        order_id = payment_intent_data.get('metadata', {}).get('orderId')
        
        logger.info("Processing payment failure", extra={
            "payment_intent_id": payment_intent_id,
            "order_id": order_id
        })
        
        if order_id and order_id != 'pending':
            PaymentService._update_order_payment_status(order_id, 'payment_failed', payment_intent_id)
            
            # Notify about payment failure
            PaymentService._notify_payment_failed(order_id, payment_intent_id)
        
        metrics.add_metric(name="WebhookPaymentFailed", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'order_marked_failed'}
    
    @staticmethod
    def _handle_payment_requires_action(payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment requiring additional action (3D Secure)"""
        payment_intent_id = payment_intent_data.get('id')
        order_id = payment_intent_data.get('metadata', {}).get('orderId')
        
        logger.info("Processing payment requiring action", extra={
            "payment_intent_id": payment_intent_id,
            "order_id": order_id
        })
        
        if order_id and order_id != 'pending':
            PaymentService._update_order_payment_status(order_id, 'requires_action', payment_intent_id)
        
        metrics.add_metric(name="WebhookPaymentRequiresAction", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'order_requires_action'}
    
    @staticmethod
    def _handle_payment_canceled(payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle canceled payment"""
        payment_intent_id = payment_intent_data.get('id')
        order_id = payment_intent_data.get('metadata', {}).get('orderId')
        
        logger.info("Processing payment cancellation", extra={
            "payment_intent_id": payment_intent_id,
            "order_id": order_id
        })
        
        if order_id and order_id != 'pending':
            PaymentService._update_order_payment_status(order_id, 'canceled', payment_intent_id)
        
        metrics.add_metric(name="WebhookPaymentCanceled", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'order_marked_canceled'}
    
    @staticmethod
    def _handle_charge_succeeded(charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful charge (additional tracking)"""
        charge_id = charge_data.get('id')
        payment_intent_id = charge_data.get('payment_intent')
        
        logger.info("Processing charge success", extra={
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id
        })
        
        metrics.add_metric(name="WebhookChargeSucceeded", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'charge_tracked'}
    
    @staticmethod
    def _handle_charge_failed(charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed charge"""
        charge_id = charge_data.get('id')
        payment_intent_id = charge_data.get('payment_intent')
        failure_code = charge_data.get('failure_code')
        failure_message = charge_data.get('failure_message')
        
        logger.warning("Processing charge failure", extra={
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id,
            "failure_code": failure_code,
            "failure_message": failure_message
        })
        
        metrics.add_metric(name="WebhookChargeFailed", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'charge_failure_tracked'}
    
    @staticmethod
    def _handle_charge_refunded(charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle charge refund"""
        charge_id = charge_data.get('id')
        payment_intent_id = charge_data.get('payment_intent')
        refunds = charge_data.get('refunds', {}).get('data', [])
        
        logger.info("Processing charge refund", extra={
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id,
            "refund_count": len(refunds)
        })
        
        # Update order refund status if we can find the order
        # This would require looking up the order by payment_intent_id
        
        metrics.add_metric(name="WebhookChargeRefunded", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'refund_tracked'}
    
    @staticmethod
    def _handle_dispute_created(charge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dispute creation (chargeback)"""
        charge_id = charge_data.get('id')
        payment_intent_id = charge_data.get('payment_intent')
        
        logger.warning("Processing dispute creation", extra={
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id
        })
        
        # Notify admin about dispute
        PaymentService._notify_dispute_created(charge_id, payment_intent_id)
        
        metrics.add_metric(name="WebhookDisputeCreated", unit=MetricUnit.Count, value=1)
        return {'status': 'processed', 'action': 'dispute_tracked'}
    
    @staticmethod
    def _notify_order_paid(order_id: str, payment_intent_id: str):
        """Notify about successful payment"""
        # This would integrate with SNS or other notification service
        logger.info("Order payment notification", extra={
            "order_id": order_id,
            "payment_intent_id": payment_intent_id
        })
    
    @staticmethod
    def _notify_payment_failed(order_id: str, payment_intent_id: str):
        """Notify about failed payment"""
        # This would integrate with SNS or other notification service
        logger.warning("Payment failure notification", extra={
            "order_id": order_id,
            "payment_intent_id": payment_intent_id
        })
    
    @staticmethod
    def _notify_dispute_created(charge_id: str, payment_intent_id: str):
        """Notify admin about dispute"""
        # This would integrate with SNS or other notification service
        logger.warning("Dispute creation notification", extra={
            "charge_id": charge_id,
            "payment_intent_id": payment_intent_id
        })
    
    @staticmethod
    @tracer.capture_method
    def process_refund(refund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process refund for a payment"""
        logger.info("Processing refund", extra={"refund_data": refund_data})
        
        try:
            # Import Stripe here to avoid cold start issues
            import stripe
            
            # Set Stripe API key
            stripe.api_key = get_stripe_api_key()
            
            if not stripe.api_key:
                raise BusinessLogicError("Stripe API key not configured")
            
            # Extract refund details
            payment_intent_id = refund_data.get('paymentIntentId')
            amount_cents = refund_data.get('amount')  # Optional - full refund if not specified
            reason = refund_data.get('reason', 'requested_by_customer')
            order_id = refund_data.get('orderId')
            
            if not payment_intent_id:
                raise ValidationError("Payment intent ID is required for refund")
            
            # Validate refund reason
            valid_reasons = ['duplicate', 'fraudulent', 'requested_by_customer']
            if reason not in valid_reasons:
                reason = 'requested_by_customer'
            
            # Create refund parameters
            refund_params = {
                'payment_intent': payment_intent_id,
                'reason': reason,
                'metadata': {
                    'orderId': order_id or 'unknown',
                    'source': 'e-com67-platform',
                    'timestamp': str(int(time.time()))
                }
            }
            
            # Add amount if partial refund
            if amount_cents:
                refund_params['amount'] = int(amount_cents)
            
            # Create the refund
            refund = stripe.Refund.create(**refund_params)
            
            logger.info("Refund created", extra={
                "refund_id": refund.id,
                "payment_intent_id": payment_intent_id,
                "amount": refund.amount,
                "status": refund.status,
                "order_id": order_id
            })
            
            metrics.add_metric(name="RefundCreated", unit=MetricUnit.Count, value=1)
            
            # Update order status if order_id provided
            if order_id:
                PaymentService._update_order_refund_status(
                    order_id,
                    refund.id,
                    refund.status,
                    refund.amount
                )
            
            return {
                'success': True,
                'refundId': refund.id,
                'paymentIntentId': payment_intent_id,
                'amount': refund.amount,
                'currency': refund.currency,
                'status': refund.status,
                'reason': refund.reason,
                'processedAt': int(time.time())
            }
            
        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid refund request", extra={"error": str(e)})
            metrics.add_metric(name="RefundInvalidRequest", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Invalid refund request: {str(e)}")
            
        except stripe.error.StripeError as e:
            logger.error("Stripe refund error", extra={"error": str(e)})
            metrics.add_metric(name="RefundStripeError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Refund processing error: {str(e)}")
            
        except Exception as e:
            logger.error("Failed to process refund", extra={"error": str(e)})
            metrics.add_metric(name="RefundProcessingError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to process refund: {str(e)}")
    
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
    
    @staticmethod
    @tracer.capture_method
    def _update_order_refund_status(order_id: str, refund_id: str, status: str, amount: int):
        """Update order refund status in DynamoDB"""
        try:
            orders_table = get_orders_table()
            
            orders_table.update_item(
                Key={'orderId': order_id},
                UpdateExpression="SET refundStatus = :status, refundId = :refund_id, refundAmount = :amount, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ':status': status,
                    ':refund_id': refund_id,
                    ':amount': amount,
                    ':updated_at': int(time.time())
                }
            )
            
            logger.info("Order refund status updated", extra={
                "order_id": order_id,
                "refund_id": refund_id,
                "status": status,
                "amount": amount
            })
            
        except ClientError as e:
            logger.error("Failed to update order refund status", extra={
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
        path = event.get('path', '')
        
        # Handle OPTIONS request for CORS
        if http_method == 'OPTIONS':
            return create_success_response({}, 200)
        
        if http_method == 'POST':
            if '/webhook' in path:
                # Handle Stripe webhook with signature verification
                try:
                    raw_body = event.get('body', '{}')
                    body = json.loads(raw_body)
                    
                    # Extract Stripe signature from headers
                    headers = event.get('headers', {})
                    signature = headers.get('Stripe-Signature') or headers.get('stripe-signature')
                    
                    result = PaymentService.handle_webhook(body, signature, raw_body)
                    return create_success_response(result)
                    
                except json.JSONDecodeError:
                    return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
                except BusinessLogicError as e:
                    return create_error_response(400, "WEBHOOK_ERROR", str(e))
                    
            elif '/refund' in path:
                # Handle refund processing
                try:
                    body = json.loads(event.get('body', '{}'))
                    result = PaymentService.process_refund(body)
                    return create_success_response(result, 201)
                    
                except json.JSONDecodeError:
                    return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body")
                except ValidationError as e:
                    return create_error_response(400, "VALIDATION_ERROR", str(e))
                except BusinessLogicError as e:
                    return create_error_response(400, "REFUND_ERROR", str(e))
                    
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
        
        elif http_method == 'GET':
            # Handle payment status queries
            if '/status' in path:
                try:
                    payment_intent_id = event.get('queryStringParameters', {}).get('payment_intent_id')
                    if not payment_intent_id:
                        return create_error_response(400, "MISSING_PARAMETER", "payment_intent_id is required")
                    
                    # Import Stripe here to avoid cold start issues
                    import stripe
                    stripe.api_key = get_stripe_api_key()
                    
                    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                    
                    result = {
                        'paymentIntentId': payment_intent.id,
                        'status': payment_intent.status,
                        'amount': payment_intent.amount,
                        'currency': payment_intent.currency,
                        'requiresAction': payment_intent.status == 'requires_action',
                        'nextAction': payment_intent.next_action if payment_intent.status == 'requires_action' else None
                    }
                    
                    return create_success_response(result)
                    
                except Exception as e:
                    logger.error("Failed to retrieve payment status", extra={"error": str(e)})
                    return create_error_response(500, "PAYMENT_STATUS_ERROR", "Failed to retrieve payment status")
            else:
                return create_error_response(404, "NOT_FOUND", "Endpoint not found")
        
        else:
            return create_error_response(405, "METHOD_NOT_ALLOWED", f"HTTP method {http_method} not allowed")
    
    except Exception as e:
        logger.exception("Unexpected error in payment function")
        metrics.add_metric(name="PaymentUnexpectedError", unit=MetricUnit.Count, value=1)
        
        return create_error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred")