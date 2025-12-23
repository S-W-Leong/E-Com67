"""
Product CRUD Lambda Function

Handles Create, Read, Update, Delete operations for products.
Implements category-based filtering using DynamoDB GSI.
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
from utils.validators import validate_product_data, ValidationError
from utils.exceptions import BusinessLogicError
from utils.formatters import format_timestamp


def convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
products_table = None

def get_products_table():
    """Get products table, initializing if needed"""
    global products_table
    if products_table is None:
        table_name = os.environ.get('PRODUCTS_TABLE_NAME')
        if not table_name:
            raise BusinessLogicError("PRODUCTS_TABLE_NAME environment variable not set")
        products_table = dynamodb.Table(table_name)
    return products_table


class ProductService:
    """Service class for product operations"""
    
    @staticmethod
    @tracer.capture_method
    def create_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        logger.info("Creating new product", extra={"product_data": product_data})
        
        # Validate product data
        validated_data = validate_product_data(product_data)
        
        # Generate unique product ID
        product_id = str(uuid.uuid4())
        current_time = int(time.time())
        
        # Prepare product item
        product_item = {
            'productId': product_id,
            'name': validated_data['name'],
            'description': validated_data['description'],
            'price': Decimal(str(validated_data['price'])),
            'category': validated_data['category'],
            'stock': validated_data.get('stock', 0),
            'imageUrl': validated_data.get('imageUrl', ''),
            'tags': validated_data.get('tags', []),
            'isActive': validated_data.get('isActive', True),
            'createdAt': current_time,
            'updatedAt': current_time
        }
        
        try:
            # Store in DynamoDB
            get_products_table().put_item(Item=product_item)
            
            logger.info("Product created successfully", extra={"product_id": product_id})
            metrics.add_metric(name="ProductCreated", unit=MetricUnit.Count, value=1)
            
            # Convert Decimal back to float for JSON serialization
            product_item['price'] = float(product_item['price'])
            return product_item
            
        except ClientError as e:
            logger.error("Failed to create product", extra={"error": str(e)})
            metrics.add_metric(name="ProductCreateError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to create product: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def get_product(product_id: str) -> Optional[Dict[str, Any]]:
        """Get a single product by ID"""
        logger.info("Retrieving product", extra={"product_id": product_id})
        
        try:
            response = get_products_table().get_item(Key={'productId': product_id})
            
            if 'Item' not in response:
                logger.info("Product not found", extra={"product_id": product_id})
                return None
            
            product = response['Item']
            # Convert all Decimal objects to float for JSON serialization
            product = convert_decimals_to_float(product)
            
            metrics.add_metric(name="ProductRetrieved", unit=MetricUnit.Count, value=1)
            return product
            
        except ClientError as e:
            logger.error("Failed to retrieve product", extra={"product_id": product_id, "error": str(e)})
            metrics.add_metric(name="ProductRetrieveError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to retrieve product: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def list_products(category: Optional[str] = None, limit: int = 50, last_key: Optional[str] = None) -> Dict[str, Any]:
        """List products with optional category filtering and pagination"""
        logger.info("Listing products", extra={"category": category, "limit": limit})
        
        try:
            if category:
                # Use GSI for category-based filtering
                query_kwargs = {
                    'IndexName': 'category-index',
                    'KeyConditionExpression': Key('category').eq(category),
                    'FilterExpression': Attr('isActive').eq(True),
                    'Limit': limit
                }
                
                # Add pagination if last_key provided
                if last_key:
                    query_kwargs['ExclusiveStartKey'] = {'category': category, 'productId': last_key}
                
                response = get_products_table().query(**query_kwargs)
            else:
                # Scan all products
                scan_kwargs = {
                    'FilterExpression': Attr('isActive').eq(True),
                    'Limit': limit
                }
                
                # Add pagination if last_key provided
                if last_key:
                    scan_kwargs['ExclusiveStartKey'] = {'productId': last_key}
                
                response = get_products_table().scan(**scan_kwargs)
            
            products = response.get('Items', [])
            
            # Convert all Decimal objects to float for JSON serialization
            products = [convert_decimals_to_float(product) for product in products]
            
            result = {
                'products': products,
                'count': len(products)
            }
            
            # Add pagination info if available
            if 'LastEvaluatedKey' in response:
                result['lastKey'] = response['LastEvaluatedKey']['productId']
            
            logger.info("Products listed successfully", extra={"count": len(products), "category": category})
            metrics.add_metric(name="ProductsListed", unit=MetricUnit.Count, value=len(products))
            
            return result
            
        except ClientError as e:
            logger.error("Failed to list products", extra={"category": category, "error": str(e)})
            metrics.add_metric(name="ProductListError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to list products: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def update_product(product_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing product"""
        logger.info("Updating product", extra={"product_id": product_id, "update_data": update_data})
        
        # Validate update data
        validated_data = validate_product_data(update_data)
        current_time = int(time.time())
        
        # Build update expression
        update_expression = "SET updatedAt = :updated_at"
        expression_values = {':updated_at': current_time}
        expression_names = {}
        
        for key, value in validated_data.items():
            if key == 'price':
                value = Decimal(str(value))
            
            attr_name = f"#{key}"
            attr_value = f":{key}"
            
            update_expression += f", {attr_name} = {attr_value}"
            expression_names[attr_name] = key
            expression_values[attr_value] = value
        
        try:
            response = get_products_table().update_item(
                Key={'productId': product_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression=Attr('productId').exists(),
                ReturnValues='ALL_NEW'
            )
            
            updated_product = response['Attributes']
            # Convert all Decimal objects to float for JSON serialization
            updated_product = convert_decimals_to_float(updated_product)
            
            logger.info("Product updated successfully", extra={"product_id": product_id})
            metrics.add_metric(name="ProductUpdated", unit=MetricUnit.Count, value=1)
            
            return updated_product
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Product not found for update", extra={"product_id": product_id})
                return None
            
            logger.error("Failed to update product", extra={"product_id": product_id, "error": str(e)})
            metrics.add_metric(name="ProductUpdateError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to update product: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def delete_product(product_id: str) -> bool:
        """Delete a product (soft delete by setting isActive to False)"""
        logger.info("Deleting product", extra={"product_id": product_id})
        
        try:
            response = get_products_table().update_item(
                Key={'productId': product_id},
                UpdateExpression="SET isActive = :inactive, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ':inactive': False,
                    ':updated_at': int(time.time())
                },
                ConditionExpression=Attr('productId').exists(),
                ReturnValues='ALL_NEW'
            )
            
            logger.info("Product deleted successfully", extra={"product_id": product_id})
            metrics.add_metric(name="ProductDeleted", unit=MetricUnit.Count, value=1)
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.info("Product not found for deletion", extra={"product_id": product_id})
                return False
            
            logger.error("Failed to delete product", extra={"product_id": product_id, "error": str(e)})
            metrics.add_metric(name="ProductDeleteError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to delete product: {str(e)}")


def get_cors_headers(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Get CORS headers for the response.
    Returns wildcard origin for development (no credentials support).
    """
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token"
    }


def create_error_response(status_code: int, error_code: str, message: str, details: Optional[Dict] = None, event: Optional[Dict] = None) -> Dict[str, Any]:
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
        "headers": get_cors_headers(event or {}),
        "body": json.dumps(error_response)
    }


def create_success_response(data: Any, status_code: int = 200, event: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "statusCode": status_code,
        "headers": get_cors_headers(event or {}),
        "body": json.dumps(data)
    }


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for product CRUD operations"""

    logger.info("Product CRUD function invoked", extra={"event": event})

    try:
        http_method = event.get('httpMethod', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}

        # Handle OPTIONS request for CORS
        if http_method == 'OPTIONS':
            return create_success_response({}, 200, event)

        # Route based on HTTP method and path
        if http_method == 'POST':
            # Create product
            try:
                body = json.loads(event.get('body', '{}'))
                product = ProductService.create_product(body)
                return create_success_response(product, 201, event)
            except json.JSONDecodeError:
                return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body", event=event)
            except ValidationError as e:
                return create_error_response(400, "VALIDATION_ERROR", str(e), event=event)
            except BusinessLogicError as e:
                return create_error_response(500, "BUSINESS_LOGIC_ERROR", str(e), event=event)

        elif http_method == 'GET':
            product_id = path_parameters.get('id')

            if product_id:
                # Get single product
                product = ProductService.get_product(product_id)
                if product:
                    return create_success_response(product, 200, event)
                else:
                    return create_error_response(404, "PRODUCT_NOT_FOUND", "Product not found", event=event)
            else:
                # List products with optional filtering
                category = query_parameters.get('category')
                limit = int(query_parameters.get('limit', 50))
                last_key = query_parameters.get('lastKey')

                result = ProductService.list_products(category, limit, last_key)
                logger.info("Products listed successfully", extra={"result": result})
                return create_success_response(result, 200, event)

        elif http_method == 'PUT':
            # Update product
            product_id = path_parameters.get('id')
            if not product_id:
                return create_error_response(400, "MISSING_PRODUCT_ID", "Product ID is required", event=event)

            try:
                body = json.loads(event.get('body', '{}'))
                updated_product = ProductService.update_product(product_id, body)
                if updated_product:
                    return create_success_response(updated_product, 200, event)
                else:
                    return create_error_response(404, "PRODUCT_NOT_FOUND", "Product not found", event=event)
            except json.JSONDecodeError:
                return create_error_response(400, "INVALID_JSON", "Invalid JSON in request body", event=event)
            except ValidationError as e:
                return create_error_response(400, "VALIDATION_ERROR", str(e), event=event)
            except BusinessLogicError as e:
                return create_error_response(500, "BUSINESS_LOGIC_ERROR", str(e), event=event)

        elif http_method == 'DELETE':
            # Delete product
            product_id = path_parameters.get('id')
            if not product_id:
                return create_error_response(400, "MISSING_PRODUCT_ID", "Product ID is required", event=event)

            success = ProductService.delete_product(product_id)
            if success:
                return create_success_response({"message": "Product deleted successfully"}, 200, event)
            else:
                return create_error_response(404, "PRODUCT_NOT_FOUND", "Product not found", event=event)

        else:
            return create_error_response(405, "METHOD_NOT_ALLOWED", f"HTTP method {http_method} not allowed", event=event)

    except Exception as e:
        logger.exception("Unexpected error in product CRUD function")
        metrics.add_metric(name="ProductCrudUnexpectedError", unit=MetricUnit.Count, value=1)

        return create_error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred", event=event)