#!/bin/bash

# E-Com67 Platform Deployment Script
# This script deploys the CDK stacks in the correct order

set -e

echo "Starting E-Com67 Platform deployment..."

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed


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

# Might need to deploy this stack tgt with the frontend pipeline stacks cuz pipeline depends on this output
echo "Deploying Frontend Stack..."
cdk deploy E-Com67-FrontendStack --require-approval never

echo "Deploying Backend Pipeline Stack..."
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack --require-approval never

echo "Deploying Frontend Pipeline Stacks (Admin & Customer)..."
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack --require-approval never

echo "Deploying AdminInsightsStack..." 
cdk deploy E-Com67-AdminInsightsStack --require-approval never