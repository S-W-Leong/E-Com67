#!/usr/bin/env python3
"""
Quick test to demonstrate JSON-RPC 2.0 format for MCP Gateway

This script shows the correct request format without actually calling the gateway.
"""

import json

# Example 1: Tool Discovery Request
discovery_request = {
    "jsonrpc": "2.0",
    "id": "list-tools-1",
    "method": "tools/list"
}

print("=" * 80)
print("TOOL DISCOVERY REQUEST (tools/list)")
print("=" * 80)
print("POST https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp")
print("Authorization: Bearer <JWT_TOKEN>")
print("Content-Type: application/json")
print()
print(json.dumps(discovery_request, indent=2))
print()

# Example 2: Tool Invocation Request
invocation_request = {
    "jsonrpc": "2.0",
    "id": "call-order-trends-1",
    "method": "tools/call",
    "params": {
        "name": "order-trends",
        "arguments": {
            "date_from": 1704067200,
            "date_to": 1706745599,
            "group_by": "day",
            "metrics": ["volume", "revenue"]
        }
    }
}

print("=" * 80)
print("TOOL INVOCATION REQUEST (tools/call)")
print("=" * 80)
print("POST https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp")
print("Authorization: Bearer <JWT_TOKEN>")
print("Content-Type: application/json")
print()
print(json.dumps(invocation_request, indent=2))
print()

# Example 3: Expected Success Response
success_response = {
    "jsonrpc": "2.0",
    "id": "list-tools-1",
    "result": {
        "tools": [
            {
                "name": "order-trends",
                "description": "Analyze order trends over time",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "integer"},
                        "date_to": {"type": "integer"},
                        "group_by": {"type": "string"}
                    },
                    "required": ["date_from", "date_to"]
                }
            }
        ]
    }
}

print("=" * 80)
print("EXPECTED SUCCESS RESPONSE")
print("=" * 80)
print(json.dumps(success_response, indent=2))
print()

# Example 4: Expected Error Response
error_response = {
    "jsonrpc": "2.0",
    "id": "call-order-trends-1",
    "error": {
        "code": -32600,
        "message": "Invalid Request"
    }
}

print("=" * 80)
print("EXPECTED ERROR RESPONSE")
print("=" * 80)
print(json.dumps(error_response, indent=2))
print()

print("=" * 80)
print("KEY DIFFERENCES FROM REST API")
print("=" * 80)
print()
print("❌ WRONG (REST API - returns 404):")
print("   GET /mcp/tools")
print("   POST /mcp/tools/order-trends")
print()
print("✓ CORRECT (JSON-RPC 2.0):")
print("   POST /mcp with method='tools/list'")
print("   POST /mcp with method='tools/call'")
print()
