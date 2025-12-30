# Admin Insights Agent Lambda - Deployment Notes

## Task 12.1 Implementation Summary

The Admin Insights Agent Lambda function has been successfully added to the CDK stack (`stacks/admin_insights_stack.py`).

### What Was Implemented

1. **Lambda Function Configuration**
   - Runtime: Python 3.12
   - Handler: `handler.handler`
   - Timeout: 30 seconds
   - Memory: 512 MB
   - Function Name: `e-com67-admin-insights-agent`

2. **Environment Variables**
   - `MEMORY_ID`: Placeholder (needs to be updated - see below)
   - `GUARDRAIL_ID`: Automatically set from Bedrock Guardrail
   - `MODEL_ID`: `amazon.nova-pro-v1:0`
   - `ORDER_TRENDS_LAMBDA_ARN`: ARN of order trends tool
   - `SALES_INSIGHTS_LAMBDA_ARN`: ARN of sales insights tool
   - `PRODUCT_SEARCH_LAMBDA_ARN`: ARN of product search tool
   - `REGION`: AWS region
   - `POWERTOOLS_SERVICE_NAME`: `admin-insights-agent`
   - `LOG_LEVEL`: `INFO`

3. **IAM Permissions**
   - Attached `AgentExecutionRole` with permissions for:
     - Bedrock model invocation
     - Bedrock Guardrails
     - Bedrock AgentCore Memory
     - Lambda invocation for analytics tools

4. **Lambda Layers**
   - Powertools layer (AWS Lambda Powertools)
   - Utils layer (shared utilities)
   - Strands layer (Strands SDK for AgentCore)

5. **Tool Invocation Permissions**
   - Granted invoke permissions for:
     - Order Trends Lambda
     - Sales Insights Lambda
     - Product Search Lambda

6. **CloudFormation Exports**
   - Added `E-Com67-AdminInsightsAgentLambdaArn` export

## Prerequisites Before Deployment

### CRITICAL: Create AgentCore Memory

Before deploying the stack, you **MUST** create the AgentCore Memory resource:

```bash
# Run the memory creation script
python scripts/create_admin_insights_memory.py --region ap-southeast-1

# The script will output a MEMORY_ID like:
# MEMORY_ID=abc123def456...
```

### Update the Stack with Memory ID

After running the script, update the `memory_id` variable in `stacks/admin_insights_stack.py`:

```python
# In the _create_agent_lambda method, replace:
memory_id = "PLACEHOLDER_MEMORY_ID"  # TODO: Replace with actual memory ID from script

# With the actual memory ID:
memory_id = "abc123def456..."  # Your actual memory ID from the script
```

## Deployment Steps

1. **Create Memory** (if not already done):
   ```bash
   python scripts/create_admin_insights_memory.py
   ```

2. **Update Memory ID** in `stacks/admin_insights_stack.py`

3. **Synthesize Stack** (verify configuration):
   ```bash
   cdk synth E-Com67-AdminInsightsStack
   ```

4. **Deploy Stack**:
   ```bash
   cdk deploy E-Com67-AdminInsightsStack
   ```

## Verification

After deployment, verify the Lambda function:

```bash
# Check Lambda function exists
aws lambda get-function --function-name e-com67-admin-insights-agent --region ap-southeast-1

# Check environment variables
aws lambda get-function-configuration --function-name e-com67-admin-insights-agent --region ap-southeast-1 | jq '.Environment.Variables'
```

## Next Steps

According to the task list, the next tasks are:

- **Task 13**: Create API Gateway endpoints
  - REST API with CORS configuration
  - Cognito authorizer
  - `/admin/insights/chat` endpoint
  - `/admin/insights/session` endpoints

- **Task 14**: Implement guardrails integration
  - Update agent handler to apply guardrails
  - Handle guardrail violations

## Troubleshooting

### Issue: "Layer version does not exist" Error

**Symptom**: CDK deployment fails with "Layer version arn:aws:lambda:...:layer:e-com67-powertools:1 does not exist"

**Solution**: This has been fixed. The stack now uses `Fn::ImportValue` to dynamically import layer ARNs from ComputeStack exports, ensuring the correct layer versions are always used.

If you still encounter this error:
1. Ensure ComputeStack is deployed: `cdk deploy E-Com67-ComputeStack`
2. Verify layer exports exist:
   ```bash
   aws cloudformation describe-stacks --stack-name E-Com67-ComputeStack --region ap-southeast-1 --query 'Stacks[0].Outputs[?contains(OutputKey, `Layer`)]'
   ```

### Issue: "PLACEHOLDER_MEMORY_ID" Error

**Symptom**: Lambda function fails with error about invalid memory ID

**Solution**: You forgot to update the memory ID. Run the memory creation script and update the stack.

### Issue: Layer Not Found

**Symptom**: CDK deployment fails with "Layer version not found"

**Solution**: Ensure the layers are deployed first by deploying the ComputeStack:
```bash
cdk deploy E-Com67-ComputeStack
```

### Issue: Permission Denied for Tool Invocation

**Symptom**: Agent cannot invoke analytics tools

**Solution**: Verify the grant_invoke permissions are correctly set in the stack. The implementation includes these grants.

## Requirements Validation

This implementation satisfies:
- **Requirement 10.2**: Lambda function provisioned for agent runtime
- **Requirement 10.3**: IAM roles with least-privilege access configured
- All required environment variables set
- Proper timeout (30s) and memory (512MB) configuration
- X-Ray tracing enabled for observability
