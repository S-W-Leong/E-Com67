# Strands Layer OpenTelemetry Fix

## Problem

The chat Lambda function was failing with OpenTelemetry import errors. Investigation revealed:

1. The `layers/strands/requirements.txt` had OpenTelemetry packages commented out with a note saying "provided by powertools layer"
2. The `layers/powertools/requirements.txt` does NOT actually provide OpenTelemetry packages
3. The build scripts were using `requirements-minimal.txt` instead of the full `requirements.txt`
4. This caused missing dependencies when strands-agents tried to import OpenTelemetry modules

## Root Cause

The strands-agents library requires OpenTelemetry for instrumentation and tracing. The assumption that powertools would provide these packages was incorrect - powertools only provides AWS Lambda Powertools and Pydantic.

## Solution

### 1. Uncommented OpenTelemetry in requirements.txt

Updated `layers/strands/requirements.txt` to include:

```txt
# MCP with OpenTelemetry support
mcp>=1.11.0,<2.0.0

# OpenTelemetry packages (required by strands-agents)
opentelemetry-api>=1.30.0,<2.0.0
opentelemetry-sdk>=1.30.0,<2.0.0
opentelemetry-instrumentation-threading>=0.51b0,<1.00b0
opentelemetry-semantic-conventions>=0.51b0

# Ensure entry points are properly discoverable in Lambda
importlib-metadata>=6.0.0
```

### 2. Updated Build Script

Modified `build_strands_layer.sh` to use `requirements.txt` instead of `requirements-minimal.txt`:

```bash
pip install -r requirements.txt -t python/ --upgrade --no-cache-dir
```

### 3. Updated Pipeline Build

Modified `stacks/backend_pipeline_stack.py` to use `requirements.txt` in the CodeBuild buildspec:

```python
"pip install -r layers/strands/requirements.txt -t layers/strands/python/ ..."
```

## Files Changed

1. `layers/strands/requirements.txt` - Uncommented OpenTelemetry dependencies
2. `build_strands_layer.sh` - Changed from requirements-minimal.txt to requirements.txt
3. `stacks/backend_pipeline_stack.py` - Changed from requirements-minimal.txt to requirements.txt

## Next Steps

The pipeline will automatically rebuild the strands layer with the full requirements on the next deployment. This will include:

- OpenTelemetry API and SDK
- OpenTelemetry instrumentation for threading
- OpenTelemetry semantic conventions
- importlib-metadata for proper entry point discovery

## Testing

After deployment, verify the fix by:

1. Checking Lambda function logs for successful imports
2. Testing chat functionality end-to-end
3. Confirming no OpenTelemetry import errors in CloudWatch logs

## Python Runtime Compatibility

All packages in the updated `requirements.txt` are fully compatible with the Lambda runtimes used in E-Com67:

- **Python 3.9 functions**: ✅ All packages compatible
- **Python 3.10 functions**: ✅ All packages compatible

Key compatibility details:
- OpenTelemetry API/SDK: Requires Python >=3.8
- OpenTelemetry instrumentation packages: Requires Python >=3.9
- All other dependencies: Compatible with Python 3.9+

See [STRANDS_LAYER_PYTHON_COMPATIBILITY.md](./STRANDS_LAYER_PYTHON_COMPATIBILITY.md) for detailed compatibility analysis.

## Why requirements-minimal.txt Exists

The `requirements-minimal.txt` file was created to reduce layer size, but it still included OpenTelemetry because it's essential for strands-agents. However, using the full `requirements.txt` is more reliable and includes all necessary dependencies like boto3, opensearch-py, and other packages that the chat function needs.
