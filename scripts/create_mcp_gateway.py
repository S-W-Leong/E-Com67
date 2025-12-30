#!/usr/bin/env python3
"""
Admin Insights Agent MCP Gateway Initialization Script

Creates a Model Context Protocol (MCP) Gateway for the Admin Insights Agent.
This gateway exposes analytics tools to external systems via authenticated API.

The MCP Gateway provides:
- JWT authentication with Cognito
- Tool discovery endpoint
- Tool invocation routing
- Rate limiting and security

Usage:
    python scripts/create_mcp_gateway.py [--region REGION] [--force]

The script will:
1. Create an MCP Gateway with JWT authentication
2. Register analytics tools as gateway targets
3. Output the gateway URL and ID for external system integration
"""

import boto3
import argparse
import sys
import time
import json
from datetime import datetime


def get_cognito_user_pool_id(region: str = "ap-southeast-1") -> str:
    """
    Get the Cognito User Pool ID from CloudFormation exports.
    
    Args:
        region: AWS region
        
    Returns:
        User Pool ID
    """
    print("Retrieving Cognito User Pool ID...")
    
    try:
        cfn_client = boto3.client('cloudformation', region_name=region)
        
        # Get exports from CloudFormation
        paginator = cfn_client.get_paginator('list_exports')
        
        for page in paginator.paginate():
            for export in page.get('Exports', []):
                if export['Name'] == 'E-Com67-UserPoolId':
                    user_pool_id = export['Value']
                    print(f"✓ Found User Pool ID: {user_pool_id}")
                    return user_pool_id
        
        print("✗ User Pool ID not found in CloudFormation exports")
        print("  Make sure the DataStack is deployed with the User Pool export")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Error retrieving User Pool ID: {str(e)}")
        sys.exit(1)


def get_lambda_arns(region: str = "ap-southeast-1") -> dict:
    """
    Get Lambda function ARNs from CloudFormation exports.
    
    Args:
        region: AWS region
        
    Returns:
        Dictionary mapping tool names to Lambda ARNs
    """
    print("Retrieving Lambda function ARNs...")
    
    try:
        cfn_client = boto3.client('cloudformation', region_name=region)
        
        # Get exports from CloudFormation
        paginator = cfn_client.get_paginator('list_exports')
        
        lambda_arns = {}
        required_exports = {
            'E-Com67-AdminInsightsOrderTrendsLambdaArn': 'order_trends',
            'E-Com67-AdminInsightsSalesInsightsLambdaArn': 'sales_insights',
            'E-Com67-AdminInsightsProductSearchLambdaArn': 'product_search'
        }
        
        for page in paginator.paginate():
            for export in page.get('Exports', []):
                export_name = export['Name']
                if export_name in required_exports:
                    tool_name = required_exports[export_name]
                    lambda_arns[tool_name] = export['Value']
                    print(f"✓ Found {tool_name}: {export['Value']}")
        
        # Verify all required ARNs were found
        if len(lambda_arns) != len(required_exports):
            missing = set(required_exports.values()) - set(lambda_arns.keys())
            print(f"✗ Missing Lambda ARNs: {', '.join(missing)}")
            print("  Make sure the AdminInsightsStack is deployed")
            sys.exit(1)
        
        return lambda_arns
        
    except Exception as e:
        print(f"✗ Error retrieving Lambda ARNs: {str(e)}")
        sys.exit(1)


def get_mcp_gateway_role_arn(region: str = "ap-southeast-1") -> str:
    """
    Get the MCP Gateway IAM role ARN from CloudFormation exports.
    
    Args:
        region: AWS region
        
    Returns:
        IAM role ARN
    """
    print("Retrieving MCP Gateway IAM role ARN...")
    
    try:
        cfn_client = boto3.client('cloudformation', region_name=region)
        
        # Get exports from CloudFormation
        paginator = cfn_client.get_paginator('list_exports')
        
        for page in paginator.paginate():
            for export in page.get('Exports', []):
                if export['Name'] == 'E-Com67-AdminInsightsMCPGatewayRoleArn':
                    role_arn = export['Value']
                    print(f"✓ Found MCP Gateway Role ARN: {role_arn}")
                    return role_arn
        
        print("✗ MCP Gateway Role ARN not found in CloudFormation exports")
        print("  Make sure the AdminInsightsStack is deployed")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Error retrieving MCP Gateway Role ARN: {str(e)}")
        sys.exit(1)


