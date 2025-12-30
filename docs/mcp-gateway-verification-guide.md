# MCP Gateway Verification Guide

This guide explains how to verify that the MCP Gateway is working correctly for the Admin Insights Agent.

## Prerequisites

1. Admin Insights Stack deployed
2. MCP Gateway created (via `scripts/create_mcp_gateway.py`)
3. Tools registered (via `scripts/register_mcp_tools.py`)
4. Valid Cognito credentials for authentication

## Verification Steps

### Step 1: Check Gateway Status

First, verify the gateway exists and is active:

```bash
python scripts/verify_mcp_gateway.py --check-status
```

This will:
- List all MCP gateways
- Show gateway status (should be ACTIVE)
- Display gateway URL
- List registered tools

### Step 2: Test Tool Discovery

Test that external systems can discover available tools:

```bash
python scripts/verify_mcp_gateway.py --test-discovery
```

This will:
- Authenticate with Cognito
- Call the gateway's tool discovery endpoint
- Verify all three tools are listed (order_trends, sales_insights, product_search)
- Display tool schemas

Expected output:
```json
{
  "tools": [
    {
      "name": "order_trends",
      "description": "Analyze order trends over time...",
      "inputSchema": { ... }
    },
    {
      "name": "sales_insights",
      "description": "Analyze product sales performance...",
      "inputSchema": { ... }
    },
    {
      "name": "product_search",
      "description": "Search products using OpenSearch...",
      "inputSchema": { ... }
    }
  ]
}
```

### Step 3: Test Tool Invocation

Test invoking each tool through the gateway:

```bash
# Test order trends tool
python scripts/verify_mcp_gateway.py --test-tool order_trends

# Test sales insights tool
python scripts/verify_mcp_gateway.py --test-tool sales_insights

# Test product search tool
python scripts/verify_mcp_gateway.py --test-tool product_search
```

This will:
- Authenticate with Cognito
- Invoke the specified tool with sample parameters
- Display the response
- Verify response format

### Step 4: Test Authentication

Test that authentication is properly enforced:

```bash
python scripts/verify_mcp_gateway.py --test-auth
```

This will:
- Test with valid token (should succeed)
- Test with invalid token (should fail with 401)
- Test with expired token (should fail with 401)
- Test with no token (should fail with 401)

### Step 5: Manual Testing with curl

You can also test manually using curl:

#### Get JWT Token

```bash
# Using AWS CLI to get token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=YourPassword \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

#### Test Tool Discovery

```bash
curl -X GET "https://GATEWAY_URL/tools" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

#### Test Tool Invocation

```bash
# Order Trends
curl -X POST "https://GATEWAY_URL/tools/order_trends" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "group_by": "day",
    "metrics": ["volume", "revenue"]
  }'

# Sales Insights
curl -X POST "https://GATEWAY_URL/tools/sales_insights" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "sort_by": "revenue",
    "limit": 10
  }'

# Product Search
curl -X POST "https://GATEWAY_URL/tools/product_search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "laptop",
    "limit": 5
  }'
```

## Expected Responses

### Successful Tool Invocation

```json
{
  "tool": "order_trends",
  "result": {
    "time_series": [...],
    "summary": {...},
    "status_breakdown": {...}
  },
  "status": "success",
  "timestamp": 1704067200
}
```

### Authentication Error

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token",
    "timestamp": 1704067200
  }
}
```

### Tool Execution Error

```json
{
  "tool": "order_trends",
  "error": {
    "code": "TOOL_EXECUTION_ERROR",
    "message": "Failed to query DynamoDB",
    "details": "..."
  },
  "status": "error",
  "timestamp": 1704067200
}
```

## Troubleshooting

### Gateway Not Found

**Problem**: Gateway doesn't exist or can't be found

**Solution**:
```bash
# Create the gateway
python scripts/create_mcp_gateway.py --region ap-southeast-1

# Register tools
python scripts/register_mcp_tools.py --gateway-id GATEWAY_ID
```

### Gateway Not Active

**Problem**: Gateway status is CREATING or FAILED

**Solution**:
- Wait a few minutes for CREATING status
- Check CloudWatch logs for errors
- Verify IAM role has correct permissions
- Delete and recreate if FAILED

### Authentication Fails

**Problem**: 401 Unauthorized errors

**Solution**:
- Verify JWT token is valid and not expired
- Check token is from correct Cognito User Pool
- Verify user has admin permissions
- Check Authorization header format: `Bearer <token>`

### Tool Not Found

**Problem**: Tool not listed in discovery or 404 on invocation

**Solution**:
```bash
# Re-register tools
python scripts/register_mcp_tools.py --gateway-id GATEWAY_ID
```

### Tool Execution Fails

**Problem**: Tool returns error or times out

**Solution**:
- Check Lambda function logs in CloudWatch
- Verify Lambda has correct permissions
- Test Lambda function directly
- Check DynamoDB/OpenSearch connectivity

## Monitoring

### CloudWatch Metrics

Monitor these metrics for the MCP Gateway:

- `GatewayInvocations` - Total gateway calls
- `GatewayErrors` - Failed gateway calls
- `GatewayLatency` - Response time
- `AuthenticationFailures` - Failed auth attempts

### CloudWatch Logs

Check these log groups:

- `/aws/lambda/admin-insights-order-trends` - Order trends tool logs
- `/aws/lambda/admin-insights-sales-insights` - Sales insights tool logs
- `/aws/lambda/admin-insights-product-search` - Product search tool logs
- `/aws/bedrock/agentcore/gateway/GATEWAY_ID` - Gateway logs

## Integration Testing

For automated integration testing, run:

```bash
python -m pytest tests/test_mcp_gateway_integration.py -v
```

This will test:
- Gateway status and availability
- Tool discovery
- Tool invocation with valid inputs
- Authentication enforcement
- Error handling
- Response format validation

## Next Steps

Once verification is complete:

1. Document the gateway URL for external systems
2. Provide authentication instructions to external teams
3. Set up monitoring and alerting
4. Create API documentation for external consumers
5. Implement rate limiting if needed
