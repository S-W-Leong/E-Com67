import boto3
import requests
import json
import os 
from dotenv import load_dotenv

# Initialize Cognito client
cognito = boto3.client('cognito-idp', region_name='us-east-1')

# Your values from CDK outputs
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID')
API_ENDPOINT = os.getenv('API_GATEWAY_ENDPOINT')

def signup_user(email, password):
    """Sign up a new user"""
    try:
        response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email}
            ]
        )
        print(f"✅ User signed up: {email}")
        return response
    except cognito.exceptions.UsernameExistsException:
        print(f"⚠️  User already exists: {email}")

def confirm_user(email):
    """Admin confirm user (skip email verification)"""
    try:
        cognito.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=email
        )
        print(f"✅ User confirmed: {email}")
    except Exception as e:
        print(f"❌ Confirm failed: {e}")

def login_user(email, password):
    """Login and get JWT token"""
    try:
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        id_token = response['AuthenticationResult']['IdToken']
        print(f"✅ Login successful. Token: {id_token[:50]}...")
        return id_token
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

def test_protected_endpoint(id_token, endpoint, method='GET', data=None):
    """Test an API endpoint with JWT token"""
    headers = {
        'Authorization': f'Bearer {id_token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{API_ENDPOINT}{endpoint}"
    
    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers, json=data)
    
    print(f"\n{method} {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response

def test_public_endpoint(endpoint):
    """Test public endpoint without auth"""
    url = f"{API_ENDPOINT}{endpoint}"
    response = requests.get(url)
    print(f"\nGET {endpoint} (no auth)")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response

# ========================================
# Test Flow
# ========================================

if __name__ == "__main__":
    # 1. Create test user
    test_email = "testuser@example.com"
    test_password = "Test1234"
    
    signup_user(test_email, test_password)
    confirm_user(test_email)
    
    # 2. Login and get token
    id_token = login_user(test_email, test_password)
    
    if id_token:
        # 3. Test public endpoint (no auth)
        test_public_endpoint('/products')
        
        # 4. Test protected endpoints (with auth)
        test_protected_endpoint(id_token, '/cart', method='GET')
        
        test_protected_endpoint(id_token, '/cart', method='POST', data={
            'productId': 'prod-123',
            'quantity': 2
        })
        
        test_protected_endpoint(id_token, '/cart', method='GET')
        
        # 5. Test without token (should fail)
        print("\n❌ Testing without token (should get 401):")
        response = requests.get(f"{API_ENDPOINT}/cart")
        print(f"Status: {response.status_code}")