#!/usr/bin/env python3
"""
Deploy a simple test function to check Strands imports.
"""

import boto3
import json
import zipfile
import os
import time

def create_test_function():
    """Create a test Lambda function to check Strands imports."""
    
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    # Create deployment package
    zip_filename = 'test_strands_import.zip'
    
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write('lambda/simple_test_strands.py', 'simple_test_strands.py')
    
    # Read the zip file
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    function_name = 'e-com67-test-strands-import'
    
    try:
        # Try to update existing function
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler='simple_test_strands.handler'
        )
        
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        print(f"Updated existing function: {function_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.10',
            Role='arn:aws:iam::724542698940:role/e-com67-lambda-execution-role',
            Handler='simple_test_strands.handler',
            Code={'ZipFile': zip_content},
            Description='Test function for Strands SDK imports',
            Timeout=30,
            MemorySize=256,
            Layers=[
                'arn:aws:lambda:ap-southeast-1:724542698940:layer:e-com67-strands:11'
            ],
            Environment={
                'Variables': {
                    'TEST_MODE': 'true'
                }
            }
        )
        print(f"Created new function: {function_name}")
    
    # Clean up
    os.remove(zip_filename)
    
    return response

def test_function():
    """Test the deployed function."""
    
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    function_name = 'e-com67-test-strands-import'
    
    print("Testing function...")
    
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({})
    )
    
    result = json.loads(response['Payload'].read())
    
    print(f"Status Code: {response['StatusCode']}")
    print(f"Result: {json.dumps(result, indent=2)}")
    
    return result

if __name__ == "__main__":
    print("=== Deploying Test Function ===")
    create_response = create_test_function()
    
    print("\n=== Testing Function ===")
    time.sleep(2)  # Wait for function to be ready
    test_result = test_function()
    
    print("\nTest completed.")