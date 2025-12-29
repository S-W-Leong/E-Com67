# Admin Insights Agent MCP Gateway Setup Guide

## Overview

The Model Context Protocol (MCP) Gateway provides authenticated external access to the Admin Insights Agent's analytics tools. External systems can discover and invoke tools via a secure REST API with JWT authentication.

## Architecture

```
┌─────────────────────┐
│  External System    │
│  (Third-party App)  │
└──────────┬──────────┘
           │ HTTPS + JWT
           ▼
┌─────────────────────────────────────┐
│      MCP Gateway                     │
│  - JWT Authentication (Cognito)     │
│  - Tool Discovery                   │
│  - Request Routing                  │
│  - Rate Limiting                    │
└──────────┬──────────────────────────┘
           │
           ├──────────────┬──────────────┬──────────────┐
           │              │              │              │
           ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Order   │   │  Sales   │   │ Product  │   │  Future  │
    │  Trends  │   │ Insights │   │  Search  │   │  Tools   │
    │  Lambda  │   │  Lambda  │   │  Lambda  │   │          │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

## Prerequisites

Before setting up the MCP Gateway, ensure:

1. **AdminInsightsStack is deployed**:
   ```bash
   cdk deploy AdminInsightsStack
   ```

2. **Cognito User Pool is configured** (from DataStack)

3. **Analytics tool Lambdas are deployed**:
   - Order Trends Tool
   - Sales Insights Tool
   - Product Search Tool

## Setup Instructions

### Step 1: Create MCP Gateway

Run the gateway creation script:

```bash
python scripts/create_mcp_gateway.py --region ap-southeast-1
```

This script will:
- Retrieve Cognito User Pool ID from CloudFormation exports
- Retrieve Lambda function ARNs for analytics tools
- Create MCP Gateway with JWT authentication
- Wait for gateway to become ACTIVE
- Output gateway ID and URL

**Output Example**:
```
======================================================================
Gateway Creation Complete!
======================================================================

Gateway Details:
  Gateway ID: gw-abc123xyz
  Gateway URL: https://abc123.execute-api.ap-southeast-1.amazonaws.com/prod

Next Steps:
1. Run the tool registration script to register analytics tools:
   python scripts/register_mcp_tools.py --gateway-id gw-abc123xyz
```

**Save the Gateway ID** - you'll need it for the next step.

### Step 2: Register Analytics Tools

Register the analytics tools as gateway targets:

```bash
python scripts/register_mcp_tools.py --gateway-id <GATEWAY_ID> --region ap-southeast-1
```

This script will:
- Retrieve Lambda ARNs from CloudFormation exports
- Define tool schemas with input/output specifications
- Register each tool as a gateway target
- Verify registration

**Output Example**:
```
======================================================================
Registration Complete!
======================================================================

Listing registered tools...
✓ Found 3 registered tools
  - order_trends (ID: tgt-123, Status: ACTIVE)
  - sales_insights (ID: tgt-456, Status: ACTIVE)
  - product_search (ID: tgt-789, Status: ACTIVE)

Summary:
  Successfully registered: 3 tools
  Total tools in gateway: 3
```

### Step 3: Test Gateway Access

Test the gateway by discovering available tools:

```bash
# Get JWT token from Cognito (replace with your user pool details)
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <CLIENT_ID> \
  --auth-parameters USERNAME=<USERNAME>,PASSWORD=<PASSWORD> \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Discover available tools
curl -X GET <GATEWAY_URL>/tools \
  -H "Authorization: Bearer $TOKEN"
