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

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE', 'e-com67-orders'))

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Orders handler - GET orders for a user
    """
    try:
        http_method = event['httpMethod']
        
        # Get user ID from request context (Cognito authorizer)
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        logger.info("Fetching orders", extra={"user_id": user_id, "method": http_method})
        
        if http_method == 'GET':
            # Query orders by userId using GSI
            response = orders_table.query(
                IndexName='userId-timestamp-index',
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=False  # Sort by timestamp descending (newest first)
            )
            
            orders = response.get('Items', [])
            
            logger.info(f"Found {len(orders)} orders for user", extra={"user_id": user_id})
            
            return success_response(orders)
        
        else:
            return error_response(405, "Method not allowed")
            
    except Exception as e:
        logger.exception("Failed to fetch orders")
        return error_response(500, "Failed to fetch orders")

def success_response(data: Any, status_code: int = 200) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET'
        },
        'body': json.dumps(data, default=decimal_default)
    }

def error_response(status_code: int, message: str) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET'
        },
        'body': json.dumps({'error': message})
    }

def decimal_default(obj):
    """Helper to serialize Decimal objects to float"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
