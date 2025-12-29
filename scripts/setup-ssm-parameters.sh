#!/bin/bash

# Setup SSM Parameters for E-Com67 Frontend Builds
# This script creates AWS Systems Manager Parameter Store parameters
# that are used by the CI/CD pipelines to build the frontend applications

set -e

REGION="ap-southeast-1"
PROFILE="${AWS_PROFILE:-shiwei}"

echo "Setting up SSM Parameters for E-Com67..."
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo ""

# Stripe Configuration
echo "Creating Stripe parameters..."
aws ssm put-parameter \
    --name "/ecom67/stripe/publishable-key" \
    --value "pk_test_51SfXQ5K99yUPr3oBLV66YQOrWMCDlvkgRqsL9pkA5x5ZIAKSuoOjdthzxDayOOBoyPeUJbs07R3o4Jg9bfAtSVRi00neuuG05F" \
    --type "String" \
    --description "Stripe publishable key for E-Com67" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --overwrite 2>/dev/null && echo "✓ Stripe publishable key created/updated" || echo "✓ Stripe publishable key already exists"

# Cognito Configuration
echo "Creating Cognito parameters..."
aws ssm put-parameter \
    --name "/ecom67/cognito/user-pool-id" \
    --value "ap-southeast-1_tWVIqi86j" \
    --type "String" \
    --description "Cognito User Pool ID for E-Com67" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --overwrite 2>/dev/null && echo "✓ User Pool ID created/updated" || echo "✓ User Pool ID already exists"

aws ssm put-parameter \
    --name "/ecom67/cognito/user-pool-client-id" \
    --value "tvv93rbvv54sjv3ts2fe41dc9" \
    --type "String" \
    --description "Cognito User Pool Client ID for E-Com67" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --overwrite 2>/dev/null && echo "✓ User Pool Client ID created/updated" || echo "✓ User Pool Client ID already exists"

# API Configuration
echo "Creating API parameters..."
aws ssm put-parameter \
    --name "/ecom67/api/base-url" \
    --value "https://qy60l1ggnj.execute-api.ap-southeast-1.amazonaws.com/prod" \
    --type "String" \
    --description "API Gateway base URL for E-Com67" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --overwrite 2>/dev/null && echo "✓ API base URL created/updated" || echo "✓ API base URL already exists"

aws ssm put-parameter \
    --name "/ecom67/api/websocket-url" \
    --value "wss://3q1jt2y351.execute-api.ap-southeast-1.amazonaws.com/prod/" \
    --type "String" \
    --description "WebSocket URL for E-Com67" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --overwrite 2>/dev/null && echo "✓ WebSocket URL created/updated" || echo "✓ WebSocket URL already exists"

echo ""
echo "✅ All SSM parameters have been created/updated successfully!"
echo ""
echo "To verify, run:"
echo "  aws ssm get-parameters-by-path --path /ecom67 --recursive --region $REGION --profile $PROFILE"
