#!/usr/bin/env python3
"""
Test script to verify Strands SDK import works in the deployed Lambda function.
This will invoke the chat Lambda function with a simple test payload.
"""

import json
import boto3
import sys

def test_strands_import():
    """Test if Strands SDK can be imported in the deployed Lambda function."""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
    
    # Test payload that will trigger Strands SDK import
    test_payload = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token"
        },
        "body": json.dumps({
            "message": "Hello, can you help me test the Strands SDK import?",
            "user_id": "test-user-123"
        })
    }
    
    try:
        print("🧪 Testing Strands SDK import in deployed Lambda function...")
        print(f"📤 Invoking e-com67-chat function...")
        
        # Invoke the chat Lambda function
        response = lambda_client.invoke(
            FunctionName='e-com67-chat',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse the response
        response_payload = json.loads(response['Payload'].read())
        
        print(f"📥 Response Status Code: {response['StatusCode']}")
        print(f"📄 Response Payload: {json.dumps(response_payload, indent=2)}")
        
        # Check if the function executed successfully
        if response['StatusCode'] == 200:
            if 'errorMessage' in response_payload:
                print(f"❌ Lambda function returned an error: {response_payload['errorMessage']}")
                if 'Strands SDK is not properly installed' in response_payload['errorMessage']:
                    print("🔍 Strands SDK import issue confirmed - architecture mismatch still exists")
                    return False
                else:
                    print("🔍 Different error - not related to Strands SDK import")
                    return False
            else:
                print("✅ Lambda function executed successfully!")
                print("✅ Strands SDK import appears to be working!")
                return True
        else:
            print(f"❌ Lambda invocation failed with status code: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_strands_import()
    sys.exit(0 if success else 1)