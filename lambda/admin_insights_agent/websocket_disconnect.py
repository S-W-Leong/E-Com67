"""
WebSocket Disconnect Handler for Admin Insights Agent

This Lambda function handles WebSocket disconnection:
- Retrieves session ID from connection ID
- Calls SessionManager.terminate_session()
- Removes connection ID from DynamoDB

Requirements: 4.5, 10.4
"""

import json
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.exceptions import ClientError
from session_manager import SessionManager

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-southeast-1'))
connections_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE_NAME'])

# Initialize session manager
session_manager = SessionManager(
    memory_id=os.environ['MEMORY_ID'],
    region=os.environ.get('REGION', 'ap-southeast-1')
)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle WebSocket $disconnect route
    
    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123"
        }
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": "Disconnected"
    }
    """
    try:
        # Extract connection ID
        connection_id = event['requestContext']['connectionId']
        
        logger.info("Processing WebSocket disconnection", extra={
            "connectionId": connection_id
        })
        
        # Retrieve connection information from DynamoDB
        try:
            response = connections_table.get_item(
                Key={'connectionId': connection_id}
            )
            
            if 'Item' not in response:
                logger.warning("Connection not found in table", extra={
                    "connectionId": connection_id
                })
                # Still return 200 - connection is already gone
                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": "Disconnected"})
                }
            
            connection_item = response['Item']
            session_id = connection_item.get('sessionId')
            actor_id = connection_item.get('actorId')
            
            # Terminate session memory if session exists
            if session_id and actor_id:
                try:
                    session_manager.terminate_session(actor_id, session_id)
                    logger.info("Session terminated", extra={
                        "sessionId": session_id,
                        "actorId": actor_id
                    })
                except Exception as e:
                    # Log error but don't fail - we still want to clean up the connection
                    logger.error("Error terminating session", extra={
                        "sessionId": session_id,
                        "actorId": actor_id,
                        "error": str(e)
                    })
            
        except ClientError as e:
            logger.error("Error retrieving connection from DynamoDB", extra={
                "connectionId": connection_id,
                "error": str(e),
                "errorCode": e.response['Error']['Code']
            })
            # Continue to delete connection even if retrieval failed
        
        # Remove connection from DynamoDB
        try:
            connections_table.delete_item(
                Key={'connectionId': connection_id}
            )
            logger.info("Connection removed from table", extra={
                "connectionId": connection_id
            })
        except ClientError as e:
            logger.error("Error deleting connection from DynamoDB", extra={
                "connectionId": connection_id,
                "error": str(e),
                "errorCode": e.response['Error']['Code']
            })
            # Don't fail - connection is being closed anyway
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Disconnected"})
        }
        
    except KeyError as e:
        logger.error("Missing required field in event", extra={
            "error": str(e),
            "event": event
        })
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Bad Request: Missing field {str(e)}"})
        }
        
    except Exception as e:
        logger.exception("Unexpected error in disconnect handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
