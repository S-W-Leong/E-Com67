# Cross-Stack Layer Update Guide

## Quick Answer

**Q: Why does AdminInsightsStack have this error but ComputeStack doesn't?**

**A: ComputeStack uses its own layer (same-stack), AdminInsightsStack uses ComputeStack's layer (cross-stack). CDK creates automatic exports for cross-stack references, and CloudFormation blocks export updates while they're being imported.**

## The Error

```
E-Com67-ComputeStack | UPDATE_ROLLBACK_IN_PROGRESS
Cannot update export E-Com67-ComputeStack:ExportsOutputRefStrandsLayer61506D6089516553 
as it is in use by E-Com67-AdminInsightsStack
```

## Why This Happens

### Same-Stack vs Cross-Stack References

| Stack | Layer Location | Reference Type | Export Created? | Has Issue? |
|-------|---------------|----------------|-----------------|------------|
| ComputeStack | ComputeStack | Same-stack | ❌ No | ❌ No |
| AdminInsightsStack | ComputeStack | Cross-stack | ✅ Yes | ✅ Yes |

**ComputeStack** creates and uses the layer in the same CloudFormation stack:
```python
# In ComputeStack
self.strands_layer = _lambda.LayerVersion(...)  # Create
self.chat_function = _lambda.Function(
    layers=[self.strands_layer]  # Use in same stack
)
```
→ No export needed, no cross-stack issue

**AdminInsightsStack** uses the layer from a different stack:
```python
# In AdminInsightsStack
self.strands_layer = self.compute_stack.strands_layer  # Cross-stack reference
self.agent_function = _lambda.Function(
    layers=[self.strands_layer]  # Use from different stack
)
```
→ CDK creates automatic export, cross-stack issue when layer changes

### Why Only Strands Layer?

**Because we only changed the Strands layer!**

If you changed Powertools or Utils layers (which are also used cross-stack), you'd get the same error. The issue appears when you **change any exported resource**.

## The Solution

Deploy both stacks together so CloudFormation can coordinate the update:

```bash
cdk deploy E-Com67-ComputeStack E-Com67-AdminInsightsStack --require-approval never
```

This tells CloudFormation to:
1. Update ComputeStack with new layer
2. Update AdminInsightsStack to use new layer
3. Coordinate the export/import changes atomically

## Step-by-Step Fix

### Option 1: Manual Deployment (Recommended)

```bash
# From project root
cdk deploy E-Com67-ComputeStack E-Com67-AdminInsightsStack --require-approval never
```

### Option 2: Use the Pipeline (After First Manual Fix)

The pipeline has been updated to deploy stacks together:

```python
# In backend_pipeline_stack.py
"cdk deploy E-Com67-ComputeStack E-Com67-AdminInsightsStack --require-approval never --concurrency 2"
```

After the first manual deployment, the pipeline will handle future updates correctly.

## Why CloudFormation Blocks This

CloudFormation exports are **immutable while in use** to prevent breaking dependencies:

1. ComputeStack exports layer ARN
2. AdminInsightsStack imports that ARN
3. If ComputeStack tries to change the export, CloudFormation blocks it
4. This prevents AdminInsightsStack from getting an invalid value mid-update

## Prevention

To avoid this in the future:

1. **Always deploy dependent stacks together** when updating shared resources
2. **Use the pipeline** which now handles this correctly
3. **Understand which resources are cross-stack** (see below)

## Cross-Stack Resource Map

### Layers (from ComputeStack)

| Layer | Used By ComputeStack | Used By AdminInsightsStack | Cross-Stack? |
|-------|---------------------|---------------------------|--------------|
| Powertools | ✅ Yes | ✅ Yes | ✅ Yes |
| Utils | ✅ Yes | ✅ Yes | ✅ Yes |
| Strands | ✅ Yes | ✅ Yes | ✅ Yes |
| OpenSearch | ✅ Yes | ❌ No | ❌ No |
| Stripe | ✅ Yes | ❌ No | ❌ No |

**Implication**: Changing Powertools, Utils, or Strands layers requires deploying both stacks together.

### Tables (from DataStack)

Both ComputeStack and AdminInsightsStack import tables from DataStack using `Fn.import_value()`. These are also cross-stack references, but they rarely change.

## Technical Details

### How CDK Creates Exports

When you write:
```python
admin_insights_stack = AdminInsightsStack(
    compute_stack=compute_stack  # Pass stack reference
)
```

And then use:
```python
self.strands_layer = self.compute_stack.strands_layer
```

CDK automatically:
1. Creates a CloudFormation export in ComputeStack
2. Creates a CloudFormation import in AdminInsightsStack
3. Generates a unique export name (the long hash you see in the error)

### Layer Versioning

Lambda layers are versioned resources:
- Each content change creates a new LayerVersion
- The ARN includes the version number
- All functions must update to the new version
- Old versions remain until all references are removed

This is why atomic updates across stacks are crucial.

## Related Documentation

- [CDK_CROSS_STACK_REFERENCE_EXPLANATION.md](./CDK_CROSS_STACK_REFERENCE_EXPLANATION.md) - Detailed explanation
- [STRANDS_LAYER_OPENTELEMETRY_FIX.md](./STRANDS_LAYER_OPENTELEMETRY_FIX.md) - What we changed
- [STRANDS_LAYER_PYTHON_COMPATIBILITY.md](./STRANDS_LAYER_PYTHON_COMPATIBILITY.md) - Compatibility verification
