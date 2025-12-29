# WebSocket Implementation for Admin Insights Agent

## Overview

This document describes the WebSocket API implementation for the Admin Insights Agent, enabling real-time streaming communication between the admin dashboard and the agent.

## Architecture

### Components

1. **WebSocket API Gateway**
   - API Name: `AdminInsightsWebSocketAPI`
   - Protocol: WebSocket
   - Routes: `$connect`, `$disconnect`, `sendMessage`, `$default`
   - Route Selection: `$request.body.action`

2. **DynamoDB Connections Table**
   - Table Name: `e-com67-admin-insights-connections`
   - Primary Key: `connectionId` (String)
   - Attributes:
     - `sessionId`: Agent session ID
     - `actorId`: Admin user ID
     - `connectedAt`: Connection timestamp
     - `ttl`: Time-to-live (24 hours)
   - GSI: `actorId-index` for querying by user

3. **Lambda Functions**
   - **Connect Handler** (`websocket_connect.py`): Handles connection establishment
   - **Disconnect Handler** (`websocket_disconnect.py`): Handles connection cleanup
   - **Agent Handler** (`handler.py`): Processes messages and streams responses

## Connection Flow

### 1. Connection Establishment ($connect)

```
Client → WebSocket API → Connect Lambda
                          ↓
                    Store connection in DynamoDB
                          ↓
                    Initialize session
                          ↓
                    Return 200 OK
```

**Connect Handler Actions:**
- Extracts `connectionId` from event
- Extracts `actorId` from JWT claims (via authorizer)
- Generates `sessionId`
- Stores connection info in DynamoDB with 24-hour TTL
- Returns success response

### 2. Message Processing (sendMessage)

```
Client → WebSocket API → Agent Lambda
                          ↓
                    Retrieve connection info
                          ↓
                    Process message through agent
                          ↓
                    Stream response chunks via WebSocket
                          ↓
                    Send completion message
```

**Agent Handler Actions:**
- Validates request and extracts parameters
- Retrieves session info from connections table
- Processes message through Bedrock AgentCore
- Streams response chunks to WebSocket connection
- Handles `GoneException` for stale connections
- Sends completion or error messages

### 3. Disconnection ($disconnect)

```
Client → WebSocket API → Disconnect Lambda
                          ↓
                    Retrieve connection info
                          ↓
                    Terminate agent session
                          ↓
                    Delete connection from DynamoDB
                          ↓
                    Return 200 OK
```

**Disconnect Handler Actions:**
- Retrieves connection info from DynamoDB
- Calls `SessionManager.terminate_session()`
- Deletes connection record
- Returns success (even if connection not found)

## Message Format

### Client → Server (sendMessage)

```json
{
  "action": "sendMessage",
  "message": "What are the top selling products this month?"
}
```

### Server → Client (Response Chunks)

```json
{
  "type": "chunk",
  "content": "Based on the sales data...",
  "timestamp": 1234567890
}
```

### Server → Client (Completion)

```json
{
  "type": "complete",
  "content": "",
  "timestamp": 1234567890
}
```

### Server → Client (Error)

```json
{
  "type": "error",
  "content": "An error occurred while processing your request",
  "timestamp": 1234567890
}
```

## Authentication

### Current Implementation

Authentication is handled in the connect handler by extracting the `actorId` from JWT claims in the authorizer context:

```python
authorizer = event['requestContext'].get('authorizer', {})
actor_id = authorizer.get('sub') or authorizer.get('principalId')
```

### Production Considerations

For production, implement a proper JWT authorizer Lambda that:
1. Validates JWT token from query string parameter
2. Verifies token signature against Cognito
3. Checks token expiration
4. Returns authorization context with user claims

## Error Handling

### Connection Errors

- **Missing actor_id**: Returns 401 Unauthorized
- **DynamoDB errors**: Returns 500 Internal Server Error
- **Unexpected errors**: Returns 500 with generic message

### Message Processing Errors

- **Validation errors**: Sends error message to WebSocket
- **Agent errors**: Sends error message to WebSocket
- **Stale connections**: Cleans up connection from DynamoDB

### Stale Connection Handling

When `GoneException` is caught:
1. Log warning about stale connection
2. Delete connection from DynamoDB
3. Stop processing (connection is closed)

