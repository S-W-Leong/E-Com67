# CORS Implementation Guide for Lambda Functions

This guide ensures all Lambda functions exposed through API Gateway have proper CORS (Cross-Origin Resource Sharing) headers to prevent browser blocking issues.

## Why CORS is Important

When a frontend application (running on `http://localhost:3000` or any domain) makes requests to API Gateway endpoints, browsers enforce CORS policy. Without proper CORS headers in the API response, browsers will block the request with errors like:

```
Access to XMLHttpRequest at 'https://api.example.com/endpoint' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Standard CORS Headers

All API responses must include these headers:

```json
{
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, X-User-Id"
}
```

## Implementation Approaches

### 1. Using the Standardized CORS Utility (Recommended)

Import and use the standardized CORS utility from the utils layer:

```python
from utils.cors import ensure_cors_headers, create_success_response, create_error_response

# For Lambda functions using AWS Lambda Powertools APIGatewayRestResolver
def handler(event, context):
    try:
        response = app.resolve(event, context)
        # Ensure CORS headers are present
        response = ensure_cors_headers(response)
        return response
    except Exception as e:
        return create_error_response(500, "INTERNAL_SERVER_ERROR", "Internal server error")

# For Lambda functions with manual response creation
def some_endpoint():
    data = {"message": "success"}
    return create_success_response(data, 200)
```

### 2. Manual CORS Headers (Legacy)

If not using the utility, ensure all response functions include CORS headers:

```python
def create_success_response(data, status_code=200):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token"
        },
        "body": json.dumps(data)
    }
```

## Lambda Functions Audit Status

### ✅ Functions with Proper CORS Implementation

1. **orders** - Uses standardized CORS utility
2. **product_crud** - Has proper CORS headers in success/error responses
3. **cart** - Has proper CORS headers in success/error responses  
4. **search** - Has proper CORS headers in all responses
5. **payment** - Has proper CORS headers in success/error responses

### ⚠️ Functions Not Requiring CORS

1. **chat** - WebSocket-based, doesn't need CORS headers
2. **order_processor** - Internal Step Functions, not exposed to frontend
3. **search_sync** - Internal DynamoDB stream handler
4. **email_notification** - Internal SNS handler
5. **knowledge_manager** - Internal processing
6. **knowledge_processor** - Internal processing
7. **notification_orchestrator** - Internal processing

## Testing CORS Implementation

### 1. Browser Developer Tools

Check the Network tab in browser developer tools:
- Look for successful requests (200 status)
- Verify response headers include `Access-Control-Allow-Origin: *`
- No CORS error messages in console

### 2. Manual Testing with curl

```bash
# Test API endpoint
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type,Authorization" \
     -X OPTIONS \
     https://your-api-gateway-url/endpoint

# Should return CORS headers in response
```

### 3. Frontend Integration Test

```javascript
// Test from browser console or frontend app
fetch('https://your-api-gateway-url/endpoint', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  }
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('CORS Error:', error));
```

## Common CORS Issues and Solutions

### Issue 1: Missing CORS Headers in Success Responses

**Problem**: Lambda function only has CORS headers in error responses
**Solution**: Ensure all response paths include CORS headers

### Issue 2: AWS Lambda Powertools APIGatewayRestResolver

**Problem**: Powertools doesn't automatically add CORS headers
**Solution**: Use `ensure_cors_headers()` utility in the handler

### Issue 3: Inconsistent CORS Headers

**Problem**: Different endpoints return different CORS headers
**Solution**: Use the standardized CORS utility for consistency

### Issue 4: OPTIONS Preflight Requests

**Problem**: Browser sends OPTIONS request before actual request
**Solution**: Handle OPTIONS method explicitly:

```python
if http_method == 'OPTIONS':
    return create_success_response({}, 200)
```

## Deployment Checklist

Before deploying any Lambda function exposed through API Gateway:

- [ ] Function includes CORS headers in ALL response paths
- [ ] Function handles OPTIONS method for preflight requests
- [ ] Success responses include CORS headers
- [ ] Error responses include CORS headers
- [ ] Headers include `Access-Control-Allow-Origin: *`
- [ ] Headers include appropriate `Access-Control-Allow-Methods`
- [ ] Headers include appropriate `Access-Control-Allow-Headers`
- [ ] Tested with browser developer tools
- [ ] No CORS errors in browser console

## Future Prevention

1. **Use the standardized CORS utility** for all new Lambda functions
2. **Include CORS testing** in the development workflow
3. **Review CORS headers** during code reviews
4. **Update this guide** when adding new API endpoints

## API Gateway CORS vs Lambda CORS

**API Gateway CORS**: Handles preflight OPTIONS requests and error responses
**Lambda CORS**: Must handle CORS headers in successful responses

Both are required for complete CORS support. API Gateway configuration alone is not sufficient.