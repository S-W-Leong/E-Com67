# OpenSearch Migration Testing Guide

## Pre-Testing: Check Domain Status

First, verify that the OpenSearch domain is ready:

```bash
# Check if domain is ready
aws opensearch describe-domain --domain-name e-com67-products --query 'DomainStatus.{DomainName:DomainName,Processing:Processing,DomainEndpoint:DomainEndpoint,Created:Created}'
```

**Wait until `DomainEndpoint` shows a URL** (not null). This can take 10-15 minutes after deployment.

## Testing Levels

### Level 1: Infrastructure Tests (Immediate)

These tests verify the infrastructure is correctly configured:

#### 1.1 Test Lambda Function Configuration
```bash
# Check if search function has correct OpenSearch endpoint
aws lambda get-function-configuration --function-name e-com67-search --query 'Environment.Variables.OPENSEARCH_ENDPOINT'

# Check if search-sync function has correct endpoint
aws lambda get-function-configuration --function-name e-com67-search-sync --query 'Environment.Variables.OPENSEARCH_ENDPOINT'
```

#### 1.2 Test IAM Permissions
```bash
# Check Lambda execution role has OpenSearch permissions
aws iam get-role-policy --role-name e-com67-lambda-execution-role --policy-name LambdaExecutionRoleDefaultPolicy | grep -A 10 -B 5 "es:ESHttp"
```

### Level 2: Connectivity Tests (Once Domain is Ready)

#### 2.1 Test Direct OpenSearch Access
```bash
# Get the domain endpoint
OPENSEARCH_ENDPOINT=$(aws opensearch describe-domain --domain-name e-com67-products --query 'DomainStatus.DomainEndpoint' --output text)

# Test basic connectivity (should return cluster info)
curl -X GET "https://$OPENSEARCH_ENDPOINT/" --aws-sigv4 "aws:amz:ap-southeast-1:es"
```

#### 2.2 Test Index Creation
```bash
# Test creating a test index
curl -X PUT "https://$OPENSEARCH_ENDPOINT/test-index" --aws-sigv4 "aws:amz:ap-southeast-1:es" -H 'Content-Type: application/json' -d '{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}'

# Verify index was created
curl -X GET "https://$OPENSEARCH_ENDPOINT/_cat/indices" --aws-sigv4 "aws:amz:ap-southeast-1:es"
```

### Level 3: Lambda Function Tests

#### 3.1 Test Search Function Directly
```bash
# Test search function with empty query (should not error)
aws lambda invoke --function-name e-com67-search --payload '{
  "httpMethod": "GET",
  "path": "/search",
  "queryStringParameters": {
    "q": ""
  }
}' response.json

# Check the response
cat response.json
```

#### 3.2 Test Search-Sync Function
```bash
# Test search-sync function (simulates DynamoDB stream event)
aws lambda invoke --function-name e-com67-search-sync --payload '{
  "Records": [
    {
      "eventName": "INSERT",
      "dynamodb": {
        "NewImage": {
          "productId": {"S": "test-product-123"},
          "name": {"S": "Test Product"},
          "description": {"S": "A test product for migration testing"},
          "category": {"S": "test"},
          "price": {"N": "29.99"}
        }
      }
    }
  ]
}' sync-response.json

# Check the response
cat sync-response.json
```

### Level 4: End-to-End Tests

#### 4.1 Test Product Creation and Search Flow
```bash
# 1. Create a test product (this should trigger search-sync via DynamoDB stream)
aws lambda invoke --function-name e-com67-product-crud --payload '{
  "httpMethod": "POST",
  "path": "/products",
  "body": "{\"name\":\"Migration Test Product\",\"description\":\"Testing search after OpenSearch migration\",\"category\":\"test\",\"price\":19.99,\"stock\":10}"
}' product-response.json

# 2. Wait a few seconds for indexing
sleep 5

# 3. Search for the product
aws lambda invoke --function-name e-com67-search --payload '{
  "httpMethod": "GET",
  "path": "/search",
  "queryStringParameters": {
    "q": "Migration Test"
  }
}' search-response.json

# Check if product appears in search results
cat search-response.json
```

