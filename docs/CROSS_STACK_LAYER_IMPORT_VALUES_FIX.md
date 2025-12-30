# Cross-Stack Layer Import Values Fix

## Problem Summary

AdminInsightsStack was experiencing deployment failures with the error:
```
Cannot update export E-Com67-ComputeStack:ExportsOutputRefStrandsLayer61506D6089516553 as it is in use by E-Com67-AdminInsightsStack
```

This occurred because AdminInsightsStack used direct CDK references to ComputeStack layers, which automatically created CloudFormation exports that couldn't be updated while in use.

## Root Cause Analysis

1. **Direct CDK References**: AdminInsightsStack used `self.compute_stack.powertools_layer` to access layers
2. **Automatic Exports**: CDK automatically created CloudFormation exports for these cross-stack references
3. **Update Conflicts**: When ComputeStack layers changed, CloudFormation couldn't update the exports while AdminInsightsStack was using them
4. **Sequential Processing**: Even deploying both stacks together didn't work because CloudFormation processes them sequentially

## Solution: Import Values Approach

Switched AdminInsightsStack to use the same pattern as ApiStack:

### 1. ComputeStack Changes
- **Added explicit layer exports** in `_create_exports()` method:
  - `E-Com67-PowertoolsLayerArn`
  - `E-Com67-UtilsLayerArn` 
  - `E-Com67-StrandsLayerArn`
  - `E-Com67-StripeLayerArn`
  - `E-Com67-OpenSearchLayerArn`

### 2. AdminInsightsStack Changes
- **Modified `_create_lambda_layers()`** to use `Fn.import_value()`:
  ```python
  self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
      self, "ImportedPowertoolsLayer",
      layer_version_arn=Fn.import_value("E-Com67-PowertoolsLayerArn")
  )
  ```
- **Removed `compute_stack` parameter** from constructor
- **Uses `LayerVersion.from_layer_version_arn()`** to create layer references

### 3. App.py Changes
- **Removed `compute_stack` parameter** from AdminInsightsStack instantiation
- **Kept explicit dependency** with `add_dependency(compute_stack)`

## Why This Works

1. **No Automatic Exports**: `Fn.import_value()` doesn't create automatic CloudFormation exports
2. **Explicit Control**: ComputeStack explicitly controls what gets exported
3. **Independent Updates**: Each stack can be updated independently without cross-stack conflicts
4. **Same Pattern**: Matches the proven approach used by ApiStack

## Comparison with ApiStack

ApiStack successfully uses this pattern for function ARNs:
```python
# ApiStack uses Fn.import_value for function ARNs
product_crud_function_arn=Fn.import_value("E-Com67-ProductCrudFunctionArn")
```

AdminInsightsStack now uses the same pattern for layer ARNs:
```python
# AdminInsightsStack uses Fn.import_value for layer ARNs  
layer_version_arn=Fn.import_value("E-Com67-PowertoolsLayerArn")
```

## Deployment Process

1. **Deploy ComputeStack first**: Creates layers and exports their ARNs
2. **Deploy AdminInsightsStack**: Imports layer ARNs and creates layer references
3. **Updates work independently**: Each stack can be updated without affecting the other

## Files Modified

- `stacks/compute_stack.py`: Added explicit layer ARN exports
- `stacks/admin_insights_stack.py`: Modified to use import values approach
- `app.py`: Removed compute_stack parameter, kept dependency
- `docs/CROSS_STACK_LAYER_IMPORT_VALUES_FIX.md`: This documentation

## Testing

After implementing this fix:
1. Deploy ComputeStack: `cdk deploy E-Com67-ComputeStack`
2. Deploy AdminInsightsStack: `cdk deploy E-Com67-AdminInsightsStack`
3. Verify both stacks can be updated independently
4. Test layer updates don't cause cross-stack conflicts

## Benefits

- **Eliminates cross-stack export conflicts**
- **Allows independent stack updates**
- **Follows proven ApiStack pattern**
- **Maintains proper dependency management**
- **Simplifies AdminInsightsStack constructor**