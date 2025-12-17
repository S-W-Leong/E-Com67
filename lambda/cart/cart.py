"""
Cart Lambda Function

Handles shopping cart operations including add, update, remove, and get.
"""

import json
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

dynamodb = boto3.resource('dynamodb')


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for cart operations"""
    
    logger.info("Cart function invoked", extra={"event": event})
    
    try:
        # Basic response for now - will be implemented in later tasks
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Cart function ready",
                "function": "cart"
            })
        }
        
        metrics.add_metric(name="CartInvocation", unit=MetricUnit.Count, value=1)
        
        return response
        
    except Exception as e:
        logger.exception("Error in cart function")
        metrics.add_metric(name="CartError", unit=MetricUnit.Count, value=1)
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }