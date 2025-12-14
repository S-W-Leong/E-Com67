import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])
cart_table = dynamodb.Table(os.environ['CART_TABLE'])
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

def handler(event, context):
    """
    Process orders from SQS queue
    """
    for record in event['Records']:
        try:
            order_data = json.loads(record['body'])
            process_order(order_data)
        except Exception as e:
            print(f"Failed to process order: {str(e)}")
            raise  # Will send to DLQ after retries

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
    
    # 1. Create order
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
    for item in items:
        try:
            cart_table.delete_item(
                Key={'userId': user_id, 'productId': item['productId']}
            )
        except Exception as e:
            print(f"Error clearing cart item: {str(e)}")
    
    # 3. Update stock
    for item in items:
        try:
            products_table.update_item(
                Key={'productId': item['productId']},
                UpdateExpression='SET stock = stock - :qty',
                ExpressionAttributeValues={':qty': int(item.get('quantity', 1))}
            )
        except Exception as e:
            print(f"Error updating stock: {str(e)}")
    
    # 4. Send notification
    if sns_topic_arn:
        try:
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
            print(f"Error sending notification: {str(e)}")
    
    print(f"Order {order_id} processed successfully")
