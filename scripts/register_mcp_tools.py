#!/usr/bin/env python3
"""
Admin Insights Agent MCP Tool Registration Script

Registers analytics tools as targets in the MCP Gateway.
This enables external systems to discover and invoke the tools via the gateway.

Tools registered:
1. Order Trends Tool - Analyze order patterns over time
2. Sales Insights Tool - Analyze product sales performance
3. Product Search Tool - Search products using OpenSearch

Usage:
    python scripts/register_mcp_tools.py --gateway-id GATEWAY_ID [--region REGION]

The script will:
1. Retrieve Lambda function ARNs from CloudFormation exports
2. Define tool schemas with input/output specifications
3. Register each tool as a gateway target
4. Verify registration and output tool discovery information
"""

import boto3
import argparse
import sys
import json
from datetime import datetime


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


def get_tool_schemas() -> dict:
    """
    Define tool schemas for all analytics tools.
    
    These schemas describe the input parameters and purpose of each tool,
    enabling external systems to discover and use them correctly.
    
    Returns:
        Dictionary mapping tool names to their schemas
    """
    return {
        "order_trends": {
            "name": "order_trends",
            "description": "Analyze order trends over time including volume, revenue, status distribution, and growth rates. "
                          "Supports grouping by day, week, or month for time-series analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "integer",
                        "description": "Start date as Unix timestamp in seconds (e.g., 1704067200 for 2024-01-01)"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date as Unix timestamp in seconds (e.g., 1706745599 for 2024-01-31)"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["day", "week", "month"],
                        "description": "Time period grouping for aggregation",
                        "default": "day"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["volume", "revenue", "status_distribution"]
                        },
                        "description": "Metrics to calculate (volume=order count, revenue=total sales, status_distribution=order status breakdown)",
                        "default": ["volume", "revenue"]
                    }
                },
                "required": ["date_from", "date_to"]
            }
        },
        "sales_insights": {
            "name": "sales_insights",
            "description": "Analyze product sales performance including top sellers, revenue by product, category performance, "
                          "and low performers. Provides actionable insights for inventory and marketing decisions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "integer",
                        "description": "Start date as Unix timestamp in seconds"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "End date as Unix timestamp in seconds"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional filter by product category (e.g., 'Electronics', 'Clothing')"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["revenue", "units_sold", "growth"],
                        "description": "Sort products by revenue, units sold, or growth rate",
                        "default": "revenue"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of products to return (1-100)",
                        "default": 10
                    },
                    "low_performer_threshold": {
                        "type": "number",
                        "description": "Revenue threshold for identifying low performers. If not provided, uses bottom 10% of products."
                    }
                },
                "required": ["date_from", "date_to"]
            }
        },
        "product_search": {
            "name": "product_search",
            "description": "Search products using OpenSearch with fuzzy matching for typo tolerance. "
                          "Searches across product name, description, tags, brand, and SKU. "
                          "Supports category filtering and active/inactive product filtering.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (e.g., 'wireless headphones', 'laptop', 'nike shoes')",
                        "minLength": 1
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional filter by product category"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of results to return (1-100)",
                        "default": 10
                    },
                    "include_inactive": {
                        "type": "boolean",
                        "description": "Include inactive products in search results",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        }
    }


def register_tool(
    control_client,
    gateway_id: str,
    tool_name: str,
    tool_schema: dict,
    lambda_arn: str
) -> dict:
    """
    Register an analytics tool as a gateway target.
    
    Args:
        control_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway ID
        tool_name: Name of the tool
        tool_schema: Tool schema with name, description, and inputSchema
        lambda_arn: Lambda function ARN
        
    Returns:
        Target registration response
    """
    print(f"\nRegistering tool: {tool_name}")
    print(f"  Description: {tool_schema['description'][:80]}...")
    print(f"  Lambda ARN: {lambda_arn}")
    
    try:
        response = control_client.create_gateway_target(
            gatewayId=gateway_id,
            name=tool_name,
            description=tool_schema['description'],
            targetType="LAMBDA",
            targetConfiguration={
                "lambdaTarget": {
                    "lambdaArn": lambda_arn
                }
            },
            toolSchema={
                "name": tool_schema['name'],
                "description": tool_schema['description'],
                "inputSchema": tool_schema['inputSchema']
            }
        )
        
        target_id = response['target']['id']
        print(f"✓ Tool registered successfully!")
        print(f"  Target ID: {target_id}")
        print(f"  Status: {response['target']['status']}")
        
        return response['target']
        
    except Exception as e:
        print(f"✗ Error registering tool {tool_name}: {str(e)}")
        raise


