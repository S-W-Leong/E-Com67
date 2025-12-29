"""
Admin Insights Agent Lambda Handler - WebSocket sendMessage Route

This module implements the Lambda handler for the WebSocket sendMessage route.
It processes admin queries through the Bedrock AgentCore agent and streams
responses back via WebSocket.

This handler is ONLY for the sendMessage route. Connection management is handled by:
- websocket_connect.py (handles $connect route)
- websocket_disconnect.py (handles $disconnect route)

Key Features:
- AWS Lambda Powertools integration (logging, tracing, metrics)
- Comprehensive error handling for all error categories
- Exponential backoff retry logic for transient failures
- CloudWatch metrics emission
- WebSocket streaming response support
- Session context retrieval from connections table

Requirements:
- Requirements 1.4: Streaming response generation
- Requirements 9.1: Error logging and handling
- Requirements 9.2: Structured error responses
- Requirements 9.3: CloudWatch metrics and observability
- Requirements 10.4: WebSocket API integration
"""

import os
import json
import time
from typing import Dict, Any, Optional, Generator
from datetime import datetime
from enum import Enum

import boto3
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent

# Import agent core functions
from agent import (
    initialize_agent,
    process_message,
    format_response,
    apply_guardrails,
    GuardrailViolationError
)
from session_manager import SessionManager

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="AdminInsightsAgent")

# Environment variables
MEMORY_ID = os.environ.get('MEMORY_ID', '')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')
CONNECTIONS_TABLE_NAME = os.environ.get('CONNECTIONS_TABLE_NAME', '')

# Initialize DynamoDB for WebSocket connections
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
connections_table = dynamodb.Table(CONNECTIONS_TABLE_NAME) if CONNECTIONS_TABLE_NAME else None

# Initialize API Gateway Management API client (for WebSocket)
# This will be initialized per-request with the correct endpoint
apigw_management_client = None

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_MS = 100
MAX_BACKOFF_MS = 5000
BACKOFF_MULTIPLIER = 2


class ErrorCode(str, Enum):
    """Error codes for structured error responses"""
    # User input errors (4xx)
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    
    # Authentication/Authorization errors (4xx)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Guardrail violations (4xx)
    PII_DETECTED = "PII_DETECTED"
    PROMPT_ATTACK_DETECTED = "PROMPT_ATTACK_DETECTED"
    CONTENT_BLOCKED = "CONTENT_BLOCKED"
    
    # Tool execution errors (5xx)
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    SEARCH_ERROR = "SEARCH_ERROR"
    
    # Agent runtime errors (5xx)
    AGENT_INITIALIZATION_FAILED = "AGENT_INITIALIZATION_FAILED"
    MODEL_INVOCATION_FAILED = "MODEL_INVOCATION_FAILED"
    MEMORY_SERVICE_UNAVAILABLE = "MEMORY_SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Transient errors (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    THROTTLED = "THROTTLED"


class AgentError(Exception):
    """Base exception for agent errors with structured information"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable



def exponential_backoff(
    attempt: int,
    initial_backoff_ms: int = INITIAL_BACKOFF_MS,
    max_backoff_ms: int = MAX_BACKOFF_MS,
    multiplier: float = BACKOFF_MULTIPLIER
) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current retry attempt (0-indexed)
        initial_backoff_ms: Initial backoff in milliseconds
        max_backoff_ms: Maximum backoff in milliseconds
        multiplier: Backoff multiplier
    
    Returns:
        Delay in seconds
    """
    import random
    
    # Calculate exponential backoff
    backoff_ms = min(initial_backoff_ms * (multiplier ** attempt), max_backoff_ms)
    
    # Add jitter (±25%)
    jitter = random.uniform(0.75, 1.25)
    backoff_ms *= jitter
    
    return backoff_ms / 1000.0


def get_apigw_management_client(endpoint_url: str):
    """
    Get or create API Gateway Management API client for WebSocket.
    
    Args:
        endpoint_url: WebSocket API endpoint URL
    
    Returns:
        boto3 client for API Gateway Management API
    """
    return boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url,
        region_name=AWS_REGION
    )


