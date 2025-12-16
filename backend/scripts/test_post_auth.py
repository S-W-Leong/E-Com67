"""
Test script for post-authentication Lambda function
Tests the handler locally before deployment
"""
import json
import os
import sys

# Mock environment variables
os.environ['USERS_TABLE'] = 'e-com67-users'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'post_auth'))

# Import the handler
from index import handler


def test_post_auth():
    """Test post-authentication trigger with sample event"""
    
    # Sample Cognito Post-Auth event
    event = {
        "version": "1",
        "triggerSource": "PostAuthentication_Authentication",
        "region": "us-east-1",
        "userPoolId": "us-east-1_test123",
        "userName": "test-user-123",
        "request": {
            "userAttributes": {
                "sub": "12345678-1234-1234-1234-123456789012",
                "email": "testuser@example.com",
                "email_verified": "true",
                "name": "Test User"
            }
        },
        "response": {}
    }
    
    # Mock context
    class Context:
        function_name = "test-post-auth"
        request_id = "test-request-id"
    
    print("Testing Post-Auth Handler...")
    print(f"Event: {json.dumps(event, indent=2)}")
    
    try:
        result = handler(event, Context())
        print("\n✓ Handler executed successfully")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Verify event is returned unchanged
        assert result == event, "Event must be returned unchanged"
        print("✓ Event returned correctly")
        
        return True
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Post-Auth Lambda Function Test")
    print("=" * 60)
    print("\nNote: This test will attempt to write to DynamoDB.")
    print("Ensure AWS credentials are configured.\n")
    
    success = test_post_auth()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Tests failed")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