```

## Available Tools

### 1. Order Trends Tool

**Purpose**: Analyze order patterns over time including volume, revenue, status distribution, and growth rates.

**Endpoint**: `POST <gateway-url>/tools/order_trends`

**Input Schema**:
```json
{
  "date_from": 1704067200,      // Unix timestamp (required)
  "date_to": 1706745599,        // Unix timestamp (required)
  "group_by": "day",            // "day" | "week" | "month" (optional, default: "day")
  "metrics": ["volume", "revenue"]  // Array of metrics (optional)
}
```

**Example Request**:
```bash
curl -X POST <gateway-url>/tools/order_trends \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "group_by": "day",
    "metrics": ["volume", "revenue", "status_distribution"]
  }'
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "time_series": [
      {
        "period": "2024-01-01",
        "timestamp": 1704067200,
        "order_count": 45,
        "total_revenue": 12500.50,
        "average_order_value": 277.79
      }
    ],
    "summary": {
      "total_orders": 450,
      "total_revenue": 125000.00,
      "average_order_value": 277.78
    },
    "status_breakdown": {
      "pending": 10,
      "processing": 25,
      "shipped": 200,
      "delivered": 200,
      "cancelled": 15
    },
    "growth_rate": 15.5
  }
}
```

### 2. Sales Insights Tool

**Purpose**: Analyze product sales performance including top sellers, revenue by product, and category performance.

**Endpoint**: `POST <gateway-url>/tools/sales_insights`

**Input Schema**:
```json
{
  "date_from": 1704067200,      // Unix timestamp (required)
  "date_to": 1706745599,        // Unix timestamp (required)
  "category": "Electronics",    // Optional category filter
  "sort_by": "revenue",         // "revenue" | "units_sold" | "growth" (optional)
  "limit": 10,                  // Max products to return (optional, default: 10)
  "low_performer_threshold": 100.0  // Revenue threshold (optional)
}
```

**Example Request**:
```bash
curl -X POST <gateway-url>/tools/sales_insights \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": 1704067200,
    "date_to": 1706745599,
    "sort_by": "revenue",
    "limit": 5
  }'
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "top_products": [
      {
        "product_id": "prod-123",
        "product_name": "Wireless Headphones",
        "category": "Electronics",
        "units_sold": 150,
        "total_revenue": 15000.00,
        "average_price": 100.00,
        "order_count": 120
      }
    ],
    "category_performance": {
      "Electronics": {
        "totalRevenue": 50000.00,
        "unitsSold": 500,
        "orderCount": 300,
        "productCount": 25
      }
    },
    "low_performers": [],
    "insights": [
      "Top product: 'Wireless Headphones' generated $15,000.00 in revenue with 150 units sold",
      "Best performing category: 'Electronics' with $50,000.00 in revenue"
    ],
    "summary": {
      "total_revenue": 125000.00,
      "total_units_sold": 1500,
      "unique_products_sold": 75
    }
  }
}
```

### 3. Product Search Tool

**Purpose**: Search products using OpenSearch with fuzzy matching for typo tolerance.

**Endpoint**: `POST <gateway-url>/tools/product_search`

**Input Schema**:
```json
{
  "query": "wireless headphones",  // Search query (required)
  "category": "Electronics",       // Optional category filter
  "limit": 10,                     // Max results (optional, default: 10)
  "include_inactive": false        // Include inactive products (optional)
}
```

**Example Request**:
```bash
curl -X POST <gateway-url>/tools/product_search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless headphones",
    "limit": 5
  }'
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "products": [
      {
        "product_id": "prod-123",
        "name": "Premium Wireless Headphones",
        "description": "High-quality wireless headphones with noise cancellation",
        "category": "Electronics",
        "price": 99.99,
        "stock": 50,
        "is_active": true,
        "sku": "WH-001",
        "brand": "AudioTech",
        "tags": ["wireless", "bluetooth", "noise-cancelling"],
        "relevance_score": 15.5
      }
    ],
    "total_results": 12,
    "query": "wireless headphones",
    "filters_applied": {
      "category": null,
      "include_inactive": false
    }
  }
}
```

## Authentication

### JWT Token Requirements

The MCP Gateway uses JWT tokens from the Cognito User Pool for authentication.

**Token Requirements**:
- Must be a valid JWT token from the configured Cognito User Pool
- Must not be expired
- Must be included in the `Authorization` header as `Bearer <token>`

### Obtaining a JWT Token

#### Option 1: Using AWS CLI

```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <CLIENT_ID> \
  --auth-parameters USERNAME=<USERNAME>,PASSWORD=<PASSWORD> \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text)
```

#### Option 2: Using AWS SDK (Python)

```python
import boto3

cognito_client = boto3.client('cognito-idp', region_name='ap-southeast-1')

response = cognito_client.initiate_auth(
    AuthFlow='USER_PASSWORD_AUTH',
    ClientId='<CLIENT_ID>',
    AuthParameters={
        'USERNAME': '<USERNAME>',
        'PASSWORD': '<PASSWORD>'
    }
)

token = response['AuthenticationResult']['IdToken']
```

#### Option 3: Using AWS SDK (JavaScript)

```javascript
import { CognitoIdentityProviderClient, InitiateAuthCommand } from "@aws-sdk/client-cognito-identity-provider";

const client = new CognitoIdentityProviderClient({ region: "ap-southeast-1" });

