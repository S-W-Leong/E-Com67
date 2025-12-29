#!/usr/bin/env python3
"""
Test script to send a WebSocket message to the Admin Insights Agent.

This script simulates what the frontend does:
1. Gets a Cognito token
2. Connects to the WebSocket API
3. Sends a test message
4. Receives and prints the response
"""

import json
import asyncio
import websockets
import boto3
from botocore.exceptions import ClientError

# Get WebSocket URL from CloudFormation exports
def get_websocket_url():
    """Get WebSocket URL from CloudFormation exports"""
    cf = boto3.client('cloudformation', region_name='ap-southeast-1')
    
    try:
        response = cf.list_exports()
        for export in response['Exports']:
            if export['Name'] == 'E-Com67-AdminInsightsWebSocketURL':
                return export['Value']
        
        raise ValueError("WebSocket URL export not found")
    except ClientError as e:
        print(f"Error getting WebSocket URL: {e}")
        raise

# Get Cognito token
def get_cognito_token():
    """Get Cognito ID token for authentication"""
    # This is a placeholder - in real usage, you'd authenticate with Cognito
    # For now, we'll just print instructions
    print("To get a token:")
    print("1. Open the admin dashboard in your browser")
    print("2. Open browser DevTools > Application > Local Storage")
    print("3. Find the Cognito token (look for keys containing 'idToken')")
    print("4. Copy the token value")
    print()
    token = input("Paste your Cognito ID token here: ")
    return token.strip()

async def test_websocket():
    """Test WebSocket connection and message sending"""
    
    # Get WebSocket URL
    ws_url = get_websocket_url()
    print(f"WebSocket URL: {ws_url}")
    
    # Get token
    token = get_cognito_token()
    
    # Connect with token
    url_with_token = f"{ws_url}?token={token}"
    
    print("\nConnecting to WebSocket...")
    
    try:
        async with websockets.connect(url_with_token) as websocket:
            print("✓ Connected!")
            
            # Send a test message
            test_message = {
                "action": "sendMessage",
                "message": "What are the top selling products this month?",
                "timestamp": 1234567890
            }
            
            print(f"\nSending message: {test_message['message']}")
            await websocket.send(json.dumps(test_message))
            print("✓ Message sent!")
            
            # Receive responses
            print("\nWaiting for responses...")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    
                    print(f"\n[{data.get('type', 'unknown')}] {data.get('content', '')}")
                    
                    if data.get('type') == 'complete':
                        print("\n✓ Response complete!")
                        break
                    elif data.get('type') == 'error':
                        print(f"\n✗ Error: {data.get('content')}")
                        break
                        
                except asyncio.TimeoutError:
                    print("\n✗ Timeout waiting for response")
                    break
                    
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