def get_cognito_client_id(region: str = "ap-southeast-1") -> str:
    """
    Get the Cognito User Pool Client ID from CloudFormation exports.
    
    Args:
        region: AWS region
        
    Returns:
        Client ID
    """
    print("Retrieving Cognito Client ID...")
    
    try:
        cfn_client = boto3.client('cloudformation', region_name=region)
        
        # Get exports from CloudFormation
        paginator = cfn_client.get_paginator('list_exports')
        
        for page in paginator.paginate():
            for export in page.get('Exports', []):
                if export['Name'] == 'E-Com67-UserPoolClientId':
                    client_id = export['Value']
                    print(f"✓ Found Client ID: {client_id}")
                    return client_id
        
        print("✗ Client ID not found in CloudFormation exports")
        print("  Make sure the DataStack is deployed with the Client ID export")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Error retrieving Client ID: {str(e)}")
        sys.exit(1)


def create_gateway(
    region: str,
    user_pool_id: str,
    client_id: str,
    role_arn: str
) -> dict:
    """
    Create MCP Gateway with JWT authentication.
    
    Args:
        region: AWS region
        user_pool_id: Cognito User Pool ID for JWT validation
        client_id: Cognito Client ID for allowed clients
        role_arn: IAM role ARN for gateway execution
        
    Returns:
        Gateway details including gateway ID and URL
    """
    print(f"\nCreating MCP Gateway in region: {region}")
    
    try:
        # Initialize boto3 client for Bedrock AgentCore Control
        control_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # Construct Cognito OIDC discovery URL
        cognito_issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        discovery_url = f"{cognito_issuer}/.well-known/openid-configuration"
        
        print(f"  Using Cognito issuer: {cognito_issuer}")
        print(f"  Discovery URL: {discovery_url}")
        print(f"  Allowed Client ID: {client_id}")
        
        # Create MCP Gateway
        gateway_response = control_client.create_gateway(
            name="admin-insights-mcp-gateway",
            description="MCP Gateway for Admin Insights Agent analytics tools. "
                       "Provides authenticated access to order trends, sales insights, and product search.",
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": discovery_url,
                    "allowedClients": [client_id]  # Specify the Cognito client ID
                }
            }
        )
        
        gateway_id = gateway_response['gateway']['id']
        gateway_url = gateway_response['gateway']['gatewayUrl']
        
        print(f"✓ Gateway created successfully!")
        print(f"  Gateway ID: {gateway_id}")
        print(f"  Gateway URL: {gateway_url}")
        print(f"  Status: {gateway_response['gateway']['status']}")
        
        # Wait for gateway to become active
        print("\nWaiting for gateway to become ACTIVE...")
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = control_client.get_gateway(gatewayId=gateway_id)
                status = status_response['gateway']['status']
                
                if status == 'ACTIVE':
                    print("✓ Gateway is now ACTIVE")
                    break
                elif status in ['FAILED', 'DELETING', 'DELETED']:
                    print(f"✗ Gateway creation failed with status: {status}")
                    sys.exit(1)
                else:
                    print(f"  Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                    attempt += 1
                    
            except Exception as e:
                print(f"  Error checking status: {str(e)}")
                time.sleep(2)
                attempt += 1
        
        if attempt >= max_attempts:
            print("✗ Timeout waiting for gateway to become active")
            sys.exit(1)
        
        return gateway_response['gateway']
        
    except Exception as e:
        print(f"✗ Error creating gateway: {str(e)}")
        sys.exit(1)


def get_existing_gateway(region: str = "ap-southeast-1") -> dict:
    """
    Check if a gateway with the same name already exists.
    
    Args:
        region: AWS region to check
        
    Returns:
        Existing gateway details if found, None otherwise
    """
    control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    try:
        # List all gateways
        response = control_client.list_gateways()
        
        # Look for existing gateway with the same name
        for gateway_summary in response.get('items', []):
            if gateway_summary.get('name') == 'admin-insights-mcp-gateway':
                # Get full gateway details
                gateway_response = control_client.get_gateway(
                    gatewayIdentifier=gateway_summary['gatewayId']
                )
                return gateway_response
                
    except Exception as e:
        print(f"Warning: Error checking for existing gateway: {str(e)}")
        
    return None


def register_tool_target(
    control_client,
    gateway_id: str,
    tool_name: str,
    tool_description: str,
    lambda_arn: str,
    input_schema: dict
) -> dict:
    """
    Register an analytics tool as a gateway target.
    
    Args:
        control_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway ID
        tool_name: Name of the tool
        tool_description: Description of the tool
        lambda_arn: Lambda function ARN
        input_schema: JSON schema for tool input
        
    Returns:
        Target registration response
    """
    print(f"\nRegistering tool: {tool_name}")
    print(f"  Lambda ARN: {lambda_arn}")
    
    try:
        response = control_client.create_gateway_target(
            gatewayId=gateway_id,
            name=tool_name,
            description=tool_description,
            targetType="LAMBDA",
            targetConfiguration={
                "lambdaTarget": {
                    "lambdaArn": lambda_arn
                }
            },
            toolSchema={
                "name": tool_name,
                "description": tool_description,
                "inputSchema": input_schema
            }
        )
        
        target_id = response['target']['id']
        print(f"✓ Tool registered successfully!")
        print(f"  Target ID: {target_id}")
        
        return response['target']
        
    except Exception as e:
        print(f"✗ Error registering tool {tool_name}: {str(e)}")
        raise


def main():
    """Main script function"""
    parser = argparse.ArgumentParser(
        description='Create MCP Gateway for Admin Insights Agent'
    )
    parser.add_argument(
        '--region',
        default='ap-southeast-1',
        help='AWS region for the gateway (default: ap-southeast-1)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force creation even if gateway already exists'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Admin Insights Agent MCP Gateway Initialization")
    print("=" * 70)
    print()
    
    # Check for existing gateway
    if not args.force:
        print("Checking for existing gateway...")
        existing_gateway = get_existing_gateway(args.region)
        
        if existing_gateway:
            print("✓ Gateway already exists!")
            print(f"  Gateway ID: {existing_gateway['gatewayId']}")
            print(f"  Gateway URL: {existing_gateway['gatewayUrl']}")
            print(f"  Status: {existing_gateway['status']}")
            print(f"  Created: {existing_gateway.get('createdAt', 'N/A')}")
            print()
            print("Use this Gateway URL for external system integration:")
            print(f"  {existing_gateway['gatewayUrl']}")
            print()
            print("To create a new gateway, use the --force flag")
            return
        else:
            print("No existing gateway found. Creating new gateway...")
            print()
    
    # Get required resources
    user_pool_id = get_cognito_user_pool_id(args.region)
    client_id = get_cognito_client_id(args.region)
    lambda_arns = get_lambda_arns(args.region)
    role_arn = get_mcp_gateway_role_arn(args.region)
    
    # Create gateway
    gateway = create_gateway(args.region, user_pool_id, client_id, role_arn)
    gateway_id = gateway['id']
    
    print()
    print("=" * 70)
    print("Gateway Creation Complete!")
    print("=" * 70)
    print()
    print("Gateway Details:")
    print(f"  Gateway ID: {gateway_id}")
    print(f"  Gateway URL: {gateway['gatewayUrl']}")
    print()
    print("Next Steps:")
    print("1. Run the tool registration script to register analytics tools:")
    print(f"   python scripts/register_mcp_tools.py --gateway-id {gateway_id}")
    print()
    print("2. External systems can now access tools via:")
    print(f"   {gateway['gatewayUrl']}")
    print()
    print("3. Authentication:")
    print("   - Obtain JWT token from Cognito User Pool")
    print("   - Include in Authorization header: Bearer <token>")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)
