#!/usr/bin/env python3
"""
Admin Insights MCP Client Example

This script demonstrates how to connect to the Admin Insights MCP Gateway
and invoke analytics tools using the JSON-RPC 2.0 protocol.

Usage:
    # Set your JWT token
    export JWT_TOKEN="your-jwt-token-here"
    
    # Run the script
    python scripts/mcp_client_example.py
    
    # Or provide token as argument
    python scripts/mcp_client_example.py --token YOUR_TOKEN
"""

import requests
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List


class AdminInsightsMCPClient:
    """Client for Admin Insights MCP Gateway using JSON-RPC 2.0"""
    
    def __init__(self, gateway_url: str, jwt_token: str):
        """
        Initialize the MCP client.
        
        Args:
            gateway_url: MCP Gateway URL (should end with /mcp)
            jwt_token: Cognito JWT ID token
        """
        self.gateway_url = gateway_url
        self.headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }
        self.request_counter = 0
    
    def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a JSON-RPC 2.0 request to the gateway.
        
        Args:
            method: JSON-RPC method (e.g., 'tools/list', 'tools/call')
            params: Method parameters
            
        Returns:
            Response result
        """
        self.request_counter += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": f"request-{self.request_counter}",
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        response = requests.post(
            self.gateway_url,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check for JSON-RPC error
        if "error" in result:
            error = result["error"]
            raise Exception(f"MCP Error {error.get('code')}: {error.get('message')}")
        
        return result.get("result", {})
    
    def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools in the gateway using tools/list method.
        
        Returns:
            List of tool definitions with schemas
        """
        result = self._make_request("tools/list")
        return result.get('tools', [])
    
    def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a specific tool using tools/call method.
        
        Args:
            tool_name: Name of the tool (e.g., 'order-trends')
            arguments: Tool input arguments
            
        Returns:
            Tool execution result
        """
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        
        result = self._make_request("tools/call", params)
        return result
    
    def get_order_trends(
        self,
        date_from: int,
        date_to: int,
        group_by: str = 'day',
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Get order trends analysis"""
        arguments = {
            'date_from': date_from,
            'date_to': date_to,
            'group_by': group_by
        }
        
        if metrics:
            arguments['metrics'] = metrics
        
        return self.invoke_tool('order-trends', arguments)
    
    def get_sales_insights(
        self,
        date_from: int,
        date_to: int,
        category: str = None,
        sort_by: str = 'revenue',
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get sales insights analysis"""
        arguments = {
            'date_from': date_from,
            'date_to': date_to,
            'sort_by': sort_by,
            'limit': limit
        }
        
        if category:
            arguments['category'] = category
        
        return self.invoke_tool('sales-insights', arguments)
    
    def search_products(
        self,
        query: str,
        category: str = None,
        limit: int = 10,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """Search products"""
        arguments = {
            'query': query,
            'limit': limit,
            'include_inactive': include_inactive
        }
        
        if category:
            arguments['category'] = category
        
        return self.invoke_tool('product-search', arguments)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Admin Insights MCP Client Example'
    )
    parser.add_argument(
        '--token',
        help='JWT token (or set JWT_TOKEN environment variable)'
    )
    parser.add_argument(
        '--gateway-url',
        default='https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp',
        help='MCP Gateway URL'
    )
    parser.add_argument(
        '--action',
        choices=['discover', 'order-trends', 'sales-insights', 'product-search', 'all'],
        default='all',
        help='Action to perform'
    )
    
    args = parser.parse_args()
    
    # Get JWT token
    jwt_token = args.token or os.environ.get('JWT_TOKEN')
    if not jwt_token:
        print("Error: JWT token required")
        print()
        print("Provide token via:")
        print("  1. --token argument: python scripts/mcp_client_example.py --token YOUR_TOKEN")
        print("  2. Environment variable: export JWT_TOKEN=YOUR_TOKEN")
        print()
        print("To get a JWT token, run:")
        print("  aws cognito-idp initiate-auth \\")
        print("    --auth-flow USER_PASSWORD_AUTH \\")
        print("    --client-id tvv93rbvv54sjv3ts2fe41dc9 \\")
        print("    --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \\")
        print("    --region ap-southeast-1 \\")
        print("    --query 'AuthenticationResult.IdToken' \\")
        print("    --output text")
        sys.exit(1)
    
    print("=" * 80)
    print("Admin Insights MCP Client Example")
    print("=" * 80)
    print()
    print(f"Gateway URL: {args.gateway_url}")
    print(f"Token: {jwt_token[:20]}...{jwt_token[-20:]}")
    print()
    print("Using JSON-RPC 2.0 protocol for MCP Gateway communication")
    print()
    
    # Initialize client
    client = AdminInsightsMCPClient(args.gateway_url, jwt_token)
    
    try:
        # Action 1: Discover tools
        if args.action in ['discover', 'all']:
            print("-" * 80)
            print("DISCOVERING TOOLS (tools/list method)")
            print("-" * 80)
            
            tools = client.discover_tools()
            print(f"Found {len(tools)} tools:")
            print()
            
            for tool in tools:
                print(f"Tool: {tool['name']}")
                print(f"  Description: {tool.get('description', 'No description')}")
                if 'inputSchema' in tool:
                    print(f"  Input Schema: {json.dumps(tool['inputSchema'], indent=4)}")
                print()
        
        # Calculate date range (last 30 days)
        now = int(datetime.now().timestamp())
        thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
        
        # Action 2: Get order trends
        if args.action in ['order-trends', 'all']:
            print("-" * 80)
            print("ORDER TRENDS (tools/call method)")
            print("-" * 80)
            
            trends = client.get_order_trends(
                date_from=thirty_days_ago,
                date_to=now,
                group_by='day',
                metrics=['volume', 'revenue']
            )
            
            print(json.dumps(trends, indent=2))
            print()
        
        # Action 3: Get sales insights
        if args.action in ['sales-insights', 'all']:
            print("-" * 80)
            print("SALES INSIGHTS (tools/call method)")
            print("-" * 80)
            
            insights = client.get_sales_insights(
                date_from=thirty_days_ago,
                date_to=now,
                sort_by='revenue',
                limit=5
            )
            
            print(json.dumps(insights, indent=2))
            print()
        
        # Action 4: Search products
        if args.action in ['product-search', 'all']:
            print("-" * 80)
            print("PRODUCT SEARCH (tools/call method)")
            print("-" * 80)
            
            results = client.search_products(
                query='laptop',
                limit=5
            )
            
            print(json.dumps(results, indent=2))
            print()
        
        print("=" * 80)
        print("SUCCESS - All operations completed")
        print("=" * 80)
        
    except requests.exceptions.HTTPError as e:
        print()
        print("=" * 80)
        print("HTTP ERROR")
        print("=" * 80)
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        print()
        
        if e.response.status_code == 401:
            print("Authentication failed - check your JWT token")
            print("Token may be expired (tokens are valid for 1 hour)")
        elif e.response.status_code == 400:
            print("Invalid request - check your parameters")
        elif e.response.status_code == 500:
            print("Server error - tool execution failed")
        
        sys.exit(1)
        
    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR")
        print("=" * 80)
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