#### 4.2 Test Knowledge Base Processing (if applicable)
```bash
# Test knowledge processor function
aws lambda invoke --function-name e-com67-knowledge-processor --payload '{
  "Records": [
    {
      "s3": {
        "bucket": {"name": "your-knowledge-base-bucket"},
        "object": {"key": "test-document.txt"}
      }
    }
  ]
}' knowledge-response.json

cat knowledge-response.json
```

### Level 5: API Gateway Tests (if deployed)

If you have API Gateway deployed, test the full HTTP endpoints:

```bash
# Get your API Gateway URL (replace with actual URL)
API_URL="https://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod"

# Test search endpoint
curl -X GET "$API_URL/search?q=test" -H "Content-Type: application/json"

# Test with more complex query
curl -X GET "$API_URL/search?q=product&category=electronics&minPrice=10&maxPrice=100" -H "Content-Type: application/json"
```

## Troubleshooting Common Issues

### Issue 1: "No export named E-Com67-OpenSearchEndpoint found"
**Solution**: Redeploy the DataStack first, then ComputeStack
```bash
cdk deploy E-Com67-DataStack --require-approval never
cdk deploy E-Com67-ComputeStack --require-approval never
```

### Issue 2: Lambda functions can't connect to OpenSearch
**Symptoms**: Connection timeout or authentication errors
**Solutions**:
1. Check IAM permissions:
   ```bash
   aws iam get-role-policy --role-name e-com67-lambda-execution-role --policy-name LambdaExecutionRoleDefaultPolicy
   ```
2. Verify domain access policy allows Lambda role access
3. Check if domain is in VPC (should be public for this setup)

### Issue 3: Search returns empty results
**Symptoms**: Search function works but returns no results
**Solutions**:
1. Check if products are indexed:
   ```bash
   curl -X GET "https://$OPENSEARCH_ENDPOINT/products/_search" --aws-sigv4 "aws:amz:ap-southeast-1:es"
   ```
2. Manually trigger search-sync for existing products
3. Check DynamoDB streams are enabled and connected

### Issue 4: Authentication errors
**Symptoms**: 403 Forbidden or signature errors
**Solutions**:
1. Verify Lambda functions are using `"es"` service (not `"aoss"`)
2. Check AWS credentials and region configuration
3. Verify domain access policy

## Performance Comparison

To verify performance is similar to before:

```bash
# Time a search request
time aws lambda invoke --function-name e-com67-search --payload '{
  "httpMethod": "GET",
  "path": "/search",
  "queryStringParameters": {"q": "product"}
}' perf-response.json
```

## Success Criteria

✅ **Migration is successful if**:
1. All Lambda functions can connect to OpenSearch without errors
2. Product search returns relevant results
3. Search-sync successfully indexes new/updated products
4. Response times are similar to before migration
5. No authentication or permission errors
6. Knowledge base processing works (if used)

## Quick Health Check Script

Save this as `test-opensearch-migration.sh`:

```bash
#!/bin/bash
echo "🔍 Testing OpenSearch Migration..."

# Check domain status
echo "1. Checking domain status..."
aws opensearch describe-domain --domain-name e-com67-products --query 'DomainStatus.{Processing:Processing,DomainEndpoint:DomainEndpoint}'

# Test search function
echo "2. Testing search function..."
aws lambda invoke --function-name e-com67-search --payload '{"httpMethod":"GET","path":"/search","queryStringParameters":{"q":"test"}}' /tmp/search-test.json
echo "Search response:"
cat /tmp/search-test.json

# Test search-sync function
echo "3. Testing search-sync function..."
aws lambda invoke --function-name e-com67-search-sync --payload '{"Records":[{"eventName":"INSERT","dynamodb":{"NewImage":{"productId":{"S":"test-123"},"name":{"S":"Test Product"}}}}]}' /tmp/sync-test.json
echo "Sync response:"
cat /tmp/sync-test.json

echo "✅ Migration test complete!"
```

Run with: `chmod +x test-opensearch-migration.sh && ./test-opensearch-migration.sh`