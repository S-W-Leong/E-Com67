#!/bin/bash

# E-Com67 Platform Deployment Script
# This script deploys the CDK stacks in the correct order

set -e

echo "🚀 Starting E-Com67 Platform deployment..."

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Build Lambda layers
echo "🔧 Building Lambda layers..."
mkdir -p layers/powertools/python/lib/python3.9/site-packages
mkdir -p layers/stripe/python/lib/python3.9/site-packages
mkdir -p layers/opensearch/python/lib/python3.9/site-packages
mkdir -p layers/utils/python/lib/python3.9/site-packages

# Install powertools layer dependencies
cd layers/powertools/python
pip install -r requirements.txt -t lib/python3.9/site-packages/
cd ../../../

# Install stripe layer dependencies  
cd layers/stripe/python
pip install -r requirements.txt -t lib/python3.9/site-packages/
cd ../../../

# Install opensearch layer dependencies
cd layers/opensearch/python
pip install -r requirements.txt -t lib/python3.9/site-packages/
cd ../../../

# Install utils layer dependencies (if requirements.txt exists)
if [ -f "layers/utils/python/requirements.txt" ]; then
    cd layers/utils/python
    pip install -r requirements.txt -t lib/python3.9/site-packages/
    cd ../../../
fi

# Synthesize CDK templates
echo "🏗️  Synthesizing CDK templates..."
cdk synth --all

# Deploy stacks in order
echo "☁️  Deploying Data Stack..."
cdk deploy E-Com67-DataStack --require-approval never

echo "⚡ Deploying Compute Stack..."
cdk deploy E-Com67-ComputeStack --require-approval never

echo "🌐 Deploying API Stack..."
cdk deploy E-Com67-ApiStack --require-approval never

echo "✅ Deployment complete!"
echo "📊 Check AWS Console for deployed resources"
echo "🔗 API Gateway URL will be displayed in the stack outputs"