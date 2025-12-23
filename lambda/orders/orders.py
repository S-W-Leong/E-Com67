"""
Orders Lambda Function

Handles order retrieval and management operations including:
- User order history queries with pagination
- Order status tracking and updates
- Order detail retrieval with complete information
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError

# Import utilities from layer
from utils.validators import ValidationError
from utils.exceptions import BusinessLogicError
from utils.formatters import format_timestamp

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="E-Com67")
app = APIGatewayRestResolver()

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')

def get_orders_table():
    """Get orders table with lazy initialization"""
    return dynamodb.Table(os.environ['ORDERS_TABLE_NAME'])


class OrdersService:
    """Service class for order retrieval and management operations"""
    
    @staticmethod
    @tracer.capture_method
    def get_user_orders(user_id: str, limit: int = 20, last_evaluated_key: Optional[str] = None) -> Dict[str, Any]:
        """Get user order history with pagination using userId-timestamp GSI"""
        logger.info("Getting user orders", extra={"user_id": user_id, "limit": limit})
        
        try:
            orders_table = get_orders_table()
            
            # Query parameters for GSI
            query_params = {
                'IndexName': 'userId-timestamp-index',
                'KeyConditionExpression': Key('userId').eq(user_id),
                'ScanIndexForward': False,  # Sort by timestamp descending (newest first)
                'Limit': limit
            }
            
            # Add pagination token if provided
            if last_evaluated_key:
                try:
                    # Decode the pagination token
                    import base64
                    decoded_key = json.loads(base64.b64decode(last_evaluated_key).decode('utf-8'))
                    query_params['ExclusiveStartKey'] = decoded_key
                except Exception as e:
                    logger.warning("Invalid pagination token", extra={"token": last_evaluated_key, "error": str(e)})
                    raise BadRequestError("Invalid pagination token")
            
            # Execute query
            response = orders_table.query(**query_params)
            
            orders = response.get('Items', [])
            
            # Convert Decimal objects to float for JSON serialization
            orders = OrdersService._convert_decimals_to_float(orders)
            
            # Format timestamps for better readability
            for order in orders:
                order['createdAtFormatted'] = format_timestamp(order['createdAt'])
                order['updatedAtFormatted'] = format_timestamp(order['updatedAt'])
            
            # Create pagination token for next page
            next_token = None
            if 'LastEvaluatedKey' in response:
                import base64
                next_token = base64.b64encode(
                    json.dumps(response['LastEvaluatedKey'], default=str).encode('utf-8')
                ).decode('utf-8')
            
            logger.info("User orders retrieved", extra={
                "user_id": user_id,
                "orders_count": len(orders),
                "has_more": next_token is not None
            })
            metrics.add_metric(name="OrdersRetrieved", unit=MetricUnit.Count, value=len(orders))
            
            return {
                'orders': orders,
                'nextToken': next_token,
                'hasMore': next_token is not None,
                'totalReturned': len(orders)
            }
            
        except ClientError as e:
            logger.error("Failed to retrieve user orders", extra={"user_id": user_id, "error": str(e)})
            metrics.add_metric(name="OrderRetrievalError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to retrieve orders: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def get_order_details(order_id: str, user_id: str) -> Dict[str, Any]:
        """Get complete order details for a specific order"""
        logger.info("Getting order details", extra={"order_id": order_id, "user_id": user_id})
        
        try:
            orders_table = get_orders_table()
            
            # Get order by orderId
            response = orders_table.get_item(
                Key={'orderId': order_id}
            )
            
            if 'Item' not in response:
                logger.warning("Order not found", extra={"order_id": order_id})
                raise NotFoundError("Order not found")
            
            order = response['Item']
            
            # Verify the order belongs to the requesting user
            if order['userId'] != user_id:
                logger.warning("Unauthorized order access attempt", extra={
                    "order_id": order_id,
                    "requesting_user": user_id,
                    "order_owner": order['userId']
                })
                raise NotFoundError("Order not found")
            
            # Convert Decimal objects to float for JSON serialization
            order = OrdersService._convert_decimals_to_float([order])[0]
            
            # Format timestamps
            order['createdAtFormatted'] = format_timestamp(order['createdAt'])
            order['updatedAtFormatted'] = format_timestamp(order['updatedAt'])
            
            # Add order status history if available
            order['statusHistory'] = OrdersService._get_order_status_history(order_id)
            
            logger.info("Order details retrieved", extra={"order_id": order_id, "user_id": user_id})
            metrics.add_metric(name="OrderDetailsRetrieved", unit=MetricUnit.Count, value=1)
            
            return order
            
        except NotFoundError:
            raise
        except ClientError as e:
            logger.error("Failed to retrieve order details", extra={
                "order_id": order_id,
                "user_id": user_id,
                "error": str(e)
            })
            metrics.add_metric(name="OrderDetailsRetrievalError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to retrieve order details: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def update_order_status(order_id: str, new_status: str, user_id: Optional[str] = None, admin_update: bool = False) -> Dict[str, Any]:
        """Update order status with proper authorization"""
        logger.info("Updating order status", extra={
            "order_id": order_id,
            "new_status": new_status,
            "admin_update": admin_update
        })
        
        # Validate status
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled', 'failed']
        if new_status not in valid_statuses:
            raise BadRequestError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        try:
            orders_table = get_orders_table()
            
            # Get current order to verify ownership (if not admin)
            if not admin_update and user_id:
                current_order = orders_table.get_item(Key={'orderId': order_id})
                if 'Item' not in current_order:
                    raise NotFoundError("Order not found")
                
                if current_order['Item']['userId'] != user_id:
                    raise NotFoundError("Order not found")
            
            current_time = int(time.time())
            
            # Update order status
            response = orders_table.update_item(
                Key={'orderId': order_id},
                UpdateExpression="SET #status = :new_status, updatedAt = :updated_at",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':new_status': new_status,
                    ':updated_at': current_time
                },
                ReturnValues='ALL_NEW'
            )
            
            updated_order = response['Attributes']
            
            # Convert Decimal objects to float
            updated_order = OrdersService._convert_decimals_to_float([updated_order])[0]
            
            # Format timestamps
            updated_order['createdAtFormatted'] = format_timestamp(updated_order['createdAt'])
            updated_order['updatedAtFormatted'] = format_timestamp(updated_order['updatedAt'])
            
            logger.info("Order status updated", extra={
                "order_id": order_id,
                "new_status": new_status,
                "updated_at": current_time
            })
            metrics.add_metric(name="OrderStatusUpdated", unit=MetricUnit.Count, value=1)
            
            return updated_order
            
        except NotFoundError:
            raise
        except ClientError as e:
            logger.error("Failed to update order status", extra={
                "order_id": order_id,
                "new_status": new_status,
                "error": str(e)
            })
            metrics.add_metric(name="OrderStatusUpdateError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to update order status: {str(e)}")
    
    @staticmethod
    @tracer.capture_method
    def search_orders(user_id: str, status_filter: Optional[str] = None, 
                     date_from: Optional[int] = None, date_to: Optional[int] = None,
                     limit: int = 20, last_evaluated_key: Optional[str] = None) -> Dict[str, Any]:
        """Search and filter user orders with various criteria"""
        logger.info("Searching orders", extra={
            "user_id": user_id,
            "status_filter": status_filter,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit
        })
        
        try:
            orders_table = get_orders_table()
            
            # Build filter expression
            filter_expressions = []
            expression_values = {}
            
            if status_filter:
                filter_expressions.append("#status = :status")
                expression_values[':status'] = status_filter
            
            if date_from:
                filter_expressions.append("#timestamp >= :date_from")
                expression_values[':date_from'] = date_from
            
            if date_to:
                filter_expressions.append("#timestamp <= :date_to")
                expression_values[':date_to'] = date_to
            
            # Query parameters
            query_params = {
                'IndexName': 'userId-timestamp-index',
                'KeyConditionExpression': Key('userId').eq(user_id),
                'ScanIndexForward': False,  # Sort by timestamp descending
                'Limit': limit
            }
            
            # Add filter expression if any filters are applied
            if filter_expressions:
                query_params['FilterExpression'] = ' AND '.join(filter_expressions)
                query_params['ExpressionAttributeNames'] = {'#status': 'status', '#timestamp': 'timestamp'}
                query_params['ExpressionAttributeValues'] = expression_values
            
            # Add pagination token if provided
            if last_evaluated_key:
                try:
                    import base64
                    decoded_key = json.loads(base64.b64decode(last_evaluated_key).decode('utf-8'))
                    query_params['ExclusiveStartKey'] = decoded_key
                except Exception as e:
                    logger.warning("Invalid pagination token", extra={"token": last_evaluated_key, "error": str(e)})
                    raise BadRequestError("Invalid pagination token")
            
            # Execute query
            response = orders_table.query(**query_params)
            
            orders = response.get('Items', [])
            
            # Convert Decimal objects to float
            orders = OrdersService._convert_decimals_to_float(orders)
            
            # Format timestamps
            for order in orders:
                order['createdAtFormatted'] = format_timestamp(order['createdAt'])
                order['updatedAtFormatted'] = format_timestamp(order['updatedAt'])
            
            # Create pagination token for next page
            next_token = None
            if 'LastEvaluatedKey' in response:
                import base64
                next_token = base64.b64encode(
                    json.dumps(response['LastEvaluatedKey'], default=str).encode('utf-8')
                ).decode('utf-8')
            
            logger.info("Orders search completed", extra={
                "user_id": user_id,
                "orders_found": len(orders),
                "has_more": next_token is not None
            })
            metrics.add_metric(name="OrdersSearched", unit=MetricUnit.Count, value=len(orders))
            
            return {
                'orders': orders,
                'nextToken': next_token,
                'hasMore': next_token is not None,
                'totalReturned': len(orders),
                'filters': {
                    'status': status_filter,
                    'dateFrom': date_from,
                    'dateTo': date_to
                }
            }
            
        except BadRequestError:
            raise
        except ClientError as e:
            logger.error("Failed to search orders", extra={
                "user_id": user_id,
                "error": str(e)
            })
            metrics.add_metric(name="OrderSearchError", unit=MetricUnit.Count, value=1)
            raise BusinessLogicError(f"Failed to search orders: {str(e)}")
    
    @staticmethod
    def _convert_decimals_to_float(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert DynamoDB Decimal objects to float for JSON serialization"""
        def convert_item(item):
            if isinstance(item, dict):
                return {k: convert_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [convert_item(i) for i in item]
            elif isinstance(item, Decimal):
                return float(item)
            else:
                return item
        
        return [convert_item(item) for item in items]
    
    @staticmethod
    def _get_order_status_history(order_id: str) -> List[Dict[str, Any]]:
        """Get order status change history (placeholder for future implementation)"""
        # This would typically query a separate status history table
        # For now, return empty list as this is a future enhancement
        return []


# API Gateway event handlers
@app.get("/orders")
@tracer.capture_method
def get_orders():
    """Get user order history with pagination"""
    try:
        # Get user ID from JWT token (would be set by API Gateway authorizer)
        user_id = app.current_event.request_context.authorizer.get('claims', {}).get('sub')
        if not user_id:
            raise BadRequestError("User ID not found in token")
        
        # Get query parameters
        query_params = app.current_event.query_string_parameters or {}
        limit = int(query_params.get('limit', 20))
        next_token = query_params.get('nextToken')
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise BadRequestError("Limit must be between 1 and 100")
        
        result = OrdersService.get_user_orders(user_id, limit, next_token)
        
        return result
        
    except BadRequestError as e:
        logger.warning("Bad request for get orders", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in get orders")
        raise e


@app.get("/orders/<order_id>")
@tracer.capture_method
def get_order_details(order_id: str):
    """Get complete order details"""
    try:
        # Get user ID from JWT token
        user_id = app.current_event.request_context.authorizer.get('claims', {}).get('sub')
        if not user_id:
            raise BadRequestError("User ID not found in token")
        
        result = OrdersService.get_order_details(order_id, user_id)
        
        return result
        
    except NotFoundError as e:
        logger.warning("Order not found", extra={"order_id": order_id, "error": str(e)})
        raise e
    except BadRequestError as e:
        logger.warning("Bad request for get order details", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in get order details")
        raise e


@app.put("/orders/<order_id>/status")
@tracer.capture_method
def update_order_status(order_id: str):
    """Update order status (customer-initiated cancellation only)"""
    try:
        # Get user ID from JWT token
        user_id = app.current_event.request_context.authorizer.get('claims', {}).get('sub')
        if not user_id:
            raise BadRequestError("User ID not found in token")
        
        # Parse request body
        try:
            body = json.loads(app.current_event.body)
        except json.JSONDecodeError:
            raise BadRequestError("Invalid JSON in request body")
        
        new_status = body.get('status')
        if not new_status:
            raise BadRequestError("Status is required")
        
        # Only allow customers to cancel their own orders
        if new_status != 'cancelled':
            raise BadRequestError("Customers can only cancel orders")
        
        result = OrdersService.update_order_status(order_id, new_status, user_id, admin_update=False)
        
        return result
        
    except NotFoundError as e:
        logger.warning("Order not found for status update", extra={"order_id": order_id, "error": str(e)})
        raise e
    except BadRequestError as e:
        logger.warning("Bad request for update order status", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in update order status")
        raise e


@app.get("/orders/search")
@tracer.capture_method
def search_orders():
    """Search and filter user orders"""
    try:
        # Get user ID from JWT token
        user_id = app.current_event.request_context.authorizer.get('claims', {}).get('sub')
        if not user_id:
            raise BadRequestError("User ID not found in token")

        # Get query parameters
        query_params = app.current_event.query_string_parameters or {}
        status_filter = query_params.get('status')
        date_from = query_params.get('dateFrom')
        date_to = query_params.get('dateTo')
        limit = int(query_params.get('limit', 20))
        next_token = query_params.get('nextToken')

        # Convert date strings to timestamps if provided
        date_from_ts = int(date_from) if date_from else None
        date_to_ts = int(date_to) if date_to else None

        # Validate limit
        if limit < 1 or limit > 100:
            raise BadRequestError("Limit must be between 1 and 100")

        result = OrdersService.search_orders(
            user_id, status_filter, date_from_ts, date_to_ts, limit, next_token
        )

        return result

    except BadRequestError as e:
        logger.warning("Bad request for search orders", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in search orders")
        raise e


# Admin API endpoints
@app.get("/admin/orders")
@tracer.capture_method
def get_admin_orders():
    """Get all orders for admin view with pagination"""
    try:
        # Get query parameters
        query_params = app.current_event.query_string_parameters or {}
        limit = int(query_params.get('limit', 20))
        next_token = query_params.get('nextToken')
        status_filter = query_params.get('status')

        # Validate limit
        if limit < 1 or limit > 100:
            raise BadRequestError("Limit must be between 1 and 100")

        orders_table = get_orders_table()

        # Build scan parameters for admin view (scans all orders)
        scan_params = {
            'Limit': limit
        }

        # Add status filter if provided
        if status_filter:
            scan_params['FilterExpression'] = Attr('status').eq(status_filter)

        # Add pagination token if provided
        if next_token:
            try:
                import base64
                decoded_key = json.loads(base64.b64decode(next_token).decode('utf-8'))
                scan_params['ExclusiveStartKey'] = decoded_key
            except Exception as e:
                logger.warning("Invalid pagination token", extra={"token": next_token, "error": str(e)})
                raise BadRequestError("Invalid pagination token")

        # Execute scan
        response = orders_table.scan(**scan_params)

        orders = response.get('Items', [])

        # Convert Decimal objects to float
        orders = OrdersService._convert_decimals_to_float(orders)

        # Format timestamps
        for order in orders:
            order['createdAtFormatted'] = format_timestamp(order['createdAt'])
            order['updatedAtFormatted'] = format_timestamp(order['updatedAt'])

        # Create pagination token for next page
        next_token_response = None
        if 'LastEvaluatedKey' in response:
            import base64
            next_token_response = base64.b64encode(
                json.dumps(response['LastEvaluatedKey'], default=str).encode('utf-8')
            ).decode('utf-8')

        logger.info("Admin orders retrieved", extra={
            "orders_count": len(orders),
            "has_more": next_token_response is not None
        })
        metrics.add_metric(name="AdminOrdersRetrieved", unit=MetricUnit.Count, value=len(orders))

        return {
            'orders': orders,
            'nextToken': next_token_response,
            'hasMore': next_token_response is not None,
            'totalReturned': len(orders)
        }

    except BadRequestError as e:
        logger.warning("Bad request for admin get orders", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in admin get orders")
        raise e


@app.put("/admin/orders/<order_id>")
@tracer.capture_method
def admin_update_order_status(order_id: str):
    """Update order status (admin only)"""
    try:
        # Parse request body
        try:
            body = json.loads(app.current_event.body)
        except json.JSONDecodeError:
            raise BadRequestError("Invalid JSON in request body")

        new_status = body.get('status')
        if not new_status:
            raise BadRequestError("Status is required")

        # Admin can update to any valid status
        result = OrdersService.update_order_status(order_id, new_status, admin_update=True)

        return result

    except NotFoundError as e:
        logger.warning("Order not found for admin status update", extra={"order_id": order_id, "error": str(e)})
        raise e
    except BadRequestError as e:
        logger.warning("Bad request for admin update order status", extra={"error": str(e)})
        raise e
    except Exception as e:
        logger.exception("Unexpected error in admin update order status")
        raise e


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """Lambda handler for orders management"""
    
    logger.info("Orders function invoked", extra={"event": event})
    
    try:
        response = app.resolve(event, context)
        return response
    except Exception as e:
        logger.exception("Unexpected error in orders function")
        metrics.add_metric(name="OrdersFunctionError", unit=MetricUnit.Count, value=1)
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }