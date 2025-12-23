"""
Simple Lambda test handler to verify Strands SDK import and initialization.

This function can be deployed to test the Strands SDK setup in the actual
Lambda environment.
"""

import json
import os
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Test Lambda handler for Strands SDK setup validation.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Test results as JSON response
    """
    
    test_results = {
        'test_timestamp': context.aws_request_id if hasattr(context, 'aws_request_id') else 'local-test',
        'environment_check': {},
        'import_check': {},
        'configuration_check': {},
        'overall_status': 'unknown'
    }
    
    try:
        # Test 1: Environment variables
        required_env_vars = [
            'CHAT_HISTORY_TABLE_NAME',
            'PRODUCTS_TABLE_NAME', 
            'BEDROCK_MODEL_ID',
            'AWS_REGION'
        ]
        
        env_status = {}
        for var in required_env_vars:
            env_status[var] = {
                'present': var in os.environ,
                'value': os.environ.get(var, 'NOT_SET')[:50] + '...' if len(os.environ.get(var, '')) > 50 else os.environ.get(var, 'NOT_SET')
            }
        
        test_results['environment_check'] = {
            'status': 'success' if all(var in os.environ for var in required_env_vars) else 'partial',
            'variables': env_status
        }
        
        # Test 2: Import Strands configuration
        try:
            from strands_config import StrandsAgentManager, test_strands_sdk_import
            
            test_results['import_check'] = {
                'status': 'success',
                'message': 'Strands configuration imported successfully'
            }
            
            # Test 3: Configuration creation
            try:
                manager = StrandsAgentManager()
                validation_results = manager.validate_configuration()
                
                test_results['configuration_check'] = {
                    'status': 'success',
                    'validation': validation_results
                }
                
                # Test 4: SDK availability
                sdk_test = test_strands_sdk_import()
                test_results['sdk_availability'] = sdk_test
                
            except Exception as e:
                test_results['configuration_check'] = {
                    'status': 'error',
                    'error': str(e)
                }
                
        except ImportError as e:
            test_results['import_check'] = {
                'status': 'error',
                'error': f'Import failed: {str(e)}'
            }
        
        # Determine overall status
        if (test_results['environment_check']['status'] == 'success' and 
            test_results['import_check']['status'] == 'success' and
            test_results['configuration_check']['status'] == 'success'):
            test_results['overall_status'] = 'success'
        elif any(check.get('status') == 'error' for check in test_results.values() if isinstance(check, dict)):
            test_results['overall_status'] = 'error'
        else:
            test_results['overall_status'] = 'partial'
            
    except Exception as e:
        test_results['overall_status'] = 'error'
        test_results['unexpected_error'] = str(e)
    
    return {
        'statusCode': 200,
        'body': json.dumps(test_results, indent=2),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


# For local testing
if __name__ == '__main__':
    # Mock context for local testing
    class MockContext:
        aws_request_id = 'local-test-123'
    
    # Set up test environment
    os.environ.update({
        'CHAT_HISTORY_TABLE_NAME': 'test-chat-history',
        'PRODUCTS_TABLE_NAME': 'test-products',
        'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1',
        'AWS_REGION': 'ap-southeast-1'
    })
    
    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))