# WebSocket Message Handling Fix

## Problem

The Admin Insights Agent Lambda was throwing a "MISSING_PARAMETER" error when receiving messages from the frontend:

```json
{
  "error_code": "MISSING_PARAMETER",
  "error_message": "Missing required parameter: 'message'",
  "status_code": 400,
  "details": {"parameter": "message"}
}
```

## Root Causes

### 1. Body Parsing Issue

The `validate_request` function had a bug in how it handled missing body fields:

```python
# OLD CODE (BUGGY)
body = event.get('body', {})  # Default to empty dict
if isinstance(body, str):
    body = json.loads(body)
```

**Problem**: When `body` is missing, it defaults to `{}` (dict), not a string. This causes issues because:
- WebSocket events always have a `body` field (as a string)
- If `body` is missing, something is wrong with the event
- The default `{}` masks the real issue

**Fix**: Check if body exists and handle missing body as an error:

```python
# NEW CODE (FIXED)
body = event.get('body')

if not body:
    raise AgentError(
        code=ErrorCode.MALFORMED_REQUEST,
        message="Missing request body",
        status_code=400
    )

if isinstance(body, str):
    try:
        body = json.loads(body)
    except json.JSONDecodeError as e:
        raise AgentError(
            code=ErrorCode.MALFORMED_REQUEST,
            message="Invalid JSON in request body",
            status_code=400,
            details={"error": str(e)}
        )
```

### 2. Heartbeat/Ping Messages

The frontend sends heartbeat messages every 30 seconds:

```javascript
{
  "action": "ping"
}
```

These messages don't have a `message` field, which was causing the "MISSING_PARAMETER" error.

**Fix**: Added a ping handler before validation:

```python
# Handle heartbeat/ping messages
body = event.get('body')
if body:
    try:
        body_data = json.loads(body) if isinstance(body, str) else body
        if body_data.get('action') == 'ping':
            # Respond to ping with pong
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "pong"})
            }
    except:
        pass  # Continue with normal processing if parsing fails
```

### 3. Lambda Context Attribute Error

There was also a minor bug where the code was trying to access `context.request_id` instead of `context.aws_request_id`:

```python
# OLD CODE (BUGGY)
request_id = context.request_id  # AttributeError!

# NEW CODE (FIXED)
request_id = context.aws_request_id
```

## Testing

After deploying the fix:

1. **Ping messages are handled correctly**: The Lambda now responds to ping messages without errors
2. **Actual chat messages should work**: The body parsing is now correct for real messages

## Next Steps

To fully test the fix:

1. Open the admin dashboard
2. Send a test message like "What are the top selling products?"
3. Verify the agent responds correctly

## Files Modified

- `lambda/admin_insights_agent/handler.py`:
  - Fixed body parsing in `validate_request()`
  - Added ping message handler in `handler()`
  - Fixed `context.request_id` → `context.aws_request_id`

## Deployment

The fix was deployed using:

```bash
# Create zip file
zip -j /tmp/admin_insights_agent.zip lambda/admin_insights_agent/*.py

# Update Lambda function
aws lambda update-function-code \
  --function-name e-com67-admin-insights-agent \
  --zip-file fileb:///tmp/admin_insights_agent.zip
```
