#!/usr/bin/env python3
"""
MCP Gateway Verification Script

Verifies that the MCP Gateway is working correctly by testing:
- Gateway status and availability
- Tool discovery
- Tool invocation
- Authentication enforcement

Usage:
    python scripts/verify_mcp_gateway.py --check-status
    python scripts/verify_mcp_gateway.py --test-discovery
    python scripts/verify_mcp_gateway.py --test-tool order_trends
    python scripts/verify_mcp_gateway.py --test-auth
    python scripts/verify_mcp_gateway.py --run-all
"""

import boto3
import argparse
import sys
import json
import time
import requests
from datetime import datetime, timedelta


def get_gateway_info(region: str = "ap-southeast-1") -> dict:
    """
    Get MCP Gateway information.
    
    Args:
        region: AWS region
        
    Returns:
        Gateway details or None if not found
    """
    print("Retrieving MCP Gateway information...")
    
    try:
        control_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # List all gateways
        response = control_client.list_gateways()
        
        # Find admin insights gateway
        for gateway_summary in response.get('items', []):
            if gateway_summary.get('name') == 'admin-insights-mcp-gateway':
                # Get full gateway details
                gateway_response = control_client.get_gateway(
                    gatewayIdentifier=gateway_summary['gatewayId']
                )
                
                print(f"✓ Found gateway: {gateway_response['gatewayId']}")
                print(f"  Status: {gateway_response['status']}")
                print(f"  URL: {gateway_response['gatewayUrl']}")
                
                return gateway_response
        
        print("✗ Admin Insights MCP Gateway not found")
        return None
        
    except Exception as e:
        print(f"✗ Error retrieving gateway: {str(e)}")
        return None


def list_gateway_tools(gateway_id: str, region: str = "ap-southeast-1") -> list:
    """
    List all tools registered in the gateway.
    
    Args:
        gateway_id: Gateway ID
        region: AWS region
        
    Returns:
        List of registered tools
    """
    print("\nListing registered tools...")
    
    try:
        control_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        response = control_client.list_gateway_targets(gatewayIdentifier=gateway_id)
        targets = response.get('items', [])
        
        print(f"✓ Found {len(targets)} registered tools:")
        for target in targets:
            print(f"  - {target['name']} (Status: {target['status']})")
        
        return targets
        
    except Exception as e:
        print(f"✗ Error listing tools: {str(e)}")
        return []


def get_cognito_token(region: str = "ap-southeast-1") -> str:
    """
    Get a JWT token from Cognito for testing.
    
    This is a simplified version - in production, you'd use proper authentication.
    
    Args:
        region: AWS region
        
    Returns:
        JWT token or None
    """
    print("\nGetting Cognito JWT token...")
    
    try:
        # Get user pool ID from environment or CloudFormation
        cfn_client = boto3.client('cloudformation', region_name=region)
        
        user_pool_id = None
        client_id = None
        
        paginator = cfn_client.get_paginator('list_exports')
        for page in paginator.paginate():
            for export in page.get('Exports', []):
                if export['Name'] == 'E-Com67-UserPoolId':
                    user_pool_id = export['Value']
                elif export['Name'] == 'E-Com67-UserPoolClientId':
                    client_id = export['Value']
        
        if not user_pool_id or not client_id:
            print("✗ Could not find Cognito User Pool configuration")
            print("  Please provide credentials manually for testing")
            return None
        
        print(f"  User Pool ID: {user_pool_id}")
        print(f"  Client ID: {client_id}")
        print()
        print("  Note: This script cannot automatically authenticate.")
        print("  Please use AWS CLI or Cognito console to get a token:")
        print()
        print("  aws cognito-idp initiate-auth \\")
        print("    --auth-flow USER_PASSWORD_AUTH \\")
        print(f"    --client-id {client_id} \\")
        print("    --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \\")
        print(f"    --region {region} \\")
        print("    --query 'AuthenticationResult.IdToken' \\")
        print("    --output text")
        print()
        
        return None
        
    except Exception as e:
        print(f"✗ Error getting token: {str(e)}")
        return None


