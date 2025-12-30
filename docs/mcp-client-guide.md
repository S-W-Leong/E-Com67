# MCP Client Guide: Connecting to Admin Insights Gateway

This guide shows you how to create an MCP (Model Context Protocol) client that connects to the Admin Insights MCP Gateway to invoke analytics tools.

> **Important Update:** This guide has been corrected to use the proper JSON-RPC 2.0 protocol. MCP Gateways do NOT expose REST endpoints like `/tools` or `/tools/{name}`. Instead, they implement the Model Context Protocol using JSON-RPC 2.0 with methods like `tools/list` and `tools/call`.

## Overview

Your MCP Gateway exposes three analytics tools:
- **order-trends** - Analyze order patterns over time
- **sales-insights** - Analyze product sales performance  
- **product-search** - Search products using OpenSearch

**Gateway URL:** `https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp`

## Important: MCP Protocol

The MCP Gateway implements the **Model Context Protocol (MCP)** using **JSON-RPC 2.0**, not a simple REST API. This means:

- All requests are POST requests to the `/mcp` endpoint
- Requests use JSON-RPC 2.0 format with `jsonrpc`, `id`, `method`, and `params` fields
- Two main methods: `tools/list` (discover tools) and `tools/call` (invoke tools)
- Responses follow JSON-RPC 2.0 format with `result` or `error` fields

### JSON-RPC 2.0 Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/list",
  "params": {
    // Optional parameters depending on method
  }
}
```

### JSON-RPC 2.0 Response Format

Success:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    // Method-specific result data
  }
}
```

Error:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

## Authentication

The gateway uses **Custom JWT authentication** with AWS Cognito. You need:
1. A valid Cognito user account
2. A JWT ID token from the Cognito User Pool
3. The token included in the `Authorization: Bearer <token>` header

### Getting a JWT Token

```bash
# Using AWS CLI
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id tvv93rbvv54sjv3ts2fe41dc9 \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

## MCP Client Implementation

### Option 1: Python with requests (JSON-RPC)

Create a simple Python client using the `requests` library with JSON-RPC 2.0 protocol:

```python
#!/usr/bin/env python3
"""
Admin Insights MCP Client

Example client for invoking analytics tools via the MCP Gateway using JSON-RPC 2.0.
"""

