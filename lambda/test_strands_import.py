"""
Simple Lambda function to test Strands SDK imports.
"""

import json
import sys
import os

def handler(event, context):
    """Test Strands SDK imports and return detailed diagnostic information."""
    
    result = {
        'python_version': sys.version,
        'python_path': sys.path[:5],
        'environment_variables': {
            'AWS_LAMBDA_FUNCTION_NAME': os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
            'AWS_LAMBDA_FUNCTION_VERSION': os.environ.get('AWS_LAMBDA_FUNCTION_VERSION'),
            'AWS_EXECUTION_ENV': os.environ.get('AWS_EXECUTION_ENV'),
        },
        'layer_info': {},
        'import_tests': {}
    }
    
    # Check layer paths
    layer_paths = ['/opt/python', '/opt/python/lib/python3.10/site-packages']
    for path in layer_paths:
        result['layer_info'][path] = {
            'exists': os.path.exists(path),
            'contents': []
        }
        if os.path.exists(path):
            try:
                contents = os.listdir(path)[:20]  # First 20 items
                result['layer_info'][path]['contents'] = contents
            except Exception as e:
                result['layer_info'][path]['error'] = str(e)
    
    # Test imports step by step
    
    # Test 1: Basic imports
    try:
        import boto3
        import json
        result['import_tests']['basic_imports'] = 'SUCCESS'
    except Exception as e:
        result['import_tests']['basic_imports'] = f'FAILED: {str(e)}'
    
    # Test 2: pydantic_core
    try:
        import pydantic_core
        result['import_tests']['pydantic_core'] = 'SUCCESS'
        
        # Try to get version
        try:
            from pydantic_core import __version__
            result['import_tests']['pydantic_core_version'] = __version__
        except Exception as e:
            result['import_tests']['pydantic_core_version'] = f'FAILED: {str(e)}'
            
    except Exception as e:
        result['import_tests']['pydantic_core'] = f'FAILED: {str(e)}'
    
    # Test 3: pydantic
    try:
        import pydantic
        result['import_tests']['pydantic'] = 'SUCCESS'
    except Exception as e:
        result['import_tests']['pydantic'] = f'FAILED: {str(e)}'
    
    # Test 4: Check opentelemetry structure
    try:
        import opentelemetry
        result['import_tests']['opentelemetry'] = 'SUCCESS'
        
        # Check what's in opentelemetry directory
        otel_path = '/opt/python/opentelemetry'
        if os.path.exists(otel_path):
            contents = os.listdir(otel_path)
            result['import_tests']['opentelemetry_contents'] = contents
            
            # Check specifically for semconv
            semconv_path = '/opt/python/opentelemetry/semconv'
            if os.path.exists(semconv_path):
                semconv_contents = os.listdir(semconv_path)
                result['import_tests']['semconv_contents'] = semconv_contents
            else:
                result['import_tests']['semconv_contents'] = 'PATH_NOT_FOUND'
        else:
            result['import_tests']['opentelemetry_contents'] = 'PATH_NOT_FOUND'
            
    except Exception as e:
        result['import_tests']['opentelemetry'] = f'FAILED: {str(e)}'
    
    # Test 5: strands
    try:
        import strands
        result['import_tests']['strands'] = 'SUCCESS'
        
        # Try specific imports
        try:
            from strands import Agent
            result['import_tests']['strands_agent'] = 'SUCCESS'
        except Exception as e:
            result['import_tests']['strands_agent'] = f'FAILED: {str(e)}'
            
        try:
            from strands.models import BedrockModel
            result['import_tests']['strands_bedrock_model'] = 'SUCCESS'
        except Exception as e:
            result['import_tests']['strands_bedrock_model'] = f'FAILED: {str(e)}'
            
    except Exception as e:
        result['import_tests']['strands'] = f'FAILED: {str(e)}'
    
    # Test 6: Check pydantic_core compiled extension
    try:
        pydantic_core_path = '/opt/python/pydantic_core'
        if os.path.exists(pydantic_core_path):
            files = os.listdir(pydantic_core_path)
            so_files = [f for f in files if f.endswith('.so')]
            result['import_tests']['pydantic_core_extensions'] = so_files
        else:
            result['import_tests']['pydantic_core_extensions'] = 'PATH_NOT_FOUND'
    except Exception as e:
        result['import_tests']['pydantic_core_extensions'] = f'ERROR: {str(e)}'
    
    return {
        'statusCode': 200,
        'body': json.dumps(result, indent=2)
    }