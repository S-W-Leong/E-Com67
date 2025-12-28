# Admin Insights Agent

This directory contains the main agent runtime that orchestrates conversation, tool invocation, and response generation using AWS Bedrock AgentCore.

## Structure

- `handler.py` - Main Lambda handler with error handling and observability
- `agent.py` - Agent core logic with Bedrock AgentCore integration
- `session_manager.py` - Session memory management using AgentCore Memory

## Dependencies

- **bedrock-agentcore-sdk-python**: AWS Bedrock AgentCore SDK for agent runtime
- **strands-agents**: Strands SDK for agent orchestration
- **boto3**: AWS SDK for Python
- **aws-lambda-powertools**: Logging, tracing, and metrics

## Key Features

- Natural language query processing
- Session-based conversation memory
- Tool invocation for analytics
- Security guardrails integration
- WebSocket streaming responses

## Testing

Property-based tests are located in `tests/test_admin_insights_agent.py` using the Hypothesis framework.
