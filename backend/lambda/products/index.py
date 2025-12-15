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
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Product CRUD handler
    """
    try:
        http_method = event['httpMethod']
        path_params = event.get('pathParameters', {}) or {}

        logger.info(f"Processing {http_method} request", extra={"path_params": path_params})

        if http_method == 'GET':
            if path_params and 'productId' in path_params:
                return get_product(path_params['productId'])
            else:
                return list_products(event.get('queryStringParameters', {}) or {})
        
        elif http_method == 'POST':
            body = json.loads(event['body'])
            return create_product(body)
        
        elif http_method == 'PUT':
            body = json.loads(event['body'])
            return update_product(path_params['productId'], body)
        
        elif http_method == 'DELETE':
            return delete_product(path_params['productId'])
        
        return error_response(400, "Unsupported method")
    
    except Exception as e:
        logger.exception("Unhandled exception in product handler")
        return error_response(500, "Internal server error")

@tracer.capture_method
def list_products(query_params: Dict) -> Dict:
    """List products with optional category filter"""
    category = query_params.get('category') if query_params else None
    logger.info("Listing products", extra={"category": category})
    
    if category:
        response = products_table.query(
            IndexName='category-index',
            KeyConditionExpression='category = :cat',
            ExpressionAttributeValues={':cat': category}
        )
    else:
        response = products_table.scan(Limit=50)
    
    return success_response(response.get('Items', []))

@tracer.capture_method
def get_product(product_id: str) -> Dict:
    """Get single product"""
    logger.info("Getting product", extra={"product_id": product_id})
    response = products_table.get_item(Key={'productId': product_id})

    if 'Item' not in response:
        logger.warning("Product not found", extra={"product_id": product_id})
        return error_response(404, "Product not found")
    
    return success_response(response['Item'])

@tracer.capture_method
def create_product(data: Dict) -> Dict:
    """Create new product"""
    import uuid

    product_id = str(uuid.uuid4())
    # Avoid using `name` as a key in `extra` because it conflicts with LogRecord.name
    logger.info("Creating product", extra={"product_id": product_id, "product_name": data.get('name')})
    item = {
        'productId': product_id,
        'name': data['name'],
        'description': data.get('description', ''),
        'price': Decimal(str(data['price'])),
        'category': data['category'],
        'stock': data.get('stock', 0),
        'imageUrl': data.get('imageUrl', '')
    }
    
    products_table.put_item(Item=item)
    logger.info("Product created successfully", extra={"product_id": product_id})
    return success_response(item, 201)

@tracer.capture_method
def update_product(product_id: str, data: Dict) -> Dict:
    """Update existing product"""
    logger.info("Updating product", extra={"product_id": product_id})
    try:
        update_expression = "SET "
        expression_attribute_values = {}
        
        for key, value in data.items():
            if key != 'productId':
                update_expression += f"{key} = :{key}, "
                if isinstance(value, (int, float)):
                    expression_attribute_values[f":{key}"] = Decimal(str(value))
                else:
                    expression_attribute_values[f":{key}"] = value
        
        update_expression = update_expression.rstrip(", ")
        
        response = products_table.update_item(
            Key={'productId': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        logger.info("Product updated successfully", extra={"product_id": product_id})
        return success_response(response.get('Attributes', {}))
    except Exception as e:
        logger.exception("Error updating product")
        return error_response(400, str(e))

@tracer.capture_method
def delete_product(product_id: str) -> Dict:
    """Delete product"""
    logger.info("Deleting product", extra={"product_id": product_id})
    products_table.delete_item(Key={'productId': product_id})
    logger.info("Product deleted successfully", extra={"product_id": product_id})
    return success_response({'message': 'Product deleted'})

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
