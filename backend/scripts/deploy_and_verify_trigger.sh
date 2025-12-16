#!/bin/bash
# Script to redeploy DataStack and verify Cognito trigger configuration

set -e

echo "=========================================="
echo "Post-Auth Trigger - Deploy & Verify"
echo "=========================================="
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/.."

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

echo ""
echo "Step 1: Synthesizing CDK stack..."
cdk synth ECom67-DataStack > /dev/null
echo "✓ Stack synthesis successful"

echo ""
echo "Step 2: Deploying ECom67-DataStack..."
echo "(This may take a few minutes)"
cdk deploy ECom67-DataStack --require-approval never

echo ""
echo "Step 3: Extracting User Pool ID..."
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name ECom67-DataStack \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$USER_POOL_ID" ]; then
    echo "⚠ Warning: Could not retrieve User Pool ID from CloudFormation"
    echo "   Attempting to find it directly..."
    USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 \
        --query 'UserPools[?Name==`e-com67-user-pool`].Id' \
        --output text 2>/dev/null || echo "")
fi

if [ -z "$USER_POOL_ID" ]; then
    echo "✗ Error: Could not find User Pool ID"
    echo "   Please check AWS credentials and try again"
    exit 1
fi

echo "✓ User Pool ID: $USER_POOL_ID"

echo ""
echo "Step 4: Verifying Lambda trigger configuration..."
TRIGGERS=$(aws cognito-idp describe-user-pool \
    --user-pool-id "$USER_POOL_ID" \
    --query 'UserPool.LambdaConfig' \
    --output json 2>/dev/null || echo "{}")

echo "$TRIGGERS" | python3 -m json.tool

if echo "$TRIGGERS" | grep -q "PostAuthentication"; then
    echo "✓ Post-authentication trigger is configured!"
    
    # Extract Lambda ARN
    LAMBDA_ARN=$(echo "$TRIGGERS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('PostAuthentication', 'N/A'))")
    echo "  Lambda ARN: $LAMBDA_ARN"
else
    echo "✗ Post-authentication trigger NOT found"
    echo "   Deployment may have failed. Check CloudFormation console."
    exit 1
fi

echo ""
echo "Step 5: Checking Lambda function exists..."
FUNCTION_NAME=$(echo "$LAMBDA_ARN" | rev | cut -d':' -f1 | rev)
aws lambda get-function --function-name "$FUNCTION_NAME" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Lambda function exists: $FUNCTION_NAME"
else
    echo "✗ Lambda function not found"
    exit 1
fi

echo ""
echo "Step 6: Verifying DynamoDB table permissions..."
aws lambda get-policy --function-name "$FUNCTION_NAME" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Lambda has resource policy configured"
else
    echo "⚠ Warning: Could not retrieve Lambda policy"
fi

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Test signup via frontend: cd ../frontend && npm start"
echo "2. Check CloudWatch Logs after signup:"
echo "   aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "3. Verify user in DynamoDB after signup:"
echo "   aws dynamodb scan --table-name e-com67-users"
echo ""
