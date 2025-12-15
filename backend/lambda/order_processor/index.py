import json
import os
import boto3
from decimal import Decimal

# AWS Lambda Powertools
from aws_lambda_powertools import Logger, Tracer  # type: ignore
from aws_lambda_powertools.utilities.typing import LambdaContext  # type: ignore

# Initialize Powertools
logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])
cart_table = dynamodb.Table(os.environ['CART_TABLE'])
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event, context: LambdaContext):
    """
    Process orders from SQS queue
    """
    logger.info(f"Processing {len(event['Records'])} order(s) from SQS queue")

    for record in event['Records']:
        try:
            order_data = json.loads(record['body'])
            logger.info("Processing order", extra={"order_id": order_data.get('orderId')})
            process_order(order_data)
        except Exception as e:
            logger.exception("Failed to process order", extra={"order_id": order_data.get('orderId')})
            raise  # Will send to DLQ after retries

@tracer.capture_method
def process_order(order_data):
    """
    1. Create order in DynamoDB
    2. Clear user's cart
    3. Update product stock
    4. Send notification
    """
    user_id = order_data['userId']
    order_id = order_data['orderId']
    items = order_data['items']

    logger.info("Processing order", extra={
        "order_id": order_id,
        "user_id": user_id,
        "item_count": len(items)
    })
    
    # 1. Create order
    logger.info("Creating order in DynamoDB", extra={"order_id": order_id})
    orders_table.put_item(Item={
        'orderId': order_id,
        'userId': user_id,
        'items': items,
        'totalAmount': Decimal(str(order_data['totalAmount'])),
        'status': 'PROCESSING',
        'paymentId': order_data.get('paymentId'),
        'timestamp': order_data['timestamp']
    })
    
    # 2. Clear cart
    logger.info("Clearing cart items", extra={"user_id": user_id})
    for item in items:
        try:
            cart_table.delete_item(
                Key={'userId': user_id, 'productId': item['productId']}
            )
        except Exception as e:
            logger.exception("Error clearing cart item", extra={"product_id": item.get('productId')})
    
    # 3. Update stock
    logger.info("Updating product stock")
    for item in items:
        try:
            products_table.update_item(
                Key={'productId': item['productId']},
                UpdateExpression='SET stock = stock - :qty',
                ExpressionAttributeValues={':qty': int(item.get('quantity', 1))}
            )
        except Exception as e:
            logger.exception("Error updating stock", extra={"product_id": item.get('productId')})
    
    # 4. Send notification
    if sns_topic_arn:
        try:
            logger.info("Sending order confirmation notification", extra={"order_id": order_id})
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject='Order Confirmation',
                Message=json.dumps({
                    'orderId': order_id,
                    'userId': user_id,
                    'email': order_data.get('email'),
                    'totalAmount': float(order_data['totalAmount'])
                }, default=str)
            )
        except Exception as e:
            logger.exception("Error sending notification", extra={"order_id": order_id})

    logger.info("Order processed successfully", extra={"order_id": order_id})
