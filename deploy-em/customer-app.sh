#!/bin/bash
set -e  # Exit on error

echo "=========================================="
echo "Deploying Customer App Frontend"
echo "=========================================="

# cd to customer app
cd ../frontends/customer-app

# install deps
echo "Installing dependencies..."
npm ci

# build frontend files (output will be in dist/)
echo "Building React application..."
npm run build

# Get S3 bucket name from CloudFormation stack
echo "Fetching S3 bucket name..."
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='CustomerBucketName'].OutputValue" \
  --output text)

if [ -z "$BUCKET_NAME" ]; then
  echo "Error: Could not find S3 bucket name. Make sure E-Com67-FrontendStack is deployed."
  exit 1
fi

echo "S3 Bucket: $BUCKET_NAME"

# Upload to S3 bucket
echo "Uploading files to S3..."
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# Get CloudFront distribution ID
echo "Fetching CloudFront distribution ID..."
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='CustomerDistributionId'].OutputValue" \
  --output text)

if [ -z "$DISTRIBUTION_ID" ]; then
  echo "Error: Could not find CloudFront distribution ID."
  exit 1
fi

echo "Distribution ID: $DISTRIBUTION_ID"

# Invalidate CloudFront cache
echo "Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "Invalidation created: $INVALIDATION_ID"

# Get the CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='CustomerUrl'].OutputValue" \
  --output text)

echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Customer App URL: $CLOUDFRONT_URL"
echo "Note: Cache invalidation may take a few minutes to complete."
echo "=========================================="