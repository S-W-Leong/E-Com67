# MCP Client Correction Summary

## Problem

The initial MCP client implementation used incorrect REST API patterns that resulted in 404 errors when attempting to interact with the MCP Gateway.

**Error Encountered:**
```
404 Not Found
<UnknownOperationException/>
```

**Incorrect Approach:**
```python
# ❌ WRONG - Treating MCP Gateway as REST API
url = f"{gateway_url}/tools"
response = requests.get(url, headers=headers)

url = f"{gateway_url}/tools/{tool_name}"
response = requests.post(url, headers=headers, json=parameters)
```

## Root Cause

AWS Bedrock AgentCore MCP Gateways implement the **Model Context Protocol (MCP)** using **JSON-RPC 2.0**, not standard REST APIs. The gateway does not expose endpoints like `/tools` or `/tools/{name}`.

## Solution

Updated the client implementation to use the correct JSON-RPC 2.0 protocol with proper methods:
- `tools/list` - Discover available tools
- `tools/call` - Invoke a specific tool

**Correct Approach:**
```python
# ✓ CORRECT - Using JSON-RPC 2.0
def _make_request(self, method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": f"request-{self.request_counter}",
        "method": method
    }
    if params:
        payload["params"] = params
    
    response = requests.post(self.gateway_url, headers=self.headers, json=payload)
    result = response.json()
    
    if "error" in result:
        raise Exception(f"MCP Error: {result['error']['message']}")
    
    return result.get("result", {})

# Tool discovery
result = self._make_request("tools/list")

# Tool invocation
params = {"name": "order-trends", "arguments": {...}}
result = self._make_request("tools/call", params)
```

## Files Updated

### 1. docs/mcp-client-guide.md
- Added protocol explanation section with JSON-RPC 2.0 format
- Updated Python client implementation with `_make_request()` method
- Updated JavaScript/TypeScript client with `makeRequest()` method
- Updated curl examples to use JSON-RPC format
- Added warning note at top about the correction

### 2. scripts/mcp_client_example.py
- Replaced REST API calls with JSON-RPC 2.0 implementation
- Added `_make_request()` helper method
- Updated `discover_tools()` to use `tools/list` method
- Updated `invoke_tool()` to use `tools/call` method
- Added JSON-RPC error handling
- Updated output messages to indicate JSON-RPC usage

### 3. New Documentation Files
- `docs/mcp-client-implementation-summary.md` - Detailed technical summary
- `docs/mcp-client-correction-summary.md` - This file
- `scripts/test_mcp_jsonrpc.py` - Demonstration script showing correct format

## JSON-RPC 2.0 Format

### Request Structure
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/list",
  "params": {
    // Optional method-specific parameters
  }
}
```

### Response Structure (Success)
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    // Method-specific result data
  }
}
```

### Response Structure (Error)
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

## Testing

To test the corrected implementation:

```bash
# 1. Get a JWT token from Cognito
export JWT_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id tvv93rbvv54sjv3ts2fe41dc9 \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# 2. Test tool discovery
python scripts/mcp_client_example.py --action discover

# 3. Test tool invocation
python scripts/mcp_client_example.py --action order-trends

# 4. Run all tests
python scripts/mcp_client_example.py --action all

# 5. View correct format examples
python scripts/test_mcp_jsonrpc.py
```

## curl Examples

### Tool Discovery
```bash
curl -X POST "https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "list-tools-1",
    "method": "tools/list"
  }'
```

### Tool Invocation
```bash
curl -X POST "https://admin-insights-mcp-gateway-aegvgncuq6.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp" \
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
```

## Key Takeaways

1. **MCP Gateways ≠ REST APIs** - They implement a specific protocol (MCP) using JSON-RPC 2.0
2. **All requests go to `/mcp` endpoint** - No separate paths for different operations
3. **Method determines operation** - Use `tools/list` or `tools/call` in the JSON-RPC method field
4. **Parameters go in params object** - Not in URL path or query string
5. **Always check for JSON-RPC errors** - Response may contain `error` instead of `result`

## References

- [AWS Docs: List available tools in an AgentCore gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-list.html)
- [AWS Docs: Call a tool in an AgentCore gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-call.html)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

## Status

✅ **COMPLETE** - MCP client guide and example script have been corrected to use proper JSON-RPC 2.0 protocol.

## Next Steps

1. Test the corrected client with a valid JWT token
2. Verify tool discovery returns expected tools
3. Test tool invocation with real data
4. Consider creating a reusable MCP client library
5. Update any other documentation that references the MCP Gateway
