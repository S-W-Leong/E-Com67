# WebSocket Connection Troubleshooting Guide

## Issue: Connection Failed

If you see "Failed to reconnect after multiple attempts" or the connection status shows "Disconnected", follow these steps:

### Step 1: Verify Environment Configuration

Check that `.env` has the correct WebSocket URL:

```bash
# Should look like this:
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
```

**Important**: 
- URL must start with `wss://` (not `ws://`)
- Must end with `/prod` (or your stage name)
- No trailing slash after stage name

### Step 2: Check Browser Console

Open browser DevTools (F12) and check the Console tab for errors:

**Common Errors:**

1. **"WebSocket connection to 'wss://...' failed"**
   - The WebSocket API endpoint is incorrect or not deployed
   - Check CloudFormation outputs for correct URL

2. **"401 Unauthorized"**
   - Authentication token is missing or invalid
   - Check that you're logged in with Cognito
   - Token might be expired - try logging out and back in

3. **"403 Forbidden"**
   - User doesn't have permission to access WebSocket API
   - Check IAM roles and API Gateway permissions

4. **"ECONNREFUSED" or "Connection refused"**
   - WebSocket API is not deployed or not accessible
   - Check that AdminInsightsStack is deployed

### Step 3: Check Network Tab

In DevTools, go to Network tab and filter by "WS" (WebSocket):

1. Look for connection attempts to your WebSocket URL
2. Check the status code:
   - **101 Switching Protocols**: Connection successful ✅
   - **401**: Authentication failed ❌
   - **403**: Forbidden ❌
   - **500**: Server error ❌
   - **502/503**: Lambda not responding ❌

3. Click on the WebSocket connection to see:
   - Request headers (should include token)
   - Response (error messages)

### Step 4: Verify Lambda Deployment

Check that the WebSocket connect Lambda is deployed:

```bash
# Check Lambda exists
aws lambda get-function --function-name e-com67-admin-insights-websocket-connect

# Check recent logs
aws logs tail /aws/lambda/e-com67-admin-insights-websocket-connect --follow
```

### Step 5: Test WebSocket Connection Manually

Use `wscat` to test the WebSocket connection:

```bash
# Install wscat if needed
npm install -g wscat

# Get your JWT token from browser (DevTools > Application > Local Storage)
# Or from Cognito
TOKEN="your-jwt-token-here"

# Test connection
wscat -c "wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod?token=$TOKEN"
```

Expected response:
```
Connected (press CTRL+C to quit)
< {"message":"Connected","sessionId":"session-abc123"}
```

### Step 6: Check CloudWatch Logs

View logs for the connect Lambda:

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/e-com67-admin-insights-websocket-connect --follow

# Or view recent logs
aws logs tail /aws/lambda/e-com67-admin-insights-websocket-connect --since 10m
```

Look for:
- "WebSocket connection established" (success)
- "No token provided" (missing token)
- "No user ID found in JWT token" (invalid token)
- "Token expired" (expired token)
- Any error messages

### Step 7: Verify API Gateway Configuration

Check that the WebSocket API is properly configured:

```bash
# Get API ID
aws cloudformation describe-stacks \
  --stack-name E-Com67-AdminInsightsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketAPIId`].OutputValue' \
  --output text

# Get API details
aws apigatewayv2 get-api --api-id YOUR_API_ID

# Check routes
aws apigatewayv2 get-routes --api-id YOUR_API_ID
```

Should have routes:
- `$connect`
- `$disconnect`
- `sendMessage`
- `$default`

### Step 8: Redeploy Lambda

If the Lambda code was updated, redeploy:

```bash
# Redeploy the stack
cdk deploy E-Com67-AdminInsightsStack

# Or just update the Lambda
cd lambda/admin_insights_agent
zip -r function.zip .
aws lambda update-function-code \
  --function-name e-com67-admin-insights-websocket-connect \
  --zip-file fileb://function.zip
```

### Step 9: Check Cognito Authentication

Verify you're properly authenticated:

```bash
# In browser console
import { fetchAuthSession } from 'aws-amplify/auth'
const session = await fetchAuthSession()
console.log('Token:', session.tokens?.idToken?.toString())
```

If no token, log out and log back in.

### Step 10: Restart Development Server

Sometimes Vite doesn't pick up `.env` changes:

```bash
# Stop the dev server (Ctrl+C)
# Restart it
npm run dev
```

## Common Solutions

### Solution 1: Update WebSocket URL

If you recently deployed, get the latest URL:

```bash
aws cloudformation describe-stacks \
  --stack-name E-Com67-AdminInsightsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURL`].OutputValue' \
  --output text
```

Update `.env` with this URL and restart dev server.

### Solution 2: Fix Token Passing

The token must be passed as a query parameter. Check `adminInsights.js`:

```javascript
// Should look like this:
const url = `${wsUrl}?token=${encodeURIComponent(token)}`
this.ws = new WebSocket(url)
```

### Solution 3: Clear Browser Cache

Sometimes old code is cached:

1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Solution 4: Check CORS (if applicable)

WebSocket doesn't use CORS, but if you see CORS errors, check:
- API Gateway CORS settings
- Lambda response headers

### Solution 5: Verify DynamoDB Table

Check that the connections table exists:

```bash
aws dynamodb describe-table --table-name e-com67-admin-insights-connections
```

If it doesn't exist, redeploy the stack.

## Debug Checklist

- [ ] `.env` has correct `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL`
- [ ] URL format is `wss://api-id.execute-api.region.amazonaws.com/stage`
- [ ] AdminInsightsStack is deployed
- [ ] WebSocket connect Lambda exists and is deployed
- [ ] Cognito authentication is working (can log in)
- [ ] JWT token is being retrieved successfully
- [ ] Token is being passed in WebSocket URL
- [ ] Browser console shows no errors
- [ ] Network tab shows WebSocket connection attempt
- [ ] CloudWatch logs show connection attempts
- [ ] DynamoDB connections table exists
- [ ] Development server was restarted after `.env` changes

## Still Not Working?

If you've tried all the above and it still doesn't work:

1. **Check Lambda Permissions**: Ensure the connect Lambda has permissions to write to DynamoDB

2. **Check API Gateway Permissions**: Ensure API Gateway can invoke the Lambda

3. **Check Network**: Ensure your network allows WebSocket connections (some corporate networks block them)

4. **Check Browser**: Try a different browser or incognito mode

5. **Check Logs**: Look at ALL CloudWatch log groups:
   - `/aws/lambda/e-com67-admin-insights-websocket-connect`
   - `/aws/apigateway/AdminInsightsWebSocketAPI/prod`

6. **Create a Test Script**: Create a simple Node.js script to test the connection:

```javascript
const WebSocket = require('ws');

const token = 'your-jwt-token';
const url = `wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod?token=${token}`;

const ws = new WebSocket(url);

ws.on('open', () => {
  console.log('Connected!');
});

ws.on('error', (error) => {
  console.error('Error:', error);
});

ws.on('close', (code, reason) => {
  console.log('Closed:', code, reason);
});
```

## Getting Help

If you need more help, provide:
1. Browser console errors (screenshot or text)
2. Network tab WebSocket details (status code, headers)
3. CloudWatch logs from connect Lambda
4. Output of `aws cloudformation describe-stacks --stack-name E-Com67-AdminInsightsStack`
5. Your `.env` file (with sensitive values redacted)

---

**Last Updated**: December 2024
