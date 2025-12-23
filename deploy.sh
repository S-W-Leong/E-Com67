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
mkdir -p layers/strands/python/lib/python3.10/site-packages

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

# Install strands layer dependencies (requires Python 3.10+)
if [ -f "layers/strands/python/requirements.txt" ]; then
    echo "🤖 Installing Strands SDK layer dependencies..."
    cd layers/strands/python
    # Check if python3.10 is available
    if command -v python3.10 &> /dev/null; then
        echo "   Using Python 3.10 for Strands SDK (required for compatibility)"
        python3.10 -m pip install -r requirements.txt -t lib/python3.10/site-packages/ || {
            echo "⚠️  Warning: Failed to install Strands SDK packages"
            echo "   This may be due to package availability or Python version issues"
            echo "   Continuing deployment without Strands layer..."
        }
    else
        echo "⚠️  Warning: Python 3.10 not found, but required for Strands SDK"
        echo "   Strands packages require Python 3.10+, but only found:"
        python3 --version
        echo "   Continuing deployment without Strands layer..."
    fi
    cd ../../../
else
    echo "ℹ️  Strands layer requirements.txt not found, skipping Strands SDK installation"
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