## Permissions

### Agent Lambda IAM Permissions

```python
# WebSocket Management
"execute-api:ManageConnections" on WebSocket API

# DynamoDB
"dynamodb:GetItem" on connections table
"dynamodb:PutItem" on connections table
"dynamodb:DeleteItem" on connections table
"dynamodb:Query" on connections table
```

### Connect/Disconnect Lambda Permissions

```python
# DynamoDB
"dynamodb:GetItem" on connections table
"dynamodb:PutItem" on connections table
"dynamodb:DeleteItem" on connections table
```

## Deployment

### Prerequisites

1. Deploy DataStack (for Cognito User Pool)
2. Deploy ComputeStack (for Lambda layers)
3. Run `scripts/create_admin_insights_memory.py` to create memory

### Deployment Steps

1. Deploy AdminInsightsStack:
   ```bash
   cdk deploy AdminInsightsStack
   ```

2. Note the WebSocket URL from stack outputs:
   ```
   AdminInsightsStack.WebSocketURL = wss://abc123.execute-api.ap-southeast-1.amazonaws.com/prod
   ```

3. Update frontend configuration with WebSocket URL

### Testing

#### Test Connection

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket (replace URL and token)
wscat -c "wss://abc123.execute-api.ap-southeast-1.amazonaws.com/prod?token=YOUR_JWT_TOKEN"

# Send message
> {"action": "sendMessage", "message": "What are the top products?"}

# Observe response chunks
< {"type": "chunk", "content": "Based on...", "timestamp": 1234567890}
< {"type": "complete", "content": "", "timestamp": 1234567890}
```

## Frontend Integration

### JavaScript Example

```javascript
// Connect to WebSocket
const token = await getAuthToken(); // Get JWT from Cognito
const ws = new WebSocket(`wss://abc123.execute-api.ap-southeast-1.amazonaws.com/prod?token=${token}`);

// Handle connection open
ws.onopen = () => {
  console.log('Connected to Admin Insights Agent');
};

// Handle incoming messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'chunk':
      // Append chunk to UI
      appendToChat(message.content);
      break;
    case 'complete':
      // Mark response as complete
      markResponseComplete();
      break;
    case 'error':
      // Display error
      showError(message.content);
      break;
  }
};

// Send message
function sendMessage(text) {
  ws.send(JSON.stringify({
    action: 'sendMessage',
    message: text
  }));
}

// Close connection
ws.close();
```

## Monitoring

### CloudWatch Metrics

- `AgentInvocations`: Total agent invocations
- `ResponseChunksStreamed`: Number of chunks streamed per response
- `WebSocketConnections`: Active WebSocket connections (custom metric)

### CloudWatch Logs

- `/aws/lambda/e-com67-admin-insights-websocket-connect`
- `/aws/lambda/e-com67-admin-insights-websocket-disconnect`
- `/aws/lambda/e-com67-admin-insights-agent`

### Key Log Events

- Connection establishment with `connectionId` and `actorId`
- Message processing with `sessionId` and latency
- Stale connection cleanup
- Session termination

## Troubleshooting

### Connection Fails

1. Check JWT token is valid and not expired
2. Verify Cognito User Pool configuration
3. Check CloudWatch logs for connect handler

### Messages Not Received

1. Verify connection is still active
2. Check agent Lambda logs for errors
3. Verify DynamoDB connections table has entry

### Stale Connections

1. Check TTL is enabled on connections table
2. Verify disconnect handler is cleaning up properly
3. Monitor for `GoneException` in agent logs

## Future Enhancements

1. **True Streaming**: Implement generator-based streaming for real-time token generation
2. **Connection Pooling**: Support multiple connections per user
3. **Reconnection Logic**: Automatic reconnection with session restoration
4. **Rate Limiting**: Per-user rate limiting on message sending
5. **Message Queue**: Queue messages when connection is temporarily unavailable
6. **Compression**: Enable WebSocket compression for large responses
7. **Metrics Dashboard**: Real-time dashboard for WebSocket connections and metrics

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 1.4**: Streaming response generation via WebSocket
- **Requirement 4.1**: Session initialization on connection
- **Requirement 4.5**: Session termination on disconnection
- **Requirement 10.4**: WebSocket API Gateway configuration
