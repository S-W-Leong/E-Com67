import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

# AWS Lambda Powertools
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger()
tracer = Tracer()

orders_table = boto3.resource('dynamodb').Table(os.environ.get('ORDERS_TABLE', 'e-com67-orders'))

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Payment handler - validate and process payments
    Supports both API Gateway and Step Functions invocations
    Note: In production, integrate with Stripe API
    """
    try:
        # Check if this is a Step Functions invocation (direct payload, no 'body' key with JSON string)
        if 'orderId' in event and 'body' not in event:
            return handle_step_functions_payment(event)
        
        # API Gateway invocation
        body = json.loads(event['body'])

        logger.info("Processing payment request (API Gateway)", extra={
            "order_id": body.get('orderId'),
            "user_id": body.get('userId'),
            "amount": body.get('amount')
        })

        # Validate payment data
        if not all(key in body for key in ['orderId', 'userId', 'amount', 'paymentToken']):
            logger.warning("Missing required payment fields", extra={"body_keys": list(body.keys())})
            return error_response(400, "Missing required payment fields")
        
        # TODO: Process payment with Stripe
        # For now, simulate successful payment

        logger.info("Payment processed successfully", extra={"order_id": body['orderId']})

        return success_response({
            'orderId': body['orderId'],
            'status': 'PAID',
            'message': 'Payment processed successfully'
        })

    except Exception as e:
        logger.exception("Payment processing failed")
        return error_response(500, "Payment processing failed")


@tracer.capture_method
def handle_step_functions_payment(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Step Functions invocation for payment processing.
    Returns direct response (not API Gateway format).
    """
    order_id = event.get('orderId')
    user_id = event.get('userId')
    amount = event.get('amount')
    payment_token = event.get('paymentToken')
    items = event.get('items', [])
    
    logger.info("Processing payment (Step Functions)", extra={
        "order_id": order_id,
        "user_id": user_id,
        "amount": amount
    })
    
    # Validate required fields
    if not all([order_id, user_id, amount, payment_token]):
        missing = [k for k, v in {'orderId': order_id, 'userId': user_id, 'amount': amount, 'paymentToken': payment_token}.items() if not v]
        raise ValueError(f"Missing required payment fields: {missing}")
    
    # TODO: Integrate with Stripe API for real payment processing
    # For now, simulate successful payment
    
    # In production, you would:
    # 1. Create a PaymentIntent with Stripe
    # 2. Confirm the payment using the payment_token
    # 3. Handle success/failure scenarios
    
    logger.info("Payment processed successfully (mock)", extra={"order_id": order_id})
    
    # Return data for next step in workflow
    return {
        'orderId': order_id,
        'userId': user_id,
        'items': items,
        'amount': amount,
        'paymentToken': payment_token,
        'paymentStatus': 'PAID',
        'transactionId': f"txn_{order_id[:8]}",
        'message': 'Payment processed successfully'
    }

def success_response(data: Any, status_code: int = 200) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,POST,DELETE'
        },
        'body': json.dumps(data, default=str)
    }

def error_response(status_code: int, message: str) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,POST,DELETE'
        },
        'body': json.dumps({'error': message})
    }
