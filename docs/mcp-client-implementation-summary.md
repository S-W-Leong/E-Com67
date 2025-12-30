# MCP Client Implementation Summary

## Issue Discovered

When testing the MCP client example, we discovered that the MCP Gateway does **NOT** expose a standard REST API. The initial implementation incorrectly attempted to use REST endpoints like:
- `GET /mcp/tools` (for discovery)
- `POST /mcp/tools/{tool_name}` (for invocation)

This resulted in **404 errors** with `<UnknownOperationException/>` responses.

## Root Cause

AWS Bedrock AgentCore MCP Gateways implement the **Model Context Protocol (MCP)** using **JSON-RPC 2.0**, not simple HTTP REST APIs. The gateway expects:
- All requests as POST to `/mcp` endpoint
- JSON-RPC 2.0 formatted payloads
- Specific methods: `tools/list` and `tools/call`

## Solution

Updated both the client guide and example script to use the correct JSON-RPC 2.0 protocol.

### Correct Protocol Format

**Tool Discovery (tools/list):**
```json
POST /mcp
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "tools/list"
}
```

**Tool Invocation (tools/call):**
```json
POST /mcp
{
  "jsonrpc": "2.0",
  "id": "request-2",
  "method": "tools/call",
  "params": {
    "name": "order-trends",
    "arguments": {
      "date_from": 1704067200,
      "date_to": 1706745599,
      "group_by": "day"
    }
  }
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "result": {
    "tools": [...]
  }
}
```

## Files Updated

1. **docs/mcp-client-guide.md**
   - Added protocol explanation with JSON-RPC 2.0 format examples
   - Updated Python client to use `_make_request()` method with JSON-RPC
   - Updated JavaScript/TypeScript client to use `makeRequest()` method
   - Updated curl examples to use JSON-RPC format
   - Added note at top explaining the correction

2. **scripts/mcp_client_example.py**
   - Replaced REST API calls with JSON-RPC 2.0 implementation
   - Added `_make_request()` method that constructs JSON-RPC payloads
   - Updated `discover_tools()` to use `tools/list` method
   - Updated `invoke_tool()` to use `tools/call` method
   - Added JSON-RPC error handling

## Key Changes in Python Client

### Before (Incorrect REST API):
```python
def discover_tools(self):
    url = f"{self.gateway_url}/tools"
    response = requests.get(url, headers=self.headers)
    return response.json().get('tools', [])

def invoke_tool(self, tool_name, parameters):
    url = f"{self.gateway_url}/tools/{tool_name}"
    response = requests.post(url, headers=self.headers, json=parameters)
    return response.json()
```

### After (Correct JSON-RPC):
```python
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
        raise Exception(f"MCP Error {result['error']['code']}: {result['error']['message']}")
    
    return result.get("result", {})

def discover_tools(self):
    result = self._make_request("tools/list")
    return result.get('tools', [])

def invoke_tool(self, tool_name, arguments):
    params = {"name": tool_name, "arguments": arguments}
    return self._make_request("tools/call", params)
```

## Testing

To test the corrected client:

```bash
# Get a JWT token
export JWT_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id tvv93rbvv54sjv3ts2fe41dc9 \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Test tool discovery
python scripts/mcp_client_example.py --action discover

# Test tool invocation
python scripts/mcp_client_example.py --action order-trends

# Run all tests
python scripts/mcp_client_example.py --action all
```

## References

- AWS Documentation: [List available tools in an AgentCore gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-list.html)
- AWS Documentation: [Call a tool in an AgentCore gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp-call.html)
- Model Context Protocol Specification: https://modelcontextprotocol.io/

## Lessons Learned

1. **MCP Gateways are NOT REST APIs** - They implement a specific protocol (MCP) using JSON-RPC 2.0
2. **Always check AWS documentation** - The gateway behavior is documented but differs from typical REST patterns
3. **Protocol matters** - Using the wrong protocol results in 404 errors, not authentication or validation errors
4. **JSON-RPC 2.0 is standard** - Many MCP implementations use this protocol for tool communication

## Next Steps

1. Test the corrected client with a valid JWT token
2. Verify tool discovery works correctly
3. Test tool invocation with sample data
4. Document any additional findings or edge cases
5. Consider creating a reusable MCP client library for the project
