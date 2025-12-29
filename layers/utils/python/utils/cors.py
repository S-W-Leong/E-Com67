"""
CORS Utilities for Lambda Functions

Provides standardized CORS headers and response helpers to ensure
consistent cross-origin resource sharing across all API endpoints.
"""

from typing import Dict, Any, Optional


# Standard CORS headers for all API responses
STANDARD_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, X-User-Id"
}


def get_cors_headers(additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get standardized CORS headers for API responses.
    
    Args:
        additional_headers: Optional additional headers to include
        
    Returns:
        Dict containing CORS headers
    """
    headers = STANDARD_CORS_HEADERS.copy()
    
    if additional_headers:
        headers.update(additional_headers)
    
    return headers


def create_cors_response(
    status_code: int,
    body: Any,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a standardized API Gateway response with CORS headers.
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        additional_headers: Optional additional headers
        
    Returns:
        Dict containing API Gateway response format
    """
    import json
    
    return {
        "statusCode": status_code,
        "headers": get_cors_headers(additional_headers),
        "body": json.dumps(body) if not isinstance(body, str) else body
    }


def create_success_response(
    data: Any,
    status_code: int = 200,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response with CORS headers.
    
    Args:
        data: Response data
        status_code: HTTP status code (default: 200)
        additional_headers: Optional additional headers
        
    Returns:
        Dict containing API Gateway response format
    """
    return create_cors_response(status_code, data, additional_headers)


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict] = None,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response with CORS headers.
    
    Args:
        status_code: HTTP status code
        error_code: Application-specific error code
        message: Error message
        details: Optional error details
        additional_headers: Optional additional headers
        
    Returns:
        Dict containing API Gateway response format
    """
    import time
    from utils.formatters import format_timestamp
    
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": format_timestamp(time.time())
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return create_cors_response(status_code, error_response, additional_headers)


def create_options_response(additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create a standardized OPTIONS response for CORS preflight requests.
    
    Args:
        additional_headers: Optional additional headers
        
    Returns:
        Dict containing API Gateway response format
    """
    return create_success_response({}, 200, additional_headers)


def ensure_cors_headers(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a response has CORS headers, adding them if missing.
    
    This is useful for Lambda functions using AWS Lambda Powertools
    or other frameworks that don't automatically add CORS headers.
    
    Args:
        response: API Gateway response dict
        
    Returns:
        Response dict with CORS headers ensured
    """
    if 'headers' not in response:
        response['headers'] = {}
    
    # Add CORS headers if not already present
    cors_headers = get_cors_headers()
    for key, value in cors_headers.items():
        if key not in response['headers']:
            response['headers'][key] = value
    
    return response