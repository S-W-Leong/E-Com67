# Nuclear Option: Fix Cross-Stack Layer Issue

## Problem

Even deploying both stacks together fails with:
```
Cannot update export E-Com67-ComputeStack:ExportsOutputRefStrandsLayer61506D6089516553 
as it is in use by E-Com67-AdminInsightsStack
```

This suggests CloudFormation is still processing the stacks sequentially, not atomically.

## Nuclear Option: Temporarily Break the Dependency

Since the coordinated deployment isn't working, we need to temporarily break the cross-stack dependency, then restore it.

### Step 1: Modify AdminInsightsStack to Not Use Strands Layer

Temporarily comment out the Strands layer usage:

```python
# In stacks/admin_insights_stack.py
def _create_lambda_layers(self):
    self.powertools_layer = self.compute_stack.powertools_layer
    self.utils_layer = self.compute_stack.utils_layer
    # TEMPORARILY COMMENT OUT - will restore after ComputeStack updates
    # self.strands_layer = self.compute_stack.strands_layer
```

And update all Lambda functions to not use the Strands layer:

```python
# In all Lambda function definitions, change from:
layers=[self.powertools_layer, self.utils_layer, self.strands_layer]

# To:
layers=[self.powertools_layer, self.utils_layer]
# TODO: Add strands_layer back after ComputeStack update
```

### Step 2: Deploy AdminInsightsStack Without Strands Layer

```bash
cdk deploy E-Com67-AdminInsightsStack --require-approval never
```

This removes the cross-stack dependency on the Strands layer.

### Step 3: Deploy ComputeStack With Updated Layer

```bash
cdk deploy E-Com67-ComputeStack --require-approval never
```

Now ComputeStack can update freely since no other stack is referencing the Strands layer.

### Step 4: Restore Strands Layer Usage

Uncomment the Strands layer code:

```python
# In stacks/admin_insights_stack.py
def _create_lambda_layers(self):
    self.powertools_layer = self.compute_stack.powertools_layer
    self.utils_layer = self.compute_stack.utils_layer
    self.strands_layer = self.compute_stack.strands_layer  # ← Restore this
```

And restore Lambda function layers:

```python
layers=[self.powertools_layer, self.utils_layer, self.strands_layer]  # ← Restore
```

### Step 5: Deploy AdminInsightsStack With Strands Layer

```bash
cdk deploy E-Com67-AdminInsightsStack --require-approval never
```

Now AdminInsightsStack will use the updated Strands layer.

## Alternative: Use Import Values (Cleaner)

Instead of the nuclear option, let's implement the import values approach properly:

### Step 1: Add Layer Exports to ComputeStack

```python
# In stacks/compute_stack.py, add at the end of __init__:
CfnOutput(
    self, "StrandsLayerArn",
    value=self.strands_layer.layer_version_arn,
    export_name="E-Com67-StrandsLayerArn",
    description="ARN of the Strands layer"
)

CfnOutput(
    self, "PowertoolsLayerArn", 
    value=self.powertools_layer.layer_version_arn,
    export_name="E-Com67-PowertoolsLayerArn",
    description="ARN of the Powertools layer"
)

CfnOutput(
    self, "UtilsLayerArn",
    value=self.utils_layer.layer_version_arn, 
    export_name="E-Com67-UtilsLayerArn",
    description="ARN of the Utils layer"
)
```

### Step 2: Modify AdminInsightsStack to Import Layer ARNs

```python
# In stacks/admin_insights_stack.py
def _create_lambda_layers(self):
    # Import layer ARNs instead of direct references
    self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "ImportedPowertoolsLayer",
        layer_version_arn=Fn.import_value("E-Com67-PowertoolsLayerArn")
    )
    
    self.utils_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "ImportedUtilsLayer", 
        layer_version_arn=Fn.import_value("E-Com67-UtilsLayerArn")
    )
    
    self.strands_layer = _lambda.LayerVersion.from_layer_version_arn(
        self, "ImportedStrandsLayer",
        layer_version_arn=Fn.import_value("E-Com67-StrandsLayerArn")
    )
```

### Step 3: Remove compute_stack Parameter

```python
# In stacks/admin_insights_stack.py constructor
def __init__(self, scope: Construct, construct_id: str, data_stack, **kwargs):
    # Remove compute_stack parameter since we're importing values instead
```

### Step 4: Update app.py

```python
# In app.py
admin_insights_stack = AdminInsightsStack(
    app,
    "E-Com67-AdminInsightsStack", 
    data_stack=data_stack,  # Remove compute_stack parameter
    env=env,
    description="E-Com67 Platform - Admin Insights Agent with Bedrock AgentCore"
)
# Keep the dependency for deployment order
admin_insights_stack.add_dependency(compute_stack)
```

## Why Import Values Might Work Better

The import values approach creates **explicit CloudFormation exports** that are designed to be updated, rather than the **implicit exports** that CDK creates for direct references.

CloudFormation handles explicit exports differently - it knows they're meant to be shared and can coordinate updates better.

## Recommendation

Try the **Import Values approach** first (Steps 1-4 above) since it's cleaner and more maintainable than the nuclear option.

If that still doesn't work, then use the nuclear option as a last resort.