const command = new InitiateAuthCommand({
  AuthFlow: "USER_PASSWORD_AUTH",
  ClientId: "<CLIENT_ID>",
  AuthParameters: {
    USERNAME: "<USERNAME>",
    PASSWORD: "<PASSWORD>"
  }
});

const response = await client.send(command);
const token = response.AuthenticationResult.IdToken;
```

## Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid or expired JWT token"
}
```

**Causes**:
- Missing Authorization header
- Invalid JWT token
- Expired JWT token
- Token from wrong Cognito User Pool

**Solution**: Obtain a fresh JWT token from Cognito

#### 400 Bad Request
```json
{
  "error": "VALIDATION_ERROR",
  "message": "date_to must be greater than or equal to date_from"
}
```

**Causes**:
- Invalid input parameters
- Missing required fields
- Invalid data types

**Solution**: Check tool schema and correct input parameters

#### 404 Not Found
```json
{
  "error": "TOOL_NOT_FOUND",
  "message": "Tool 'invalid_tool' not found"
}
```

**Causes**:
- Invalid tool name in URL
- Tool not registered in gateway

**Solution**: Use tool discovery endpoint to get valid tool names

#### 500 Internal Server Error
```json
{
  "error": "INTERNAL_ERROR",
  "message": "An unexpected error occurred"
}
```

**Causes**:
- Lambda execution error
- DynamoDB/OpenSearch connection issues
- Timeout

**Solution**: Check CloudWatch logs for detailed error information

## Rate Limiting

The MCP Gateway implements rate limiting to prevent abuse:

- **Default Limit**: 100 requests per minute per client
- **Burst Limit**: 200 requests

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

## Monitoring and Logging

### CloudWatch Logs

Gateway logs are available in CloudWatch Logs:

```bash
# View gateway logs
aws logs tail /aws/bedrock/agentcore/gateway/<GATEWAY_ID> --follow

# View tool invocation logs
aws logs tail /aws/lambda/e-com67-admin-insights-order-trends --follow
aws logs tail /aws/lambda/e-com67-admin-insights-sales-insights --follow
aws logs tail /aws/lambda/e-com67-admin-insights-product-search --follow
```

### CloudWatch Metrics

Monitor gateway performance:

```bash
# View gateway invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/BedrockAgentCore \
  --metric-name Invocations \
  --dimensions Name=GatewayId,Value=<GATEWAY_ID> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Troubleshooting

### Gateway Not Found

**Problem**: `Gateway with ID 'gw-xyz' not found`

**Solution**:
1. Verify gateway was created successfully
2. Check gateway ID is correct
3. Ensure you're using the correct AWS region

### Tool Registration Failed

**Problem**: `Error registering tool: AccessDeniedException`

**Solution**:
1. Verify MCP Gateway IAM role has Lambda invoke permissions
2. Check Lambda function ARNs are correct
3. Ensure AdminInsightsStack is deployed

### Authentication Failed

**Problem**: `401 Unauthorized` when invoking tools

**Solution**:
1. Verify JWT token is valid and not expired
2. Check token is from the correct Cognito User Pool
3. Ensure Authorization header format is correct: `Bearer <token>`

### Tool Invocation Timeout

**Problem**: `504 Gateway Timeout`

**Solution**:
1. Check Lambda function timeout settings (default: 30s)
2. Verify DynamoDB/OpenSearch connectivity
3. Review CloudWatch logs for Lambda errors

## Security Best Practices

1. **Token Management**:
   - Never hardcode JWT tokens
   - Implement token refresh logic
   - Store tokens securely (e.g., environment variables, secrets manager)

2. **Network Security**:
   - Use HTTPS only
   - Implement IP whitelisting if possible
   - Monitor for suspicious activity

3. **Access Control**:
   - Use least-privilege IAM roles
   - Regularly rotate credentials
   - Audit access logs

4. **Data Protection**:
   - Validate all input parameters
   - Sanitize output data
   - Implement request/response logging

## Next Steps

1. **Add More Tools**: Register additional analytics tools as needed
2. **Implement Client SDK**: Create SDK for your programming language
3. **Set Up Monitoring**: Configure CloudWatch alarms for errors and latency
4. **Document Integration**: Create integration guides for your external systems

## Support

For issues or questions:
- Check CloudWatch logs for detailed error information
- Review the Admin Insights Agent documentation
- Contact the platform team

## References

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Admin Insights Agent Design Document](../.kiro/specs/admin-insights-agent/design.md)
- [Admin Insights Agent Requirements](../.kiro/specs/admin-insights-agent/requirements.md)
