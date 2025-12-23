# Strands AI Agent Setup for E-Com67

This document describes the Strands SDK integration setup for the E-Com67 platform's enhanced AI chat functionality.

## Overview

The Strands AI Agent enhancement replaces the existing Amazon Bedrock-based chatbot with a sophisticated Strands SDK-powered agent system that provides:

- **Direct API Integration**: Custom tools that interact with E-Com67 platform APIs
- **Structured Responses**: Pydantic models for consistent data formatting  
- **Enhanced Recommendations**: AI-powered product suggestions with reasoning
- **Better Error Handling**: Graceful fallbacks and detailed error reporting
- **Performance Optimization**: Efficient tool execution and caching strategies

## Files Created

### Configuration Module
- `strands_config.py` - Main configuration and agent management module
- `test_strands_setup.py` - Local testing script for configuration validation
- `test_lambda_import.py` - Lambda-compatible test handler

### Layer Structure
- `layers/strands/python/requirements.txt` - Strands SDK dependencies

### CDK Updates
- Updated `stacks/compute_stack.py` to include Strands layer and environment variables

## Configuration

### Environment Variables

The following environment variables are configured in the CDK stack:

```python
# Bedrock Model Configuration
BEDROCK_MODEL_ID = "amazon.titan-text-express-v1"  # Amazon Titan Text Express model
BEDROCK_TEMPERATURE = "0.7"
BEDROCK_MAX_TOKENS = "4096"
BEDROCK_STREAMING = "false"

# Strands Agent Configuration  
DEPLOYMENT_STAGE = "development"  # development, staging, production
PLATFORM_VERSION = "1.0.0"

# Existing E-Com67 Configuration
CHAT_HISTORY_TABLE_NAME = "..."
PRODUCTS_TABLE_NAME = "..."
OPENSEARCH_ENDPOINT = "..."
```

### Model Selection

The configuration uses **Amazon Titan Text Express** as the default model for several reasons:

- **Native AWS Integration**: Titan models are Amazon's own foundation models, providing seamless integration with AWS services
- **Cost Effectiveness**: Titan models offer competitive pricing for text generation tasks
- **Availability**: Available by default in most AWS regions without additional model access requests
- **Performance**: Optimized for conversational AI and text generation tasks
- **Larger Context Window**: Supports up to 4096 tokens for longer conversations and complex tool interactions

### Deployment Stages

The configuration automatically adjusts based on deployment stage:

- **Development**: 10 message memory, 15s timeout, debug enabled
- **Staging**: 15 message memory, 20s timeout, debug enabled  
- **Production**: 20 message memory, 25s timeout, debug disabled

## Usage

### Basic Agent Initialization

```python
from strands_config import StrandsAgentManager

# Create agent manager
manager = StrandsAgentManager()

# Get agent instance with user context
user_context = {
    'user_id': 'user123',
    'session_id': 'session456',
    'connection_id': 'conn789'
}

agent = manager.get_agent(user_context)

# Use agent (once tools are implemented)
response = agent("Help me find a laptop under $1000")
```

### Configuration Validation

```python
from strands_config import StrandsAgentManager

manager = StrandsAgentManager()
validation_results = manager.validate_configuration()

if validation_results['valid']:
    print("Configuration is valid")
else:
    print("Configuration errors:", validation_results['errors'])
```

## Testing

### Local Testing

Run the setup validation tests:

```bash
# Test configuration module
python lambda/chat/test_strands_setup.py

# Test Lambda handler
python lambda/chat/test_lambda_import.py

# Test deployment readiness
python test_strands_deployment.py
```

### Lambda Testing

Deploy the test handler to validate in actual Lambda environment:

```python
# Use test_lambda_import.lambda_handler as a temporary Lambda function
# to validate the setup in the AWS environment
```

## Dependencies

### Strands SDK Layer

The `layers/strands/python/requirements.txt` includes:

```
strands-agents-sdk>=0.1.0
strands-agents-tools>=0.1.0
pydantic>=2.0.0
```

### CDK Layer Configuration

```python
self.strands_layer = _lambda.LayerVersion(
    self, "StrandsLayer",
    layer_version_name="e-com67-strands",
    code=_lambda.Code.from_asset("layers/strands"),
    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9, _lambda.Runtime.PYTHON_3_10],
    description="Strands SDK for enhanced AI agent capabilities"
)
```

## Next Steps

1. **Install Strands SDK**: The actual SDK packages need to be installed in the layer
2. **Implement Custom Tools**: Create product search, cart management, and order query tools
3. **Update Chat Handler**: Integrate Strands agent into the main chat.py handler
4. **Add Pydantic Models**: Create structured response models
5. **Testing**: Comprehensive testing of agent functionality

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Strands SDK is properly installed in the layer
2. **Configuration Errors**: Check environment variables are set correctly
3. **Timeout Issues**: Adjust tool timeout settings for your use case
4. **Memory Issues**: Increase Lambda memory if needed for complex operations

### Validation Commands

```bash
# Check configuration
python -c "from lambda.chat.strands_config import StrandsAgentManager; print(StrandsAgentManager().validate_configuration())"

# Test imports
python -c "from lambda.chat.strands_config import test_strands_sdk_import; print(test_strands_sdk_import())"
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Chat Lambda   │    │  Strands Agent  │
│   Frontend      │◄──►│   Function      │◄──►│   (Enhanced)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
                ┌──────▼──────┐              ┌──────────▼──────────┐              ┌──────▼──────┐
                │  Product    │              │   Cart Management   │              │   Order     │
                │ Search Tool │              │       Tool          │              │ Query Tool  │
                └──────┬──────┘              └──────────┬──────────┘              └──────┬──────┘
                       │                                │                                 │
                ┌──────▼──────┐              ┌──────────▼──────────┐              ┌──────▼──────┐
                │  Search API │              │     Cart API        │              │  Orders API │
                │ (OpenSearch)│              │   (DynamoDB)        │              │ (DynamoDB)  │
                └─────────────┘              └─────────────────────┘              └─────────────┘
```

This setup provides the foundation for the Strands AI Agent enhancement while maintaining compatibility with the existing E-Com67 platform architecture.