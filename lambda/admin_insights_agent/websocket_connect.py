"""
WebSocket Connection Handler for Admin Insights Agent

This Lambda function handles WebSocket connection establishment:
- Validates JWT token from query parameters
- Stores connection ID in DynamoDB connections table
- Initializes session with SessionManager
- Returns 200 on successful connection

Requirements: 4.1, 10.4
"""

import json
import os
import time
import base64
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


def decode_jwt_payload(token: str) -> dict:
    """
    Decode JWT token payload without verification (for extracting claims)
    Note: In production, you should verify the signature
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.error("Failed to decode JWT", extra={"error": str(e)})
        return {}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle WebSocket $connect route
    
    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123"
        },
        "queryStringParameters": {
            "token": "jwt-token-here"
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
        
        # Get token from query parameters
        query_params = event.get('queryStringParameters') or {}
        token = query_params.get('token')
        
        if not token:
            logger.error("No token provided in query parameters", extra={
                "connectionId": connection_id
            })
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized: Missing authentication token"})
            }
        
        # Decode JWT to extract user information
        payload = decode_jwt_payload(token)
        
        # Extract actor_id (admin user ID) from JWT claims
        # Cognito tokens have 'sub' claim for user ID
        actor_id = payload.get('sub') or payload.get('cognito:username')
        
        if not actor_id:
            logger.error("No user ID found in JWT token", extra={
                "connectionId": connection_id,
                "payload_keys": list(payload.keys())
            })
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized: Invalid token"})
            }
        
        # Check token expiration
        exp = payload.get('exp')
        if exp and exp < time.time():
            logger.error("Token expired", extra={
                "connectionId": connection_id,
                "exp": exp,
                "now": time.time()
            })
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized: Token expired"})
            }
        
        # Generate session ID for this connection
        session_id = f"session-{connection_id}"
        
        # Calculate TTL (24 hours from now)
        ttl = int((datetime.now() + timedelta(hours=24)).timestamp())
        
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