import requests
import json
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
    
    # Convenience methods for each tool
    
    def get_order_trends(
        self,
        date_from: int,
        date_to: int,
        group_by: str = 'day',
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get order trends analysis.
        
        Args:
            date_from: Start date as Unix timestamp (seconds)
            date_to: End date as Unix timestamp (seconds)
            group_by: Grouping period ('day', 'week', 'month')
            metrics: List of metrics to calculate
            
        Returns:
            Order trends data
        """
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
        """
        Get sales insights analysis.
        
        Args:
            date_from: Start date as Unix timestamp (seconds)
            date_to: End date as Unix timestamp (seconds)
            category: Optional category filter
            sort_by: Sort by 'revenue', 'units_sold', or 'growth'
            limit: Maximum number of products to return
            
        Returns:
            Sales insights data
        """
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
        """
        Search products.
        
        Args:
            query: Search query string
            category: Optional category filter
            limit: Maximum number of results
            include_inactive: Include inactive products
            
        Returns:
            Product search results
        """
        arguments = {
            'query': query,
            'limit': limit,
            'include_inactive': include_inactive
        }
        
        if category:
            arguments['category'] = category
        
        return self.invoke_tool('product-search', arguments)


# Example usage
def main():
    # Configuration
    GATEWAY_URL = "https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp"
    JWT_TOKEN = "your-jwt-token-here"  # Get from Cognito
    
    # Initialize client
    client = AdminInsightsMCPClient(GATEWAY_URL, JWT_TOKEN)
    
    # Example 1: Discover available tools
    print("Discovering tools...")
    tools = client.discover_tools()
    for tool in tools:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    print()
    
    # Example 2: Get order trends for last 30 days
    print("Getting order trends...")
    now = int(datetime.now().timestamp())
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    
    trends = client.get_order_trends(
        date_from=thirty_days_ago,
        date_to=now,
        group_by='day',
        metrics=['volume', 'revenue']
    )
    print(json.dumps(trends, indent=2))
    print()
    
    # Example 3: Get top selling products
    print("Getting sales insights...")
    insights = client.get_sales_insights(
        date_from=thirty_days_ago,
        date_to=now,
        sort_by='revenue',
        limit=5
    )
    print(json.dumps(insights, indent=2))
    print()
    
    # Example 4: Search for products
    print("Searching products...")
    results = client.search_products(
        query='laptop',
        limit=5
    )
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
```

### Option 2: JavaScript/TypeScript Client (JSON-RPC)

Create a client for Node.js or browser environments using JSON-RPC 2.0:

```typescript
/**
 * Admin Insights MCP Client
 * 
 * TypeScript client for invoking analytics tools via the MCP Gateway using JSON-RPC 2.0.
 */

interface Tool {
  name: string;
  description: string;
  inputSchema: any;
}

interface OrderTrendsParams {
  date_from: number;
  date_to: number;
  group_by?: 'day' | 'week' | 'month';
  metrics?: string[];
}

interface SalesInsightsParams {
  date_from: number;
  date_to: number;
  category?: string;
  sort_by?: 'revenue' | 'units_sold' | 'growth';
  limit?: number;
}

interface ProductSearchParams {
  query: string;
  category?: string;
  limit?: number;
  include_inactive?: boolean;
}

export class AdminInsightsMCPClient {
  private gatewayUrl: string;
  private jwtToken: string;
  private requestCounter: number = 0;

  constructor(gatewayUrl: string, jwtToken: string) {
    this.gatewayUrl = gatewayUrl;
    this.jwtToken = jwtToken;
  }

  private async makeRequest(method: string, params?: any): Promise<any> {
    this.requestCounter++;

    const payload: any = {
      jsonrpc: '2.0',
      id: `request-${this.requestCounter}`,
      method: method
    };

    if (params) {
      payload.params = params;
    }

    const headers = {
      'Authorization': `Bearer ${this.jwtToken}`,
      'Content-Type': 'application/json'
    };

    const response = await fetch(this.gatewayUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`HTTP error (${response.status}): ${error}`);
    }

    const result = await response.json();

    // Check for JSON-RPC error
    if (result.error) {
      throw new Error(`MCP Error ${result.error.code}: ${result.error.message}`);
    }

    return result.result || {};
  }

  /**
   * Discover available tools in the gateway using tools/list method
   */
  async discoverTools(): Promise<Tool[]> {
    const result = await this.makeRequest('tools/list');
    return result.tools || [];
  }

  /**
   * Invoke a specific tool using tools/call method
   */
  async invokeTool(toolName: string, arguments: any): Promise<any> {
    const params = {
      name: toolName,
      arguments: arguments
    };
    return this.makeRequest('tools/call', params);
  }

  /**
   * Get order trends analysis
   */
  async getOrderTrends(params: OrderTrendsParams): Promise<any> {
    return this.invokeTool('order-trends', params);
  }

  /**
   * Get sales insights analysis
   */
  async getSalesInsights(params: SalesInsightsParams): Promise<any> {
    return this.invokeTool('sales-insights', params);
  }

  /**
   * Search products
   */
  async searchProducts(params: ProductSearchParams): Promise<any> {
    return this.invokeTool('product-search', params);
  }
}

// Example usage
async function main() {
  const GATEWAY_URL = 'https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp';
  const JWT_TOKEN = 'your-jwt-token-here'; // Get from Cognito

  const client = new AdminInsightsMCPClient(GATEWAY_URL, JWT_TOKEN);

  try {
    // Discover tools
    console.log('Discovering tools...');
    const tools = await client.discoverTools();
    tools.forEach(tool => {
      console.log(`  - ${tool.name}: ${tool.description || 'No description'}`);
    });

    // Get order trends
    const now = Math.floor(Date.now() / 1000);
    const thirtyDaysAgo = now - (30 * 24 * 60 * 60);

    console.log('\nGetting order trends...');
    const trends = await client.getOrderTrends({
      date_from: thirtyDaysAgo,
      date_to: now,
      group_by: 'day',
      metrics: ['volume', 'revenue']
    });
    console.log(JSON.stringify(trends, null, 2));

    // Get sales insights
    console.log('\nGetting sales insights...');
    const insights = await client.getSalesInsights({
      date_from: thirtyDaysAgo,
      date_to: now,
      sort_by: 'revenue',
      limit: 5
    });
    console.log(JSON.stringify(insights, null, 2));

    // Search products
    console.log('\nSearching products...');
    const results = await client.searchProducts({
      query: 'laptop',
      limit: 5
    });
    console.log(JSON.stringify(results, null, 2));

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}
```

### Option 3: Using curl (JSON-RPC)

Quick testing with curl commands using JSON-RPC 2.0 format:

```bash
# Set your JWT token
export JWT_TOKEN="your-jwt-token-here"
export GATEWAY_URL="https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp"

# Discover tools (tools/list method)
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "list-tools-1",
    "method": "tools/list"
  }'

# Get order trends (tools/call method)
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'

# Get sales insights
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-sales-insights-1",
    "method": "tools/call",
    "params": {
      "name": "sales-insights",
      "arguments": {
        "date_from": 1704067200,
        "date_to": 1706745599,
        "sort_by": "revenue",
        "limit": 10
      }
    }
  }'

# Search products
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-product-search-1",
    "method": "tools/call",
    "params": {
      "name": "product-search",
      "arguments": {
        "query": "laptop",
        "limit": 5
      }
    }
  }'
```

## Integration with AI Agents

### Using with Amazon Bedrock Agents

You can connect your Bedrock Agent to the MCP Gateway:

```python
import boto3

bedrock_agent = boto3.client('bedrock-agent')

# Create action group that uses the MCP Gateway
response = bedrock_agent.create_agent_action_group(
    agentId='your-agent-id',
    agentVersion='DRAFT',
    actionGroupName='AdminInsightsTools',
    actionGroupExecutor={
        'customControl': 'RETURN_CONTROL'  # Or use Lambda
    },
    apiSchema={
        'payload': json.dumps({
            'openapi': '3.0.0',
            'info': {
                'title': 'Admin Insights API',
                'version': '1.0.0'
            },
            'servers': [{
                'url': 'https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp'
            }],
            'paths': {
                '/tools/order-trends': {
                    'post': {
                        'summary': 'Get order trends',
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'date_from': {'type': 'integer'},
                                            'date_to': {'type': 'integer'},
                                            'group_by': {'type': 'string'},
                                            'metrics': {
                                                'type': 'array',
                                                'items': {'type': 'string'}
                                            }
                                        },
                                        'required': ['date_from', 'date_to']
                                    }
                                }
                            }
                        }
                    }
                }
                # Add other tools...
            }
        })
    }
)
```

### Using with LangChain

Integrate with LangChain as a custom tool:

```python
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field

class OrderTrendsInput(BaseModel):
    date_from: int = Field(description="Start date as Unix timestamp")
    date_to: int = Field(description="End date as Unix timestamp")
    group_by: str = Field(default="day", description="Grouping period")

class OrderTrendsTool(BaseTool):
    name = "order_trends"
    description = "Analyze order trends over time including volume and revenue"
    args_schema: Type[BaseModel] = OrderTrendsInput
    
    def __init__(self, mcp_client: AdminInsightsMCPClient):
        super().__init__()
        self.mcp_client = mcp_client
    
    def _run(self, date_from: int, date_to: int, group_by: str = "day") -> str:
        result = self.mcp_client.get_order_trends(
            date_from=date_from,
            date_to=date_to,
            group_by=group_by
        )
        return json.dumps(result)

# Use in LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain.llms import Bedrock

llm = Bedrock(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
mcp_client = AdminInsightsMCPClient(GATEWAY_URL, JWT_TOKEN)

tools = [
    OrderTrendsTool(mcp_client),
    # Add other tools...
]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Use the agent
response = agent.run("What were the order trends for the last 30 days?")
```

## Error Handling

Handle common errors gracefully:

```python
from requests.exceptions import HTTPError

try:
    result = client.get_order_trends(date_from, date_to)
except HTTPError as e:
    if e.response.status_code == 401:
        print("Authentication failed - check your JWT token")
    elif e.response.status_code == 400:
        print(f"Invalid request: {e.response.text}")
    elif e.response.status_code == 500:
        print("Server error - tool execution failed")
    else:
        print(f"Unexpected error: {e}")
```

## Best Practices

1. **Token Management:**
   - Cache JWT tokens (they're valid for 1 hour)
   - Implement automatic token refresh
   - Store tokens securely (never in code)

2. **Error Handling:**
   - Always handle authentication errors (401)
   - Implement retry logic for transient failures
   - Log errors for debugging

3. **Rate Limiting:**
   - Implement client-side rate limiting
   - Use exponential backoff for retries
   - Monitor API usage

4. **Security:**
   - Never expose JWT tokens in logs
   - Use HTTPS only
   - Validate all input parameters

5. **Performance:**
   - Reuse HTTP connections
   - Implement response caching where appropriate
   - Use async/await for concurrent requests

## Testing Your Client

Create a test script:

```python
def test_mcp_client():
    """Test MCP client functionality"""
    client = AdminInsightsMCPClient(GATEWAY_URL, JWT_TOKEN)
    
    # Test 1: Tool discovery
    tools = client.discover_tools()
    assert len(tools) == 3, "Expected 3 tools"
    assert any(t['name'] == 'order-trends' for t in tools)
    
    # Test 2: Order trends
    now = int(datetime.now().timestamp())
    week_ago = now - (7 * 24 * 60 * 60)
    
    trends = client.get_order_trends(week_ago, now)
    assert 'data' in trends or 'results' in trends
    
    # Test 3: Product search
    results = client.search_products('test', limit=1)
    assert 'products' in results or 'results' in results
    
    print("✓ All tests passed!")

if __name__ == '__main__':
    test_mcp_client()
```

## Next Steps

1. **Get a JWT Token:** Use the AWS CLI or Cognito SDK to authenticate
2. **Choose Your Language:** Pick Python, JavaScript, or another language
3. **Implement the Client:** Use the examples above as a starting point
4. **Test the Connection:** Start with tool discovery
5. **Integrate with Your Application:** Add the client to your workflow

## Support

For issues or questions:
- Check the MCP Gateway logs in CloudWatch
- Verify your JWT token is valid
- Ensure your Cognito user has the correct permissions
- Review the tool schemas for correct parameter formats