def test_tool_discovery(gateway_url: str, token: str = None) -> bool:
    """
    Test tool discovery endpoint.
    
    Args:
        gateway_url: Gateway URL
        token: JWT token (optional for testing)
        
    Returns:
        True if successful
    """
    print("\nTesting tool discovery...")
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Call discovery endpoint
        discovery_url = f"{gateway_url}/tools"
        print(f"  GET {discovery_url}")
        
        response = requests.get(discovery_url, headers=headers, timeout=10)
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            tools = response.json().get('tools', [])
            print(f"✓ Tool discovery successful! Found {len(tools)} tools:")
            
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
            
            # Verify expected tools
            tool_names = [t['name'] for t in tools]
            expected_tools = ['order_trends', 'sales_insights', 'product_search']
            
            missing = set(expected_tools) - set(tool_names)
            if missing:
                print(f"✗ Missing expected tools: {', '.join(missing)}")
                return False
            
            return True
        elif response.status_code == 401:
            print("✗ Authentication required (401 Unauthorized)")
            print("  This is expected if no token provided")
            return False
        else:
            print(f"✗ Tool discovery failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing discovery: {str(e)}")
        return False


def test_tool_invocation(
    gateway_url: str,
    tool_name: str,
    token: str = None
) -> bool:
    """
    Test invoking a specific tool.
    
    Args:
        gateway_url: Gateway URL
        tool_name: Name of tool to test
        token: JWT token (optional for testing)
        
    Returns:
        True if successful
    """
    print(f"\nTesting tool invocation: {tool_name}")
    
    # Sample parameters for each tool
    sample_params = {
        "order_trends": {
            "date_from": int((datetime.now() - timedelta(days=30)).timestamp()),
            "date_to": int(datetime.now().timestamp()),
            "group_by": "day",
            "metrics": ["volume", "revenue"]
        },
        "sales_insights": {
            "date_from": int((datetime.now() - timedelta(days=30)).timestamp()),
            "date_to": int(datetime.now().timestamp()),
            "sort_by": "revenue",
            "limit": 10
        },
        "product_search": {
            "query": "laptop",
            "limit": 5
        }
    }
    
    if tool_name not in sample_params:
        print(f"✗ Unknown tool: {tool_name}")
        return False
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Call tool endpoint
        tool_url = f"{gateway_url}/tools/{tool_name}"
        params = sample_params[tool_name]
        
        print(f"  POST {tool_url}")
        print(f"  Parameters: {json.dumps(params, indent=2)}")
        
        response = requests.post(
            tool_url,
            headers=headers,
            json=params,
            timeout=30
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Tool invocation successful!")
            print(f"  Response: {json.dumps(result, indent=2)[:200]}...")
            return True
        elif response.status_code == 401:
            print("✗ Authentication required (401 Unauthorized)")
            print("  Provide a valid JWT token to test tool invocation")
            return False
        else:
            print(f"✗ Tool invocation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing tool: {str(e)}")
        return False


def test_authentication(gateway_url: str) -> bool:
    """
    Test authentication enforcement.
    
    Args:
        gateway_url: Gateway URL
        
    Returns:
        True if authentication is properly enforced
    """
    print("\nTesting authentication enforcement...")
    
    try:
        # Test 1: No token (should fail)
        print("\n  Test 1: Request without token")
        response = requests.get(
            f"{gateway_url}/tools",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 401:
            print("  ✓ Correctly rejected (401)")
        else:
            print(f"  ✗ Expected 401, got {response.status_code}")
            return False
        
        # Test 2: Invalid token (should fail)
        print("\n  Test 2: Request with invalid token")
        response = requests.get(
            f"{gateway_url}/tools",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid.token.here"
            },
            timeout=10
        )
        
        if response.status_code == 401:
            print("  ✓ Correctly rejected (401)")
        else:
            print(f"  ✗ Expected 401, got {response.status_code}")
            return False
        
        print("\n✓ Authentication is properly enforced!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing authentication: {str(e)}")
        return False


def check_status(region: str) -> bool:
    """Check gateway status and configuration"""
    print("=" * 80)
    print("MCP GATEWAY STATUS CHECK")
    print("=" * 80)
    print()
    
    gateway = get_gateway_info(region)
    
    if not gateway:
        print("\n✗ Gateway not found or not accessible")
        print("\nTo create the gateway, run:")
        print("  python scripts/create_mcp_gateway.py")
        return False
    
    if gateway['status'] != 'READY':
        print(f"\n✗ Gateway is not ready (status: {gateway['status']})")
        return False
    
    # List tools
    tools = list_gateway_tools(gateway['gatewayId'], region)
    
    if len(tools) < 3:
        print(f"\n✗ Expected 3 tools, found {len(tools)}")
        print("\nTo register tools, run:")
        print(f"  python scripts/register_mcp_tools.py --gateway-id {gateway['gatewayId']}")
        return False
    
    print("\n✓ Gateway is ready and properly configured!")
    return True


def run_all_tests(region: str, token: str = None) -> bool:
    """Run all verification tests"""
    print("=" * 80)
    print("MCP GATEWAY VERIFICATION - FULL TEST SUITE")
    print("=" * 80)
    print()
    
    # Get gateway info
    gateway = get_gateway_info(region)
    if not gateway:
        return False
    
    if gateway['status'] != 'READY':
        print(f"\n✗ Gateway is not ready (status: {gateway['status']})")
        return False
    
    gateway_url = gateway['gatewayUrl']
    
    # Run tests
    results = []
    
    # Test 1: Tool discovery
    results.append(("Tool Discovery", test_tool_discovery(gateway_url, token)))
    
    # Test 2: Authentication
    results.append(("Authentication", test_authentication(gateway_url)))
    
    # Test 3: Tool invocations (if token provided)
    if token:
        results.append(("Order Trends Tool", test_tool_invocation(gateway_url, "order_trends", token)))
        results.append(("Sales Insights Tool", test_tool_invocation(gateway_url, "sales_insights", token)))
        results.append(("Product Search Tool", test_tool_invocation(gateway_url, "product_search", token)))
    else:
        print("\n⚠ Skipping tool invocation tests (no token provided)")
        print("  To test tool invocation, provide a JWT token:")
        print("  python scripts/verify_mcp_gateway.py --run-all --token YOUR_TOKEN")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    
    return all_passed


def main():
    """Main script function"""
    parser = argparse.ArgumentParser(
        description='Verify MCP Gateway functionality'
    )
    parser.add_argument(
        '--region',
        default='ap-southeast-1',
        help='AWS region (default: ap-southeast-1)'
    )
    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Check gateway status and configuration'
    )
    parser.add_argument(
        '--test-discovery',
        action='store_true',
        help='Test tool discovery endpoint'
    )
    parser.add_argument(
        '--test-tool',
        choices=['order_trends', 'sales_insights', 'product_search'],
        help='Test specific tool invocation'
    )
    parser.add_argument(
        '--test-auth',
        action='store_true',
        help='Test authentication enforcement'
    )
    parser.add_argument(
        '--run-all',
        action='store_true',
        help='Run all verification tests'
    )
    parser.add_argument(
        '--token',
        help='JWT token for authenticated requests'
    )
    
    args = parser.parse_args()
    
    # If no specific test specified, show help
    if not any([args.check_status, args.test_discovery, args.test_tool, 
                args.test_auth, args.run_all]):
        parser.print_help()
        sys.exit(0)
    
    success = True
    
    if args.check_status:
        success = check_status(args.region) and success
    
    if args.run_all:
        success = run_all_tests(args.region, args.token) and success
    else:
        # Get gateway for individual tests
        gateway = get_gateway_info(args.region)
        if not gateway:
            sys.exit(1)
        
        gateway_url = gateway['gatewayUrl']
        
        if args.test_discovery:
            success = test_tool_discovery(gateway_url, args.token) and success
        
        if args.test_tool:
            success = test_tool_invocation(gateway_url, args.test_tool, args.token) and success
        
        if args.test_auth:
            success = test_authentication(gateway_url) and success
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
