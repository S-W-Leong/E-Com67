# Strands SDK Lambda Layer

## Current Status: Python Version Compatibility Issue

This layer includes the Strands AI Agent SDK for enhancing the E-Com67 chat functionality, but requires Python 3.10+.

## Python Version Requirements

- **Strands SDK**: Requires Python 3.10 or higher
- **AWS Lambda**: Supports Python 3.9, 3.10, 3.11, and 3.12
- **Current Setup**: Updated to use Python 3.10 for Strands layer compatibility

## Dependencies

This layer includes:
- `strands-agents>=0.1.0` - Core Strands agent framework (correct package name)
- `strands-agents-tools>=0.1.0` - Pre-built tools for common tasks
- `pydantic>=2.0.0` - Data validation and serialization
- `boto3>=1.34.0` - AWS SDK for Python

## Package Information

**Package Names**: 
- `strands-agents` (not `strands-agents-sdk`)
- `strands-agents-tools`

**Version Availability**: All versions require Python 3.10+
- strands-agents: 1.20.0 (latest)
- strands-agents-tools: 0.2.18 (latest)

## Deployment Notes

The deployment script (`deploy.sh`) has been updated to:
1. Use Python 3.10 for the Strands layer specifically
2. Check for Python 3.10 availability before attempting installation
3. Gracefully handle missing Python 3.10 or package installation failures

## Next Steps

1. **Ensure Python 3.10**: Make sure Python 3.10 is installed on your deployment environment
2. **Update CDK Stack**: Configure the compute stack to use Python 3.10 runtime for the chat Lambda function
3. **Test Integration**: Verify the Strands agent works correctly with the E-Com67 platform

## Development Environment Setup

To work with Strands SDK locally:
```bash
# Install Python 3.10 if not available
# On macOS with Homebrew:
brew install python@3.10

# Create virtual environment with Python 3.10
python3.10 -m venv .venv-strands
source .venv-strands/bin/activate

# Install Strands SDK
pip install strands-agents strands-agents-tools pydantic boto3
```

## Related Files

- `lambda/chat/strands_config.py` - Strands agent configuration
- `lambda/chat/models.py` - Pydantic models for structured responses
- `.kiro/specs/strands-ai-agent/` - Complete specification for the enhancement
- `stacks/compute_stack.py` - CDK stack configuration (needs Python 3.10 runtime)