@tracer.capture_method
def send_websocket_message(
    connection_id: str,
    message_type: str,
    content: str,
    endpoint_url: str
) -> bool:
    """
    Send a message to a WebSocket connection.
    
    Message format: {"type": "chunk|complete|error", "content": str}
    
    Args:
        connection_id: WebSocket connection ID
        message_type: Type of message (chunk, complete, error)
        content: Message content
        endpoint_url: WebSocket API endpoint URL
    
    Returns:
        True if message sent successfully, False otherwise
    """
    try:
        client = get_apigw_management_client(endpoint_url)
        
        message = {
            "type": message_type,
            "content": content,
            "timestamp": int(datetime.now().timestamp())
        }
        
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
        
        logger.debug("WebSocket message sent", extra={
            "connectionId": connection_id,
            "messageType": message_type,
            "contentLength": len(content)
        })
        
        return True
        
    except client.exceptions.GoneException:
        # Connection is stale/closed
        logger.warning("WebSocket connection gone", extra={
            "connectionId": connection_id
        })
        
        # Clean up stale connection from DynamoDB
        if connections_table:
            try:
                connections_table.delete_item(Key={'connectionId': connection_id})
                logger.info("Cleaned up stale connection", extra={
                    "connectionId": connection_id
                })
            except Exception as e:
                logger.error("Failed to clean up stale connection", extra={
                    "connectionId": connection_id,
                    "error": str(e)
                })
        
        return False
        
    except Exception as e:
        logger.error("Failed to send WebSocket message", extra={
            "connectionId": connection_id,
            "error": str(e),
            "errorType": type(e).__name__
        })
        return False


@tracer.capture_method
def stream_response_to_websocket(
    connection_id: str,
    response_generator: Generator[str, None, None],
    endpoint_url: str
) -> bool:
    """
    Stream response chunks to WebSocket connection.
    
    Args:
        connection_id: WebSocket connection ID
        response_generator: Generator yielding response chunks
        endpoint_url: WebSocket API endpoint URL
    
    Returns:
        True if streaming completed successfully, False otherwise
    """
    try:
        chunk_count = 0
        
        for chunk in response_generator:
            if not send_websocket_message(
                connection_id=connection_id,
                message_type="chunk",
                content=chunk,
                endpoint_url=endpoint_url
            ):
                # Connection is gone, stop streaming
                logger.warning("Stopped streaming due to connection loss", extra={
                    "connectionId": connection_id,
                    "chunksStreamed": chunk_count
                })
                return False
            
            chunk_count += 1
        
        # Send completion message
        send_websocket_message(
            connection_id=connection_id,
            message_type="complete",
            content="",
            endpoint_url=endpoint_url
        )
        
        logger.info("Response streaming completed", extra={
            "connectionId": connection_id,
            "chunksStreamed": chunk_count
        })
        
        metrics.add_metric(name="ResponseChunksStreamed", unit=MetricUnit.Count, value=chunk_count)
        
        return True
        
    except Exception as e:
        logger.error("Error during response streaming", extra={
            "connectionId": connection_id,
            "error": str(e)
        })
        
        # Try to send error message
        try:
            send_websocket_message(
                connection_id=connection_id,
                message_type="error",
                content="An error occurred while streaming the response",
                endpoint_url=endpoint_url
            )
        except:
            pass
        
        return False