def list_registered_tools(control_client, gateway_id: str) -> list:
    """
    List all tools registered in the gateway.
    
    Args:
        control_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway ID
        
    Returns:
        List of registered targets
    """
    print("\nListing registered tools...")
    
    try:
        response = control_client.list_gateway_targets(gatewayId=gateway_id)
        targets = response.get('targets', [])
        
        print(f"✓ Found {len(targets)} registered tools")
        
        for target in targets:
            print(f"  - {target['name']} (ID: {target['id']}, Status: {target['status']})")
        
        return targets
        
    except Exception as e:
        print(f"✗ Error listing tools: {str(e)}")
        return []


def verify_gateway_status(control_client, gateway_id: str) -> bool:
    """
    Verify that the gateway is active and ready.
    
    Args:
        control_client: Boto3 bedrock-agentcore-control client
        gateway_id: Gateway ID
        
    Returns:
        True if gateway is active, False otherwise
    """
    print(f"\nVerifying gateway status...")
    
    try:
        response = control_client.get_gateway(gatewayId=gateway_id)
        gateway = response['gateway']
        
        status = gateway['status']
        print(f"  Gateway Status: {status}")
        
        if status == 'ACTIVE':
            print("✓ Gateway is active and ready")
            return True
        else:
            print(f"✗ Gateway is not active (status: {status})")
            return False
            
    except Exception as e:
        print(f"✗ Error verifying gateway: {str(e)}")
        return False


def main():
    """Main script function"""
    parser = argparse.ArgumentParser(
        description='Register analytics tools in MCP Gateway'
    )
    parser.add_argument(
        '--gateway-id',
        required=True,
        help='MCP Gateway ID (from create_mcp_gateway.py output)'
    )
    parser.add_argument(
        '--region',
        default='ap-southeast-1',
        help='AWS region (default: ap-southeast-1)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Admin Insights Agent MCP Tool Registration")
    print("=" * 70)
    print()
    print(f"Gateway ID: {args.gateway_id}")
    print(f"Region: {args.region}")
    print()
    
    # Initialize boto3 client
    control_client = boto3.client('bedrock-agentcore-control', region_name=args.region)
    
    # Verify gateway is active
    if not verify_gateway_status(control_client, args.gateway_id):
        print("\n✗ Gateway is not ready. Please wait for it to become active.")
        sys.exit(1)
    
    # Get Lambda ARNs
    lambda_arns = get_lambda_arns(args.region)
    
    # Get tool schemas
    tool_schemas = get_tool_schemas()
    
    # Register each tool
    print("\n" + "=" * 70)
    print("Registering Analytics Tools")
    print("=" * 70)
    
    registered_tools = []
    
    for tool_name, lambda_arn in lambda_arns.items():
        if tool_name in tool_schemas:
            try:
                target = register_tool(
                    control_client,
                    args.gateway_id,
                    tool_name,
                    tool_schemas[tool_name],
                    lambda_arn
                )
                registered_tools.append(target)
            except Exception as e:
                print(f"\n✗ Failed to register {tool_name}: {str(e)}")
                print("  Continuing with remaining tools...")
    
    # List all registered tools
    print("\n" + "=" * 70)
    print("Registration Complete!")
    print("=" * 70)
    
    all_targets = list_registered_tools(control_client, args.gateway_id)
    
    print()
    print("Summary:")
    print(f"  Successfully registered: {len(registered_tools)} tools")
    print(f"  Total tools in gateway: {len(all_targets)}")
    print()
    print("Next Steps:")
    print("1. External systems can now discover tools via:")
    print(f"   GET <gateway-url>/tools")
    print()
    print("2. Invoke tools via:")
    print(f"   POST <gateway-url>/tools/<tool-name>")
    print("   Headers: Authorization: Bearer <jwt-token>")
    print("   Body: JSON matching tool's inputSchema")
    print()
    print("3. Example tool invocation:")
    print("   curl -X POST <gateway-url>/tools/order_trends \\")
    print("     -H 'Authorization: Bearer <token>' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"date_from\": 1704067200, \"date_to\": 1706745599, \"group_by\": \"day\"}'")
    print()


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
