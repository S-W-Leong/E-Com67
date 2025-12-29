"""
WebSocket Connection Handler for Admin Insights Agent

This Lambda function handles WebSocket connection establishment:
- Stores connection ID in DynamoDB connections table
- Initializes session with SessionManager
- Returns 200 on successful connection

Requirements: 4.1, 10.4
"""

import json
import os
import time
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.exceptions import ClientError

logger = Logger()
tracer = Tracer()

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-southeast-1'))
connections_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE_NAME'])


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle WebSocket $connect route
    
    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123",
            "authorizer": {
                "sub": "user-id-from-jwt",
                "email": "user@example.com"
            }
        }
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": "Connected"
    }
    """
    try:
        # Extract connection information
        connection_id = event['requestContext']['connectionId']
        
        # Extract actor_id (admin user ID) from JWT claims
        # The authorizer adds claims to requestContext.authorizer
        authorizer = event['requestContext'].get('authorizer', {})
        actor_id = authorizer.get('sub') or authorizer.get('principalId')
        
        if not actor_id:
            logger.error("No actor_id found in authorizer context", extra={
                "connectionId": connection_id,
                "authorizer": authorizer
            })
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized: Missing user identity"})
            }
        
        # Generate session ID for this connection
        session_id = f"session-{connection_id}"
        
        # Calculate TTL (24 hours from now)
        ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        
        # Store connection in DynamoDB
        connections_table.put_item(
            Item={
                'connectionId': connection_id,
                'sessionId': session_id,
                'actorId': actor_id,
                'connectedAt': int(time.time()),
                'ttl': ttl
            }
        )
        
        logger.info("WebSocket connection established", extra={
            "connectionId": connection_id,
            "sessionId": session_id,
            "actorId": actor_id
        })
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Connected",
                "sessionId": session_id
            })
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
        
    except ClientError as e:
        logger.error("DynamoDB error storing connection", extra={
            "error": str(e),
            "errorCode": e.response['Error']['Code']
        })
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
        
    except Exception as e:
        logger.exception("Unexpected error in connection handler")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