@tracer.capture_method
def validate_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate incoming WebSocket sendMessage request and extract parameters.
    
    This function assumes the connection has already been established and validated
    by the websocket_connect handler. It retrieves session context from the
    connections table.
    
    Args:
        event: Lambda event dictionary from WebSocket API Gateway
    
    Returns:
        Validated request parameters including:
        - message: User message
        - session_id: Session identifier (from connections table)
        - actor_id: Admin user ID (from connections table)
        - connection_id: WebSocket connection ID
    
    Raises:
        AgentError: If validation fails
    """
    try:
        # Extract connection ID from WebSocket event
        request_context = event.get('requestContext', {})
        connection_id = request_context.get('connectionId')
        
        if not connection_id:
            raise AgentError(
                code=ErrorCode.INVALID_INPUT,
                message="Missing connection ID. This handler only processes WebSocket events.",
                status_code=400
            )
        
        # Parse body
        body = event.get('body')
        
        # Log the raw body for debugging
        logger.debug("Raw body from event", extra={
            "body": body,
            "body_type": type(body).__name__,
            "full_event": event
        })
        
        if not body:
            raise AgentError(
                code=ErrorCode.MALFORMED_REQUEST,
                message="Missing request body",
                status_code=400
            )
        
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse body JSON", extra={
                    "body": body,
                    "error": str(e)
                })
                raise AgentError(
                    code=ErrorCode.MALFORMED_REQUEST,
                    message="Invalid JSON in request body",
                    status_code=400,
                    details={"error": str(e)}
                )
        
        # Extract message
        message = body.get('message')
        if not message:
            raise AgentError(
                code=ErrorCode.MISSING_PARAMETER,
                message="Missing required parameter: 'message'",
                status_code=400,
                details={"parameter": "message"}
            )
        
        if not isinstance(message, str) or len(message.strip()) == 0:
            raise AgentError(
                code=ErrorCode.INVALID_INPUT,
                message="Message must be a non-empty string",
                status_code=400,
                details={"message_type": type(message).__name__}
            )
        
        # Retrieve session info from connections table
        if not connections_table:
            raise AgentError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Connections table not configured",
                status_code=500
            )
        
        try:
            response = connections_table.get_item(
                Key={'connectionId': connection_id}
            )
            
            if 'Item' not in response:
                raise AgentError(
                    code=ErrorCode.SESSION_EXPIRED,
                    message="Connection not found. Please reconnect.",
                    status_code=401,
                    details={"connectionId": connection_id}
                )
            
            connection_item = response['Item']
            session_id = connection_item.get('sessionId')
            actor_id = connection_item.get('actorId')
            
            if not session_id or not actor_id:
                raise AgentError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Invalid connection data",
                    status_code=500,
                    details={"connectionId": connection_id}
                )
            
        except ClientError as e:
            logger.error("Failed to retrieve connection info", extra={
                "connectionId": connection_id,
                "error": str(e)
            })
            raise AgentError(
                code=ErrorCode.DATABASE_ERROR,
                message="Failed to retrieve session information",
                status_code=500,
                details={"error": str(e)}
            )
        
        logger.info("Request validated", extra={
            "session_id": session_id,
            "actor_id": actor_id,
            "message_length": len(message),
            "connection_id": connection_id
        })
        
        return {
            "message": message.strip(),
            "session_id": session_id,
            "actor_id": actor_id,
            "connection_id": connection_id
        }
        
    except json.JSONDecodeError as e:
        raise AgentError(
            code=ErrorCode.MALFORMED_REQUEST,
            message="Invalid JSON in request body",
            status_code=400,
            details={"error": str(e)}
        )
    except AgentError:
        raise
    except Exception as e:
        logger.error("Request validation failed", extra={"error": str(e)})
        raise AgentError(
            code=ErrorCode.INVALID_INPUT,
            message="Request validation failed",
            status_code=400,
            details={"error": str(e)}
        )


@tracer.capture_method
def handle_agent_processing(
    message: str,
    session_id: str,
    actor_id: str,
    attempt: int = 0
) -> Dict[str, Any]:
    """
    Handle agent processing with retry logic.
    
    Args:
        message: User message to process
        session_id: Session identifier
        actor_id: Admin user ID
        attempt: Current retry attempt (0-indexed)
    
    Returns:
        Processing result dictionary
    
    Raises:
        AgentError: If processing fails after all retries
    """
    try:
        # Initialize agent
        logger.info("Initializing agent", extra={
            "session_id": session_id,
            "actor_id": actor_id,
            "attempt": attempt
        })
        
        agent_config = initialize_agent(
            session_id=session_id,
            actor_id=actor_id,
            memory_id=MEMORY_ID
        )
        
        # Process message
        logger.info("Processing message", extra={
            "session_id": session_id,
            "attempt": attempt
        })
        
        result = process_message(
            agent_config=agent_config,
            message=message,
            session_id=session_id,
            actor_id=actor_id
        )
        
        # Emit success metrics
        metrics.add_metric(name="AgentInvocationSuccess", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="AgentLatency", unit=MetricUnit.Milliseconds, value=0)  # Would track actual latency
        
        return result
        
    except GuardrailViolationError as e:
        # Guardrail violations (not retryable)
        logger.warning("Guardrail violation detected", extra={
            "session_id": session_id,
            "violations": e.violations,
            "source": e.source
        })
        
        metrics.add_metric(name="GuardrailBlocked", unit=MetricUnit.Count, value=1)
        
        # Determine specific error code based on violation type
        error_code = ErrorCode.CONTENT_BLOCKED
        if any("PII" in v for v in e.violations):
            error_code = ErrorCode.PII_DETECTED
        elif any("attack" in v.lower() for v in e.violations):
            error_code = ErrorCode.PROMPT_ATTACK_DETECTED
        
        raise AgentError(
            code=error_code,
            message=str(e),
            status_code=400,
            details={"violations": e.violations, "source": e.source},
            retryable=False
        )
        
    except ValueError as e:
        # Other validation errors (not retryable)
        raise AgentError(
            code=ErrorCode.INVALID_INPUT,
            message=str(e),
            status_code=400,
            retryable=False
        )
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        # Determine if error is retryable
        retryable_codes = [
            'ThrottlingException',
            'TooManyRequestsException',
            'ServiceUnavailable',
            'InternalServerError',
            'RequestTimeout'
        ]
        
        is_retryable = error_code in retryable_codes
        
        if error_code == 'ThrottlingException':
            metrics.add_metric(name="ThrottlingErrors", unit=MetricUnit.Count, value=1)
            agent_error = AgentError(
                code=ErrorCode.THROTTLED,
                message="Service is currently throttled. Please try again.",
                status_code=503,
                details={"aws_error_code": error_code},
                retryable=True
            )
        elif error_code in ['ServiceUnavailable', 'InternalServerError']:
            metrics.add_metric(name="ServiceErrors", unit=MetricUnit.Count, value=1)
            agent_error = AgentError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Service temporarily unavailable. Please try again.",
                status_code=503,
                details={"aws_error_code": error_code},
                retryable=True
            )
        else:
            metrics.add_metric(name="AgentErrors", unit=MetricUnit.Count, value=1)
            agent_error = AgentError(
                code=ErrorCode.MODEL_INVOCATION_FAILED,
                message=f"Agent processing failed: {error_message}",
                status_code=500,
                details={"aws_error_code": error_code},
                retryable=is_retryable
            )
        
        # Retry if applicable
        if is_retryable and attempt < MAX_RETRIES:
            delay = exponential_backoff(attempt)
            logger.warning(
                f"Retryable error encountered, retrying after {delay:.2f}s",
                extra={
                    "attempt": attempt,
                    "error_code": error_code,
                    "delay_seconds": delay
                }
            )
            time.sleep(delay)
            return handle_agent_processing(message, session_id, actor_id, attempt + 1)
        
        raise agent_error
    
    except RuntimeError as e:
        error_message = str(e)
        
        # Determine error type from message
        if "initialize" in error_message.lower():
            metrics.add_metric(name="InitializationErrors", unit=MetricUnit.Count, value=1)
            raise AgentError(
                code=ErrorCode.AGENT_INITIALIZATION_FAILED,
                message="Failed to initialize agent",
                status_code=500,
                details={"error": error_message},
                retryable=True
            )
        elif "memory" in error_message.lower():
            metrics.add_metric(name="MemoryErrors", unit=MetricUnit.Count, value=1)
            raise AgentError(
                code=ErrorCode.MEMORY_SERVICE_UNAVAILABLE,
                message="Memory service unavailable",
                status_code=503,
                details={"error": error_message},
                retryable=True
            )
        else:
            metrics.add_metric(name="AgentErrors", unit=MetricUnit.Count, value=1)
            raise AgentError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Internal agent error",
                status_code=500,
                details={"error": error_message},
                retryable=False
            )
    
    except Exception as e:
        logger.error("Unexpected error during agent processing", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "session_id": session_id
        })
        metrics.add_metric(name="UnexpectedErrors", unit=MetricUnit.Count, value=1)
        
        raise AgentError(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            status_code=500,
            details={"error_type": type(e).__name__},
            retryable=False
        )


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for WebSocket sendMessage route.
    
    This handler processes admin queries through the Bedrock AgentCore agent
    and streams responses back via WebSocket. It is invoked when a client sends
    a message through an established WebSocket connection.
    
    Prerequisites:
    - Connection must be established via websocket_connect handler
    - Connection info must exist in connections DynamoDB table
    - Session must be initialized
    
    WebSocket Event Format:
    {
        "requestContext": {
            "connectionId": str,
            "routeKey": "sendMessage",
            "domainName": str,
            "stage": str
        },
        "body": {
            "action": "sendMessage",
            "message": str
        }
    }
    
    Response Format (streamed to WebSocket):
    Multiple messages sent via ApiGatewayManagementApi:
    {"type": "chunk", "content": str, "timestamp": int}
    {"type": "chunk", "content": str, "timestamp": int}
    ...
    {"type": "complete", "content": "", "timestamp": int}
    
    Or on error:
    {"type": "error", "content": str, "timestamp": int}
    
    Args:
        event: Lambda event from WebSocket API Gateway
        context: Lambda context object
    
    Returns:
        API Gateway response (200 OK or error status)
    """
    request_id = context.aws_request_id
    start_time = time.time()
    connection_id = None
    
    try:
        # Add request ID to logger context
        logger.append_keys(request_id=request_id)
        
        # Handle heartbeat/ping messages
        body = event.get('body')
        if body:
            try:
                body_data = json.loads(body) if isinstance(body, str) else body
                if body_data.get('action') == 'ping':
                    # Respond to ping with pong
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"message": "pong"})
                    }
            except:
                pass  # Continue with normal processing if parsing fails
        
        # Emit invocation metric
        metrics.add_metric(name="AgentInvocations", unit=MetricUnit.Count, value=1)
        
        # Validate request and extract parameters
        logger.info("Validating WebSocket request")
        validated_params = validate_request(event)
        
        message = validated_params["message"]
        session_id = validated_params["session_id"]
        actor_id = validated_params["actor_id"]
        connection_id = validated_params["connection_id"]
        
        # Get WebSocket endpoint URL
        request_context = event.get('requestContext', {})
        domain_name = request_context.get('domainName')
        stage = request_context.get('stage')
        
        if not domain_name or not stage:
            logger.error("Missing WebSocket endpoint information")
            raise AgentError(
                code=ErrorCode.INTERNAL_ERROR,
                message="WebSocket configuration error",
                status_code=500
            )
        
        endpoint_url = f"https://{domain_name}/{stage}"
        
        # Process message through agent
        logger.info("Processing agent request", extra={
            "session_id": session_id,
            "actor_id": actor_id,
            "connection_id": connection_id
        })
        
        processing_result = handle_agent_processing(
            message=message,
            session_id=session_id,
            actor_id=actor_id
        )
        
        # Stream response to WebSocket
        response_text = processing_result.get("response", "")
        
        # Send response as single message (can be enhanced for true streaming later)
        success = send_websocket_message(
            connection_id=connection_id,
            message_type="chunk",
            content=response_text,
            endpoint_url=endpoint_url
        )
        
        if success:
            send_websocket_message(
                connection_id=connection_id,
                message_type="complete",
                content="",
                endpoint_url=endpoint_url
            )
        
        # Calculate and emit latency metric
        latency_ms = (time.time() - start_time) * 1000
        metrics.add_metric(name="AgentLatency", unit=MetricUnit.Milliseconds, value=latency_ms)
        
        # Emit tool invocation metrics
        tools_invoked = processing_result.get("tools_invoked", [])
        if tools_invoked:
            metrics.add_metric(name="ToolInvocations", unit=MetricUnit.Count, value=len(tools_invoked))
            for tool_name in tools_invoked:
                metrics.add_metric(name=f"Tool_{tool_name}_Invocations", unit=MetricUnit.Count, value=1)
        
        logger.info("WebSocket response sent", extra={
            "session_id": session_id,
            "connection_id": connection_id,
            "latency_ms": latency_ms,
            "tools_invoked": tools_invoked
        })
        
        # Return success to API Gateway
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Response sent"})
        }
    
    except AgentError as e:
        # Structured error from our code
        logger.error("Agent error", extra={
            "error_code": e.code.value,
            "error_message": e.message,
            "status_code": e.status_code,
            "details": e.details,
            "connection_id": connection_id
        })
        
        # Emit error metric
        metrics.add_metric(name=f"Error_{e.code.value}", unit=MetricUnit.Count, value=1)
        
        # Send error message to WebSocket connection
        if connection_id:
            request_context = event.get('requestContext', {})
            domain_name = request_context.get('domainName')
            stage = request_context.get('stage')
            
            if domain_name and stage:
                endpoint_url = f"https://{domain_name}/{stage}"
                send_websocket_message(
                    connection_id=connection_id,
                    message_type="error",
                    content=e.message,
                    endpoint_url=endpoint_url
                )
        
        # Return error status to API Gateway
        return {
            "statusCode": e.status_code,
            "body": json.dumps({
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "timestamp": int(datetime.now().timestamp()),
                    "requestId": request_id
                }
            })
        }
    
    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error in handler", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "connection_id": connection_id
        })
        
        metrics.add_metric(name="UnhandledErrors", unit=MetricUnit.Count, value=1)
        
        # Try to send error to WebSocket
        if connection_id:
            try:
                request_context = event.get('requestContext', {})
                domain_name = request_context.get('domainName')
                stage = request_context.get('stage')
                
                if domain_name and stage:
                    endpoint_url = f"https://{domain_name}/{stage}"
                    send_websocket_message(
                        connection_id=connection_id,
                        message_type="error",
                        content="An unexpected error occurred. Please try again.",
                        endpoint_url=endpoint_url
                    )
            except:
                pass
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected error occurred",
                    "timestamp": int(datetime.now().timestamp()),
                    "requestId": request_id
                }
            })
        }
