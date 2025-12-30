# WebSocket Customer App Connection Fix

## Issue Summary

The customer app's WebSocket connection to the chatbot was failing with the error:
```
WebSocket connection to 'wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod?token=...' failed
```

## Root Causes

### 1. Trailing Slash in WebSocket URL
The `.env` file had a trailing slash in the WebSocket URL:
```
VITE_WEBSOCKET_URL=wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod/
```

This caused the chat service to construct an invalid URL when appending query parameters.

### 2. Unnecessary Token Parameter
The chat service was trying to pass an authentication token as a query parameter, but:
- The WebSocket API doesn't have an authorizer configured
- The Lambda function expects anonymous connections
- The token parameter was being passed even when no user was authenticated

## Fixes Applied

### Fix 1: Remove Trailing Slash
**File**: `frontends/customer-app/.env`

Changed:
```env
VITE_WEBSOCKET_URL=wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod/
```

To:
```env
VITE_WEBSOCKET_URL=wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod
```

### Fix 2: Update Connection Logic
**File**: `frontends/customer-app/src/services/chat.js`

Updated the WebSocket URL construction to:
1. Always include the session ID (required for chat history)
2. Only include the token if one is available
3. Make the token optional for future authentication implementation

Changed from:
```javascript
const wsUrl = `${this.getWebSocketUrl()}?token=${encodeURIComponent(token || 'guest')}&sessionId=${sessionId}`
```

To:
```javascript
const wsUrl = `${this.getWebSocketUrl()}?sessionId=${sessionId}${token ? `&token=${encodeURIComponent(token)}` : ''}`
```

## Current Architecture

### WebSocket API Configuration
- **API ID**: `3q1jt2y351`
- **Stage**: `prod`
- **Region**: `ap-southeast-1`
- **Authentication**: None (anonymous connections allowed)
- **Routes**:
  - `$connect` - Connection establishment
  - `$disconnect` - Connection cleanup
  - `sendMessage` - Message handling

### Lambda Function
- **Function**: `e-com67-chat`
- **Runtime**: Python 3.10
- **Handler**: `chat.handler`
- **Authentication**: Extracts user from authorizer context (returns 'anonymous' if not present)

## Testing

After applying these fixes, test the connection by:

1. **Restart the development server**:
   ```bash
   cd frontends/customer-app
   npm run dev
   ```

2. **Open the customer app** in your browser

3. **Click the chat widget** (blue circle button in bottom-right)

4. **Verify connection**:
   - Status should show "Online"
   - Welcome message should appear
   - You should be able to send messages

5. **Check browser console** for any errors

## Future Enhancements

### Add WebSocket Authentication
To add proper authentication in the future:

1. **Add Cognito Authorizer to WebSocket API** (`stacks/api_stack.py`):
   ```python
   # Create Lambda authorizer for WebSocket
   websocket_authorizer = apigwv2.CfnAuthorizer(
       self, "WebSocketAuthorizer",
       api_id=self.websocket_api.ref,
       authorizer_type="REQUEST",
       authorizer_uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{authorizer_function.function_arn}/invocations",
       identity_source=["route.request.querystring.token"],
       name="CognitoAuthorizer"
   )
   
   # Update $connect route to use authorizer
   connect_route = apigwv2.CfnRoute(
       self, "ConnectRoute",
       api_id=self.websocket_api.ref,
       route_key="$connect",
       authorization_type="CUSTOM",
       authorizer_id=websocket_authorizer.ref,
       target=f"integrations/{websocket_integration.ref}"
   )
   ```

2. **Create Lambda Authorizer Function**:
   - Validate JWT token from Cognito
   - Return IAM policy allowing/denying connection
   - Include user information in context

3. **Update Lambda Handler** (`lambda/chat/chat.py`):
   ```python
   def extract_user_id(event: Dict[str, Any]) -> Optional[str]:
       """Extract user ID from WebSocket event"""
       try:
           authorizer = event.get('requestContext', {}).get('authorizer', {})
           # Get user ID from authorizer context
           user_id = authorizer.get('principalId')
           if user_id and user_id != 'anonymous':
               return user_id
           return 'anonymous'
       except:
           return 'anonymous'
   ```

4. **Frontend remains unchanged** - it already passes the token

## Related Files

- `frontends/customer-app/.env` - Environment configuration
- `frontends/customer-app/src/services/chat.js` - Chat service
- `frontends/customer-app/src/components/ChatWidget.jsx` - Chat UI component
- `stacks/api_stack.py` - WebSocket API infrastructure
- `lambda/chat/chat.py` - WebSocket Lambda handler

## Troubleshooting

### Connection Still Failing?

1. **Check the WebSocket URL**:
   ```bash
   echo $VITE_WEBSOCKET_URL
   ```
   Should be: `wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod` (no trailing slash)

2. **Verify Lambda function is deployed**:
   ```bash
   aws lambda get-function --function-name e-com67-chat --region ap-southeast-1
   ```

3. **Check Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/e-com67-chat --follow --region ap-southeast-1
   ```

4. **Test WebSocket connection manually**:
   ```javascript
   const ws = new WebSocket('wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod?sessionId=test-123')
   ws.onopen = () => console.log('Connected!')
   ws.onerror = (error) => console.error('Error:', error)
   ```

### Common Errors

- **403 Forbidden**: Lambda doesn't have permission to be invoked by API Gateway
- **500 Internal Server Error**: Lambda function error (check CloudWatch logs)
- **Connection timeout**: Lambda function taking too long to respond
- **Invalid URL**: Check for trailing slashes or malformed query parameters

## References

- [AWS API Gateway WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [WebSocket API Routes](https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-routes.html)
- [Lambda Authorizers for WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-lambda-auth.html)
