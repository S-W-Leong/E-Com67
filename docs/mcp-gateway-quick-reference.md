# MCP Gateway Quick Reference

## Setup Commands

```bash
# 1. Create MCP Gateway
python scripts/create_mcp_gateway.py --region ap-southeast-1

# 2. Register Tools (use gateway ID from step 1)
python scripts/register_mcp_tools.py --gateway-id <GATEWAY_ID> --region ap-southeast-1
```

## Authentication

```bash
# Get JWT token from Cognito
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <CLIENT_ID> \
  --auth-parameters USERNAME=<USERNAME>,PASSWORD=<PASSWORD> \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text)
```

## Tool Discovery

```bash
# List available tools
curl -X GET <GATEWAY_URL>/tools \
  -H "Authorization: Bearer $TOKEN"
```

## Tool Invocation Examples

### Order Trends

```bash
curl -X POST <GATEWAY_URL>/tools/order_trends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "group_by": "day",
    "metrics": ["volume", "revenue"]
  }'
```

### Sales Insights

```bash
curl -X POST <GATEWAY_URL>/tools/sales_insights \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "sort_by": "revenue",
    "limit": 10
  }'
```

### Product Search

```bash
curl -X POST <GATEWAY_URL>/tools/product_search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless headphones",
    "limit": 5
  }'
```

## Common Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| 401 | Invalid/expired token | Get fresh JWT token |
| 400 | Invalid parameters | Check tool schema |
| 404 | Tool not found | Verify tool name |
| 429 | Rate limit exceeded | Wait and retry |
| 500 | Internal error | Check CloudWatch logs |

## Monitoring

```bash
# View gateway logs
aws logs tail /aws/bedrock/agentcore/gateway/<GATEWAY_ID> --follow

# View tool logs
aws logs tail /aws/lambda/e-com67-admin-insights-order-trends --follow
```

## Tool Schemas

### order_trends
- **Required**: date_from, date_to
- **Optional**: group_by ("day"|"week"|"month"), metrics (array)

### sales_insights
- **Required**: date_from, date_to
- **Optional**: category, sort_by, limit, low_performer_threshold

### product_search
- **Required**: query
- **Optional**: category, limit, include_inactive

## Rate Limits

- **Default**: 100 requests/minute
- **Burst**: 200 requests

## Support

- **Logs**: CloudWatch Logs
- **Metrics**: CloudWatch Metrics
- **Docs**: `docs/mcp-gateway-setup.md`
