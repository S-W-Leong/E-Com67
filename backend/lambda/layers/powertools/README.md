# AWS Lambda Powertools Layer

This directory contains the configuration for building a custom Lambda layer with AWS Lambda Powertools.

## What is Lambda Powertools?

AWS Lambda Powertools provides utilities for:
- **Structured Logging** - JSON-formatted logs with correlation IDs
- **Distributed Tracing** - Automatic X-Ray instrumentation
- **Custom Metrics** - Easy CloudWatch metrics
- **Event Validation** - Request/response validation
- **Batch Processing** - SQS/Kinesis batch utilities

## Build Options

The CDK stack supports two options for the Powertools layer:

### Option 1: AWS-Managed Layer (Default)

The easiest approach - uses AWS's pre-built Powertools layer:
- No build required
- Automatically updated by AWS
- ARN: `arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:59`

This is the default if you haven't built the custom layer.

### Option 2: Custom-Built Layer (Recommended for Production)

Build your own layer for:
- Version pinning
- Reproducible builds
- Custom dependencies
- Offline development

## Building the Layer

To build the custom layer:

```bash
cd backend/lambda/layers/powertools
./build.sh
```

This will:
1. Install `aws-lambda-powertools` into the `python/` directory
2. Create the proper Lambda layer structure
3. Ready for CDK deployment

## Deployment

After building (if using custom layer), deploy with CDK:

```bash
cd backend
cdk deploy
```

The CDK stack will automatically detect the built layer and use it instead of the AWS-managed layer.

## Dependencies

The layer includes:
- `aws-lambda-powertools[tracer,validation]>=2.31.0`

## Usage in Lambda Functions

All Lambda functions in this project use Powertools:

```python
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event, context: LambdaContext):
    logger.info("Processing request")
    # Your code here
```

## Environment Variables

The following environment variables are automatically set by the CDK stack:
- `POWERTOOLS_SERVICE_NAME` - Service identifier for traces
- `POWERTOOLS_METRICS_NAMESPACE` - CloudWatch metrics namespace
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

## References

- [Powertools Documentation](https://docs.powertools.aws.dev/lambda/python/)
- [Layer ARN Versions](https://docs.powertools.aws.dev/lambda/python/latest/#lambda-layer)
- [X-Ray Tracing Guide](https://docs.powertools.aws.dev/lambda/python/latest/core/tracer/)
