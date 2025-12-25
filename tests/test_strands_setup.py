#!/usr/bin/env python3
"""
Test script for Strands SDK setup and configuration.

This script validates that the Strands SDK is properly installed and configured
for the E-Com67 platform enhancement.
"""

import os
import sys
import json
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

def test_environment_setup() -> Dict[str, Any]:
    """Test environment variable setup"""
    print("Testing environment setup...")
    
    # Set up test environment variables
    test_env_vars = {
        'CHAT_HISTORY_TABLE_NAME': 'test-chat-history',
        'PRODUCTS_TABLE_NAME': 'test-products',
        'AWS_REGION': 'ap-southeast-1',
        'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1',
        'DEPLOYMENT_STAGE': 'development'
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    return {
        'status': 'success',
        'message': 'Environment variables configured for testing',
        'variables_set': list(test_env_vars.keys())
    }


def test_strands_config_import() -> Dict[str, Any]:
    """Test importing the Strands configuration module"""
    print("Testing Strands configuration import...")
    
    try:
        from strands_config import (
            StrandsAgentConfig, 
            StrandsAgentManager, 
            DeploymentStage,
            test_strands_sdk_import
        )
        
        return {
            'status': 'success',
            'message': 'Strands configuration module imported successfully',
            'classes_available': [
                'StrandsAgentConfig',
                'StrandsAgentManager', 
                'DeploymentStage'
            ]
        }
        
    except ImportError as e:
        return {
            'status': 'error',
            'message': f'Failed to import Strands configuration: {str(e)}',
            'error_type': 'ImportError'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error importing configuration: {str(e)}',
            'error_type': type(e).__name__
        }


def test_configuration_creation() -> Dict[str, Any]:
    """Test creating Strands agent configuration"""
    print("Testing configuration creation...")
    
    try:
        from strands_config import StrandsAgentConfig, DeploymentStage
        
        # Test configuration creation from environment
        config = StrandsAgentConfig.from_environment()
        
        return {
            'status': 'success',
            'message': 'Configuration created successfully',
            'config_details': {
                'deployment_stage': config.deployment_stage.value,
                'model_id': config.bedrock_config.model_id,
                'temperature': config.bedrock_config.temperature,
                'max_tokens': config.bedrock_config.max_tokens,
                'memory_limit': config.conversation_memory_limit,
                'platform_name': config.platform_name
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to create configuration: {str(e)}',
            'error_type': type(e).__name__
        }


def test_agent_manager_creation() -> Dict[str, Any]:
    """Test creating Strands agent manager"""
    print("Testing agent manager creation...")
    
    try:
        from strands_config import StrandsAgentManager
        
        # Create agent manager
        manager = StrandsAgentManager()
        
        # Validate configuration
        validation_results = manager.validate_configuration()
        
        return {
            'status': 'success',
            'message': 'Agent manager created successfully',
            'validation_results': validation_results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to create agent manager: {str(e)}',
            'error_type': type(e).__name__
        }


def test_strands_sdk_availability() -> Dict[str, Any]:
    """Test Strands SDK availability"""
    print("Testing Strands SDK availability...")
    
    try:
        from strands_config import test_strands_sdk_import
        
        # Run SDK import test
        sdk_test_results = test_strands_sdk_import()
        
        return {
            'status': 'success' if sdk_test_results['sdk_available'] else 'warning',
            'message': 'SDK availability test completed',
            'sdk_results': sdk_test_results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to test SDK availability: {str(e)}',
            'error_type': type(e).__name__
        }


def run_all_tests() -> Dict[str, Any]:
    """Run all setup tests"""
    print("=" * 60)
    print("E-Com67 Strands SDK Setup Test")
    print("=" * 60)
    
    test_results = {}
    
    # Run tests in order
    tests = [
        ('environment_setup', test_environment_setup),
        ('config_import', test_strands_config_import),
        ('configuration_creation', test_configuration_creation),
        ('agent_manager_creation', test_agent_manager_creation),
        ('strands_sdk_availability', test_strands_sdk_availability)
    ]
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name.replace('_', ' ').title()} ---")
        try:
            result = test_func()
            test_results[test_name] = result
            
            if result['status'] == 'success':
                print(f"✅ {result['message']}")
            elif result['status'] == 'warning':
                print(f"⚠️  {result['message']}")
            else:
                print(f"❌ {result['message']}")
                
        except Exception as e:
            error_result = {
                'status': 'error',
                'message': f'Test execution failed: {str(e)}',
                'error_type': type(e).__name__
            }
            test_results[test_name] = error_result
            print(f"❌ {error_result['message']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    success_count = sum(1 for result in test_results.values() if result['status'] == 'success')
    warning_count = sum(1 for result in test_results.values() if result['status'] == 'warning')
    error_count = sum(1 for result in test_results.values() if result['status'] == 'error')
    
    print(f"✅ Successful: {success_count}")
    print(f"⚠️  Warnings: {warning_count}")
    print(f"❌ Errors: {error_count}")
    
    overall_status = 'success' if error_count == 0 else 'partial' if success_count > 0 else 'failed'
    
    return {
        'overall_status': overall_status,
        'summary': {
            'success_count': success_count,
            'warning_count': warning_count,
            'error_count': error_count
        },
        'detailed_results': test_results
    }


if __name__ == '__main__':
    results = run_all_tests()
    
    # Print JSON results for programmatic use
    print(f"\nDetailed Results (JSON):")
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if results['overall_status'] == 'success':
        sys.exit(0)
    elif results['overall_status'] == 'partial':
        sys.exit(1)  # Warnings
    else:
        sys.exit(2)  # Errors