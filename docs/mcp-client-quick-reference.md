# MCP Client Quick Reference

## Gateway Information

- **Gateway ID:** `admin-insights-mcp-gateway-aegvgncuq6`
- **Gateway URL:** `https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp`
- **Protocol:** JSON-RPC 2.0 (Model Context Protocol)
- **Authentication:** JWT Bearer token from Cognito

## Available Tools

1. **order-trends** - Analyze order patterns over time
2. **sales-insights** - Analyze product sales performance
3. **product-search** - Search products using OpenSearch

## Quick Start

### Get JWT Token
```bash
export JWT_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id tvv93rbvv54sjv3ts2fe41dc9 \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text)
```

### Python Client
```python
from scripts.mcp_client_example import AdminInsightsMCPClient

client = AdminInsightsMCPClient(
    gateway_url="https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp",
    jwt_token=JWT_TOKEN
)

# Discover tools
tools = client.discover_tools()

# Get order trends
trends = client.get_order_trends(
    date_from=1704067200,
    date_to=1706745599,
    group_by='day'
)
```

### curl Commands

**Discover Tools:**
```bash
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list"}'
```

**Call Tool:**
```bash
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/call",
    "params": {
      "name": "order-trends",
      "arguments": {
        "date_from": 1704067200,
        "date_to": 1706745599,
        "group_by": "day"
      }
    }
  }'
```

## JSON-RPC 2.0 Format

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "unique-id",
  "method": "tools/list | tools/call",
  "params": { /* optional */ }
}
```

### Response (Success)
```json
{
  "jsonrpc": "2.0",
  "id": "unique-id",
  "result": { /* data */ }
}
```

### Response (Error)
```json
{
  "jsonrpc": "2.0",
  "id": "unique-id",
  "error": {
    "code": -32600,
    "message": "Error message"
  }
}
```

## Common Mistakes

❌ **WRONG:**
```python
# Don't use REST API patterns
requests.get(f"{gateway_url}/tools")
requests.post(f"{gateway_url}/tools/order-trends", json=params)
```

✅ **CORRECT:**
```python
# Use JSON-RPC 2.0
payload = {"jsonrpc": "2.0", "id": "1", "method": "tools/list"}
requests.post(gateway_url, json=payload)
```

## Testing Scripts

```bash
# View correct format examples
python scripts/test_mcp_jsonrpc.py

# Test client (requires JWT token)
python scripts/mcp_client_example.py --action discover
python scripts/mcp_client_example.py --action all
```

## Documentation

- **Full Guide:** `docs/mcp-client-guide.md`
- **Implementation Details:** `docs/mcp-client-implementation-summary.md`
- **Correction Summary:** `docs/mcp-client-correction-summary.md`
- **This Quick Reference:** `docs/mcp-client-quick-reference.md`

## Tool Parameters

### order-trends
```json
{
  "date_from": 1704067200,      // Unix timestamp (required)
  "date_to": 1706745599,        // Unix timestamp (required)
  "group_by": "day",            // "day" | "week" | "month"
  "metrics": ["volume", "revenue"]  // Optional array
}
```

### sales-insights
```json
{
  "date_from": 1704067200,      // Unix timestamp (required)
  "date_to": 1706745599,        // Unix timestamp (required)
  "category": "Electronics",    // Optional string
  "sort_by": "revenue",         // "revenue" | "units_sold" | "growth"
  "limit": 10                   // Optional integer
}
```

### product-search
```json
{
  "query": "laptop",            // Search query (required)
  "category": "Electronics",    // Optional string
  "limit": 10,                  // Optional integer
  "include_inactive": false     // Optional boolean
}
```

## Error Codes

- **401** - Authentication failed (invalid or expired JWT token)
- **400** - Invalid request (malformed JSON-RPC or invalid parameters)
- **404** - Tool not found (wrong tool name)
- **500** - Tool execution error (internal error)

## Support

For issues:
1. Check JWT token is valid (tokens expire after 1 hour)
2. Verify JSON-RPC format is correct
3. Check CloudWatch logs for gateway errors
4. Review tool parameter schemas
