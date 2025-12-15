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
    Note: In production, integrate with Stripe API
    """
    try:
        body = json.loads(event['body'])

        logger.info("Processing payment request", extra={
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
