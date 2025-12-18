#!/bin/bash

# Script to set up Stripe API key in AWS Secrets Manager
# Usage: ./scripts/setup-stripe-secret.sh <your-stripe-secret-key>

set -e

echo "🔐 Setting up Stripe API Key in AWS Secrets Manager"
echo "=================================================="

# Check if Stripe API key is provided
if [ -z "$1" ]; then
  echo "❌ Error: Stripe API key not provided"
  echo ""
  echo "Usage: $0 <stripe-secret-key>"
  echo ""
  echo "Example:"
  echo "  $0 sk_test_51ABC123..."
  echo ""
  echo "To get your Stripe test key:"
  echo "  1. Go to https://dashboard.stripe.com/test/apikeys"
  echo "  2. Copy the 'Secret key' (starts with sk_test_...)"
  echo "  3. Run this script with that key"
  exit 1
fi

STRIPE_KEY="$1"
SECRET_NAME="e-com67/stripe/api-key"
REGION="${AWS_REGION:-ap-southeast-1}"

# Validate the key format
if [[ ! "$STRIPE_KEY" =~ ^sk_(test|live)_ ]]; then
  echo "⚠️  Warning: The provided key doesn't look like a valid Stripe secret key"
  echo "   Expected format: sk_test_... or sk_live_..."
  echo "   Provided: ${STRIPE_KEY:0:10}..."
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Check if using test or live key
if [[ "$STRIPE_KEY" =~ ^sk_test_ ]]; then
  echo "✅ Using Stripe TEST key (safe for development)"
elif [[ "$STRIPE_KEY" =~ ^sk_live_ ]]; then
  echo "⚠️  WARNING: Using Stripe LIVE key (real payments!)"
  read -p "Are you sure you want to use a LIVE key? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Create JSON payload
SECRET_VALUE=$(cat <<EOF
{"api_key":"$STRIPE_KEY"}
EOF
)

echo ""
echo "📡 Checking if secret exists..."

# Check if secret exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
  echo "✅ Secret exists, updating value..."

  # Update existing secret
  aws secretsmanager put-secret-value \
    --secret-id "$SECRET_NAME" \
    --secret-string "$SECRET_VALUE" \
    --region "$REGION" \
    --output json > /dev/null

  echo "✅ Secret updated successfully!"

else
  echo "⚠️  Secret doesn't exist yet"
  echo "   The CDK stack will create it automatically"
  echo "   Please run: cdk deploy E-Com67-DataStack E-Com67-ComputeStack"
  echo "   Then run this script again"
  exit 1
fi

echo ""
echo "🔍 Verifying secret..."

# Verify the secret was set correctly
RETRIEVED_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --region "$REGION" \
  --query 'SecretString' \
  --output text)

if echo "$RETRIEVED_SECRET" | grep -q "api_key"; then
  echo "✅ Secret verified successfully!"
  echo ""
  echo "Secret structure:"
  echo "$RETRIEVED_SECRET" | jq .
else
  echo "❌ Secret verification failed"
  exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Deploy the updated Lambda: cdk deploy E-Com67-ComputeStack"
echo "  2. Run your tests: python3 tests/test_checkout_integration.py"
echo ""
echo "Note: The secret is stored in region: $REGION"
