"""
Simple test for opentelemetry.semconv import
"""

import json

def handler(event, context):
    """Simple test for semconv import."""
    
    result = {}
    
    # Test opentelemetry.semconv import
    try:
        from opentelemetry.semconv import trace
        result['semconv_trace'] = 'SUCCESS'
    except Exception as e:
        result['semconv_trace'] = f'FAILED: {str(e)}'
    
    try:
        from opentelemetry.semconv.attributes import http_attributes
        result['semconv_attributes'] = 'SUCCESS'
    except Exception as e:
        result['semconv_attributes'] = f'FAILED: {str(e)}'
    
    # Test strands import
    try:
        import strands
        result['strands'] = 'SUCCESS'
    except Exception as e:
        result['strands'] = f'FAILED: {str(e)}'
    
    return {
        'statusCode': 200,
        'body': json.dumps(result, indent=2)
    }