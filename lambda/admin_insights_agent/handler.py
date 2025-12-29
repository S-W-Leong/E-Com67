"""
Admin Insights Agent Lambda Handler

This module implements the main Lambda handler for the Admin Insights Agent.
It provides comprehensive error handling, observability, and retry logic for
processing admin queries through the Bedrock AgentCore agent.

Key Features:
- AWS Lambda Powertools integration (logging, tracing, metrics)
- Comprehensive error handling for all error categories
- Exponential backoff retry logic for transient failures
- CloudWatch metrics emission
- Structured error responses

Requirements:
- Requirements 9.1: Error logging and handling
- Requirements 9.2: Structured error responses
- Requirements 9.3: CloudWatch metrics and observability
"""

import os
import json
import time
from typing import Dict, Any, Optional
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
    apply_guardrails
)
from session_manager import SessionManager

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="AdminInsightsAgent")

# Environment variables
MEMORY_ID = os.environ.get('MEMORY_ID', '')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')

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


def create_error_response(
    error: AgentError,
    request_id: str
) -> Dict[str, Any]:
    """
    Create a structured error response.
    
    Args:
        error: AgentError instance
        request_id: Lambda request ID for tracing
    
    Returns:
        Formatted error response dictionary
    """
    return {
        "statusCode": error.status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps({
            "error": {
                "code": error.code.value,
                "message": error.message,
                "timestamp": int(datetime.now().timestamp()),
                "requestId": request_id,
                "details": error.details
            }
        })
    }


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


@tracer.capture_method
def validate_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate incoming request and extract parameters.
    
    Args:
        event: Lambda event dictionary
    
    Returns:
        Validated request parameters
    
    Raises:
        AgentError: If validation fails
    """
    try:
        # Parse body if it's a string
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        # Extract required parameters
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
        
        # Extract optional parameters
        session_id = body.get('sessionId')
        actor_id = body.get('actorId')
        
        # Extract actor_id from authorizer context if not provided
        if not actor_id:
            request_context = event.get('requestContext', {})
            authorizer = request_context.get('authorizer', {})
            claims = authorizer.get('claims', {})
            actor_id = claims.get('sub') or claims.get('cognito:username')
        
        if not actor_id:
            raise AgentError(
                code=ErrorCode.UNAUTHORIZED,
                message="Unable to identify user. Authentication required.",
                status_code=401
            )
        
        # Generate session_id if not provided
        if not session_id:
            import uuid
            session_id = f"session-{uuid.uuid4()}"
        
        logger.info("Request validated", extra={
            "session_id": session_id,
            "actor_id": actor_id,
            "message_length": len(message)
        })
        
        return {
            "message": message.strip(),
            "session_id": session_id,
            "actor_id": actor_id
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
        
    except ValueError as e:
        # Guardrail violations or validation errors (not retryable)
        error_message = str(e)
        
        if "cannot be processed" in error_message.lower():
            metrics.add_metric(name="GuardrailBlocked", unit=MetricUnit.Count, value=1)
            raise AgentError(
                code=ErrorCode.CONTENT_BLOCKED,
                message=error_message,
                status_code=400,
                retryable=False
            )
        else:
            raise AgentError(
                code=ErrorCode.INVALID_INPUT,
                message=error_message,
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
    Main Lambda handler for Admin Insights Agent.
    
    This handler processes admin queries through the Bedrock AgentCore agent
    with comprehensive error handling, retry logic, and observability.
    
    Request Format:
    {
        "body": {
            "message": str (required),
            "sessionId": str (optional),
            "actorId": str (optional, extracted from auth context if not provided)
        }
    }
    
    Response Format (Success):
    {
        "statusCode": 200,
        "body": {
            "response": str,
            "session_id": str,
            "timestamp": int,
            "metadata": {
                "actor_id": str,
                "tools_invoked": List[str],
                "tools_count": int
            }
        }
    }
    
    Response Format (Error):
    {
        "statusCode": 4xx | 5xx,
        "body": {
            "error": {
                "code": str,
                "message": str,
                "timestamp": int,
                "requestId": str,
                "details": dict
            }
        }
    }
    
    Args:
        event: Lambda event from API Gateway
        context: Lambda context object
    
    Returns:
        API Gateway response dictionary
    """
    request_id = context.request_id
    start_time = time.time()
    
    try:
        # Add request ID to logger context
        logger.append_keys(request_id=request_id)
        
        # Emit invocation metric
        metrics.add_metric(name="AgentInvocations", unit=MetricUnit.Count, value=1)
        
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                },
                "body": ""
            }
        
        # Validate request
        logger.info("Validating request")
        validated_params = validate_request(event)
        
        message = validated_params["message"]
        session_id = validated_params["session_id"]
        actor_id = validated_params["actor_id"]
        
        # Process message through agent
        logger.info("Processing agent request", extra={
            "session_id": session_id,
            "actor_id": actor_id
        })
        
        processing_result = handle_agent_processing(
            message=message,
            session_id=session_id,
            actor_id=actor_id
        )
        
        # Format response
        response_body = format_response(
            processing_result=processing_result,
            include_metadata=True
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
        
        logger.info("Request processed successfully", extra={
            "session_id": session_id,
            "latency_ms": latency_ms,
            "tools_invoked": tools_invoked
        })
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": json.dumps(response_body)
        }
    
    except AgentError as e:
        # Structured error from our code
        logger.error("Agent error", extra={
            "error_code": e.code.value,
            "error_message": e.message,
            "status_code": e.status_code,
            "details": e.details
        })
        
        # Emit error metric
        metrics.add_metric(name=f"Error_{e.code.value}", unit=MetricUnit.Count, value=1)
        
        return create_error_response(e, request_id)
    
    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error in handler", extra={
            "error": str(e),
            "error_type": type(e).__name__
        })
        
        metrics.add_metric(name="UnhandledErrors", unit=MetricUnit.Count, value=1)
        
        error = AgentError(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again.",
            status_code=500,
            details={"error_type": type(e).__name__}
        )
        
        return create_error_response(error, request_id)
