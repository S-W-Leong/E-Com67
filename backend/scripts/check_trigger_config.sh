#!/bin/bash
# Quick check if the Cognito trigger is in the CloudFormation template

cd "$(dirname "$0")/.."

echo "Synthesizing CloudFormation template..."
cdk synth ECom67-DataStack --quiet > /tmp/ecom67-template.yaml 2>&1

echo ""
echo "Checking for LambdaConfig..."
if grep -q "LambdaConfig" /tmp/ecom67-template.yaml; then
    echo "✓ LambdaConfig found in template!"
    echo ""
    grep -B 2 -A 15 "LambdaConfig" /tmp/ecom67-template.yaml
else
    echo "✗ LambdaConfig NOT found in template"
    echo ""
    echo "Checking UserPool configuration..."
    grep -B 5 -A 20 "ECom67UserPool" /tmp/ecom67-template.yaml | head -30
fi

echo ""
echo "Template saved to: /tmp/ecom67-template.yaml"
