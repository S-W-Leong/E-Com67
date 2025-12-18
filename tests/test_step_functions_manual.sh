#!/bin/bash

# Manual Step Functions Testing Script
# Tests the checkout workflow end-to-end

set -e

echo "🧪 Testing E-Com67 Step Functions Checkout Workflow"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REGION=${AWS_REGION:-us-east-1}
STATE_MACHINE_NAME="e-com67-checkout-workflow"

# Get the state machine ARN
echo -e "${YELLOW}📡 Finding Step Functions state machine...${NC}"
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --region $REGION \
  --query "stateMachines[?name=='$STATE_MACHINE_NAME'].stateMachineArn" \
  --output text)

if [ -z "$STATE_MACHINE_ARN" ]; then
  echo -e "${RED}❌ State machine not found. Did you deploy the ComputeStack?${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Found state machine: $STATE_MACHINE_ARN${NC}"

# Test Case 1: Valid checkout with valid cart
echo -e "\n${YELLOW}Test 1: Valid Checkout${NC}"
echo "------------------------"

EXECUTION_INPUT_1='{
  "userId": "test-user-123",
  "orderId": "test-order-'$(date +%s)'",
  "items": [
    {
      "productId": "prod-1",
      "name": "Test Product 1",
      "price": 29.99,
      "quantity": 2,
      "itemTotal": 59.98
    },
    {
      "productId": "prod-2",
      "name": "Test Product 2",
      "price": 49.99,
      "quantity": 1,
      "itemTotal": 49.99
    }
  ],
  "subtotal": 109.97,
  "taxAmount": 8.80,
  "totalAmount": 118.77,
  "currency": "usd",
  "shippingAddress": {
    "street": "123 Test St",
    "city": "Seattle",
    "state": "WA",
    "zip": "98101",
    "country": "USA"
  }
}'

echo "Input:"
echo "$EXECUTION_INPUT_1" | jq .

echo -e "\n${YELLOW}🚀 Starting execution...${NC}"
EXECUTION_1=$(aws stepfunctions start-execution \
  --region $REGION \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --name "test-valid-checkout-$(date +%s)" \
  --input "$EXECUTION_INPUT_1" \
  --output json)

EXECUTION_ARN_1=$(echo "$EXECUTION_1" | jq -r '.executionArn')
echo -e "${GREEN}✅ Execution started: $EXECUTION_ARN_1${NC}"

# Wait for execution to complete
echo -e "${YELLOW}⏳ Waiting for execution to complete...${NC}"
sleep 5

STATUS_1=$(aws stepfunctions describe-execution \
  --region $REGION \
  --execution-arn "$EXECUTION_ARN_1" \
  --query 'status' \
  --output text)

echo -e "${GREEN}Status: $STATUS_1${NC}"

# Get execution history
echo -e "\n${YELLOW}📜 Execution History:${NC}"
aws stepfunctions get-execution-history \
  --region $REGION \
  --execution-arn "$EXECUTION_ARN_1" \
  --max-results 20 \
  --output json | jq '.events[] | {type: .type, timestamp: .timestamp}'

# Test Case 2: Invalid checkout (empty cart)
echo -e "\n\n${YELLOW}Test 2: Invalid Checkout (Empty Items)${NC}"
echo "----------------------------------------"

EXECUTION_INPUT_2='{
  "userId": "test-user-456",
  "orderId": "test-order-'$(date +%s)'",
  "items": [],
  "subtotal": 0,
  "taxAmount": 0,
  "totalAmount": 0,
  "currency": "usd"
}'

echo "Input:"
echo "$EXECUTION_INPUT_2" | jq .

echo -e "\n${YELLOW}🚀 Starting execution...${NC}"
EXECUTION_2=$(aws stepfunctions start-execution \
  --region $REGION \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --name "test-empty-cart-$(date +%s)" \
  --input "$EXECUTION_INPUT_2" \
  --output json)

EXECUTION_ARN_2=$(echo "$EXECUTION_2" | jq -r '.executionArn')
echo -e "${GREEN}✅ Execution started: $EXECUTION_ARN_2${NC}"

# Wait for execution
sleep 3

STATUS_2=$(aws stepfunctions describe-execution \
  --region $REGION \
  --execution-arn "$EXECUTION_ARN_2" \
  --query 'status' \
  --output text)

echo -e "${GREEN}Status: $STATUS_2${NC}"

# Summary
echo -e "\n\n${YELLOW}📊 Test Summary${NC}"
echo "==============="
echo -e "Test 1 (Valid Checkout): $STATUS_1"
echo -e "Test 2 (Empty Cart): $STATUS_2"
echo ""
echo -e "${GREEN}✅ Testing complete!${NC}"
echo ""
echo -e "${YELLOW}🔍 View detailed execution in AWS Console:${NC}"
echo "https://console.aws.amazon.com/states/home?region=$REGION#/statemachines/view/$STATE_MACHINE_ARN"
