# Lambda Layer Reference Fix

## Problem

The initial deployment of the AdminInsightsStack failed with the following error:

```
Layer version arn:aws:lambda:ap-southeast-1:724542698940:layer:e-com67-powertools:1 does not exist.
```

This occurred for all three layers:
- `e-com67-powertools:1`
- `e-com67-utils:1`
- `e-com67-strands:1`

## Root Cause

The stack was hardcoding layer version numbers to `:1`, but the actual deployed layers had different version numbers:
- `e-com67-powertools:12`
- `e-com67-utils:5`
- `e-com67-strands:26`

Layer versions increment each time they're updated, so hardcoding version `:1` was incorrect.

## Solution

Changed the layer references from hardcoded ARNs to CloudFormation imports:

### Before (Incorrect)
```python
self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
    self, "PowertoolsLayerRef",
    layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:e-com67-powertools:1"
)
```

### After (Correct)
```python
self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
    self, "PowertoolsLayerRef",
    layer_version_arn=Fn.import_value("E-Com67-PowertoolsLayerArn")
)
```

## Benefits

1. **Dynamic Version Resolution**: Always uses the current layer version from ComputeStack
2. **No Manual Updates**: Layer version changes in ComputeStack automatically propagate
3. **Cross-Stack Consistency**: Ensures all stacks use the same layer versions
4. **Deployment Safety**: CloudFormation validates that referenced layers exist

## Implementation Details

The fix was applied to all three layers in `stacks/admin_insights_stack.py`:

```python
def _create_lambda_layers(self):
    """Reference Lambda layers from ComputeStack using CloudFormation imports"""
    # Import layer ARNs from ComputeStack exports
    # This ensures we always use the correct layer versions
    self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "PowertoolsLayerRef",
        layer_version_arn=Fn.import_value("E-Com67-PowertoolsLayerArn")
    )
    
    self.utils_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "UtilsLayerRef",
        layer_version_arn=Fn.import_value("E-Com67-UtilsLayerArn")
    )
    
    self.strands_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "StrandsLayerRef",
        layer_version_arn=Fn.import_value("E-Com67-StrandsLayerArn")
    )
```

## Verification

After the fix, the CloudFormation template correctly references the layers:

```yaml
Layers:
  - Fn::ImportValue: E-Com67-PowertoolsLayerArn
  - Fn::ImportValue: E-Com67-UtilsLayerArn
  - Fn::ImportValue: E-Com67-StrandsLayerArn
```

## Deployment Status

- ✓ Failed stack cleaned up
- ✓ Layer references fixed
- ✓ CDK synthesis successful
- ⏳ Ready for redeployment

## Next Steps

The stack is now ready for deployment:

```bash
cdk deploy E-Com67-AdminInsightsStack
```

Note: You still need to create the AgentCore Memory and update the MEMORY_ID before the Lambda function will work correctly.
