#!/usr/bin/env python3
"""
Test script to validate Strands SDK deployment configuration.

This script checks that the CDK stack configuration is correct for the
Strands SDK integration without actually deploying.
"""

import os
import sys
import json
from typing import Dict, Any


def test_layer_structure() -> Dict[str, Any]:
    """Test that the Strands layer structure is correct"""
    print("Testing Strands layer structure...")
    
    layer_path = "layers/strands/python"
    requirements_file = os.path.join(layer_path, "requirements.txt")
    
    results = {
        'layer_directory_exists': os.path.exists(layer_path),
        'requirements_file_exists': os.path.exists(requirements_file),
        'requirements_content': None
    }
    
    if results['requirements_file_exists']:
        try:
            with open(requirements_file, 'r') as f:
                content = f.read().strip()
                results['requirements_content'] = content.split('\n')
        except Exception as e:
            results['requirements_read_error'] = str(e)
    
    status = 'success' if all([
        results['layer_directory_exists'],
        results['requirements_file_exists'],
        results['requirements_content']
    ]) else 'error'
    
    return {
        'status': status,
        'message': 'Layer structure validation completed',
        'details': results
    }


def test_cdk_stack_syntax() -> Dict[str, Any]:
    """Test that the CDK stack has valid Python syntax"""
    print("Testing CDK stack syntax...")
    
    stack_file = "stacks/compute_stack.py"
    
    if not os.path.exists(stack_file):
        return {
            'status': 'error',
            'message': 'CDK stack file not found',
            'file_path': stack_file
        }
    
    try:
        # Try to compile the stack file to check syntax
        with open(stack_file, 'r') as f:
            source_code = f.read()
        
        compile(source_code, stack_file, 'exec')
        
        # Check for Strands layer references
        strands_references = [
            'strands_layer' in source_code,
            'StrandsLayer' in source_code,
            'e-com67-strands' in source_code
        ]
        
        return {
            'status': 'success',
            'message': 'CDK stack syntax is valid',
            'strands_references_found': sum(strands_references),
            'has_strands_integration': any(strands_references)
        }
        
    except SyntaxError as e:
        return {
            'status': 'error',
            'message': f'CDK stack syntax error: {str(e)}',
            'line_number': e.lineno,
            'error_text': e.text
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error reading CDK stack: {str(e)}'
        }


def test_chat_function_config() -> Dict[str, Any]:
    """Test that the chat function configuration includes Strands setup"""
    print("Testing chat function configuration...")
    
    try:
        # Import and check the configuration module
        sys.path.insert(0, 'lambda/chat')
        from strands_config import StrandsAgentConfig
        
        # Create a test configuration
        config = StrandsAgentConfig.from_environment()
        
        # Validate configuration
        validation = config.__class__.from_environment().validate_configuration if hasattr(config.__class__.from_environment(), 'validate_configuration') else None
        
        return {
            'status': 'success',
            'message': 'Chat function configuration is valid',
            'config_available': True,
            'model_id': config.bedrock_config.model_id,
            'deployment_stage': config.deployment_stage.value
        }
        
    except ImportError as e:
        return {
            'status': 'error',
            'message': f'Configuration import failed: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Configuration test failed: {str(e)}'
        }


def test_environment_variables() -> Dict[str, Any]:
    """Test that required environment variables are documented"""
    print("Testing environment variable configuration...")
    
    # Check CDK stack for environment variables
    stack_file = "stacks/compute_stack.py"
    
    try:
        with open(stack_file, 'r') as f:
            stack_content = f.read()
        
        # Look for Strands-related environment variables
        strands_env_vars = [
            'BEDROCK_TEMPERATURE',
            'BEDROCK_MAX_TOKENS', 
            'BEDROCK_STREAMING',
            'DEPLOYMENT_STAGE',
            'PLATFORM_VERSION'
        ]
        
        found_vars = []
        for var in strands_env_vars:
            if var in stack_content:
                found_vars.append(var)
        
        return {
            'status': 'success' if len(found_vars) >= 3 else 'partial',
            'message': f'Found {len(found_vars)} Strands environment variables',
            'expected_vars': strands_env_vars,
            'found_vars': found_vars
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error checking environment variables: {str(e)}'
        }


def run_deployment_tests() -> Dict[str, Any]:
    """Run all deployment validation tests"""
    print("=" * 60)
    print("E-Com67 Strands SDK Deployment Test")
    print("=" * 60)
    
    test_results = {}
    
    tests = [
        ('layer_structure', test_layer_structure),
        ('cdk_stack_syntax', test_cdk_stack_syntax),
        ('chat_function_config', test_chat_function_config),
        ('environment_variables', test_environment_variables)
    ]
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name.replace('_', ' ').title()} ---")
        try:
            result = test_func()
            test_results[test_name] = result
            
            if result['status'] == 'success':
                print(f"✅ {result['message']}")
            elif result['status'] == 'partial':
                print(f"⚠️  {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        except Exception as e:
            error_result = {
                'status': 'error',
                'message': f'Test execution failed: {str(e)}'
            }
            test_results[test_name] = error_result
            print(f"❌ {error_result['message']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Deployment Test Summary")
    print("=" * 60)
    
    success_count = sum(1 for result in test_results.values() if result['status'] == 'success')
    partial_count = sum(1 for result in test_results.values() if result['status'] == 'partial')
    error_count = sum(1 for result in test_results.values() if result['status'] == 'error')
    
    print(f"✅ Successful: {success_count}")
    print(f"⚠️  Partial: {partial_count}")
    print(f"❌ Errors: {error_count}")
    
    overall_status = 'ready' if error_count == 0 else 'needs_fixes'
    
    return {
        'overall_status': overall_status,
        'summary': {
            'success_count': success_count,
            'partial_count': partial_count,
            'error_count': error_count
        },
        'detailed_results': test_results,
        'deployment_ready': error_count == 0
    }


if __name__ == '__main__':
    # Set up minimal environment for testing
    os.environ.update({
        'CHAT_HISTORY_TABLE_NAME': 'test-chat-history',
        'PRODUCTS_TABLE_NAME': 'test-products',
        'AWS_REGION': 'ap-southeast-1',
        'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1',
        'DEPLOYMENT_STAGE': 'development'
    })
    
    results = run_deployment_tests()
    
    print(f"\nDeployment Readiness: {'✅ READY' if results['deployment_ready'] else '❌ NEEDS FIXES'}")
    
    # Exit with appropriate code
    sys.exit(0 if results['deployment_ready'] else 1)