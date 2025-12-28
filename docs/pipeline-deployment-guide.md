# E-Com67 CI/CD Pipeline Deployment Guide

This guide provides detailed instructions for deploying and managing the E-Com67 CI/CD pipelines.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment Steps](#deployment-steps)
- [Pipeline Management](#pipeline-management)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

E-Com67 uses a **three-pipeline architecture** for complete automation:

1. **Backend Pipeline** (`e-com67-backend-pipeline`)
   - Deploys infrastructure stacks (Data, Compute, API)
   - Builds Lambda layers
   - Manages backend resources

2. **Admin Dashboard Pipeline** (`e-com67-admin-dashboard-pipeline`)
   - Builds admin React application
   - Deploys to S3
   - Invalidates CloudFront cache

3. **Customer App Pipeline** (`e-com67-customer-app-pipeline`)
   - Builds customer React application
   - Deploys to S3
   - Invalidates CloudFront cache

### Why Three Pipelines?

**Separation of Concerns:**
- Backend and frontend have different build processes
- Independent deployment cycles
- Faster feedback loops (frontend changes don't trigger backend deployment)

**Flexibility:**
- Deploy backend infrastructure independently
- Update frontends without touching infrastructure
- Different teams can own different pipelines

**Cost Optimization:**
- Only build what changed
- Shorter build times = lower costs
- Parallel deployments when possible

---

## Architecture

### Pipeline Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      CodeCommit Repository (master)                       │
└────────────┬─────────────────────────┬─────────────────────────┬─────────┘
             │                         │                         │
             ▼                         ▼                         ▼
┌────────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│  Backend Pipeline      │  │  Admin Pipeline    │  │  Customer Pipeline │
├────────────────────────┤  ├────────────────────┤  ├────────────────────┤
│ 1. Source (CodeCommit) │  │ 1. Source          │  │ 1. Source          │
│ 2. Synth (CDK + Layers)│  │ 2. Build (npm)     │  │ 2. Build (npm)     │
│ 3. Deploy:             │  │ 3. Deploy (S3)     │  │ 3. Deploy (S3)     │
│    - DataStack         │  │ 4. Invalidate CF   │  │ 4. Invalidate CF   │
│    - ComputeStack      │  │                    │  │                    │
│    - ApiStack          │  │                    │  │                    │
└────────────────────────┘  └────────────────────┘  └────────────────────┘
             │                         │                         │
             ▼                         ▼                         ▼
┌────────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│  CloudFormation        │  │  S3 + CloudFront   │  │  S3 + CloudFront   │
│  Stacks Deployed       │  │  Admin Dashboard   │  │  Customer App      │
└────────────────────────┘  └────────────────────┘  └────────────────────┘
```

### Stack Dependencies

```
FrontendStack (S3 + CloudFront)
    │
    ├─► AdminPipelineStack
    └─► CustomerPipelineStack

BackendPipelineStack (Independent)
    │
    └─► Deploys: DataStack → ComputeStack → ApiStack
```

---

## Prerequisites

### 1. AWS Account Setup

- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Region: `ap-southeast-1` (or your preferred region)

### 2. Development Tools

```bash
# Check versions
python3 --version  # 3.9+
node --version     # 18+
npm --version      # 9+
aws --version      # 2.x
cdk --version      # 2.x
```

### 3. CodeCommit Repository

Create the repository if it doesn't exist:

```bash
aws codecommit create-repository \
  --repository-name e-com67 \
  --repository-description "E-Com67 Platform Source Code" \
  --region ap-southeast-1
```

Add as remote and push:

```bash
git remote add codecommit https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/e-com67
git push codecommit master
```

### 4. CDK Bootstrap

Ensure CDK is bootstrapped in your account:

```bash
cdk bootstrap aws://ACCOUNT-ID/ap-southeast-1
```

---

## Deployment Steps

### Option 1: Interactive Deployment (Recommended)

Use the provided helper script:

```bash
./deploy_pipelines.sh
```

Follow the interactive menu to:
1. Check prerequisites
2. Deploy backend pipeline
3. Deploy frontend stack
4. Deploy frontend pipelines
5. Monitor status

### Option 2: Manual Deployment

#### Step 1: Destroy Old Pipeline (If Exists)

```bash
# Check if old pipeline exists
aws cloudformation describe-stacks --stack-name E-Com67-PipelineStack

# If it exists, destroy it
cdk destroy E-Com67-PipelineStack --force
```

#### Step 2: Deploy Backend Pipeline

```bash
# Set environment variable
export USE_BACKEND_PIPELINE=true

# Deploy the pipeline stack
cdk deploy E-Com67-BackendPipelineStack --require-approval never

# Verify deployment
aws codepipeline get-pipeline-state --name e-com67-backend-pipeline
```

**What This Creates:**
- CodePipeline with 3 stages (Source, Synth, Deploy)
- CodeBuild project for CDK synthesis
- IAM roles and policies
- EventBridge rule for automatic triggering

**First Run:**
The pipeline will automatically execute after deployment, deploying:
1. DataStack (DynamoDB, Cognito, OpenSearch, S3)
2. ComputeStack (Lambda functions and layers)
3. ApiStack (API Gateway)

#### Step 3: Deploy Frontend Stack

```bash
# Deploy S3 buckets and CloudFront distributions
cdk deploy E-Com67-FrontendStack --require-approval never

# Get the outputs
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs" \
  --output table
```

**What This Creates:**
- S3 bucket for admin dashboard
- S3 bucket for customer app
- CloudFront distribution for admin dashboard
- CloudFront distribution for customer app
- Origin Access Identities for secure access

#### Step 4: Deploy Frontend Pipelines

```bash
# Set environment variable
export USE_FRONTEND_PIPELINES=true

# Deploy both frontend pipelines
cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack --require-approval never

# Verify deployments
aws codepipeline get-pipeline-state --name e-com67-admin-dashboard-pipeline
aws codepipeline get-pipeline-state --name e-com67-customer-app-pipeline
```

**What This Creates:**
- CodePipeline for admin dashboard
- CodePipeline for customer app
- CodeBuild projects for npm builds
- CodeBuild projects for CloudFront invalidation
- IAM roles and policies

---

## Pipeline Management

### Triggering Pipelines

**Automatic Trigger:**
All pipelines trigger automatically on push to `master`:

```bash
git add .
git commit -m "Update feature X"
git push codecommit master
```

**Manual Trigger:**

```bash
# Backend pipeline
aws codepipeline start-pipeline-execution --name e-com67-backend-pipeline

# Admin dashboard pipeline
aws codepipeline start-pipeline-execution --name e-com67-admin-dashboard-pipeline

# Customer app pipeline
aws codepipeline start-pipeline-execution --name e-com67-customer-app-pipeline
```

### Monitoring Pipelines

**View Pipeline Status:**

```bash
# Backend pipeline
aws codepipeline get-pipeline-state --name e-com67-backend-pipeline \
  --query 'stageStates[*].[stageName,latestExecution.status]' \
  --output table

# Admin dashboard pipeline
aws codepipeline get-pipeline-state --name e-com67-admin-dashboard-pipeline \
  --query 'stageStates[*].[stageName,latestExecution.status]' \
  --output table

# Customer app pipeline
aws codepipeline get-pipeline-state --name e-com67-customer-app-pipeline \
  --query 'stageStates[*].[stageName,latestExecution.status]' \
  --output table
```

**View Execution History:**

```bash
aws codepipeline list-pipeline-executions \
  --pipeline-name e-com67-backend-pipeline \
  --max-items 10
```

**View Build Logs:**

```bash
# Get the latest build ID
BUILD_ID=$(aws codebuild list-builds-for-project \
  --project-name <project-name> \
  --query 'ids[0]' \
  --output text)

# View logs
aws codebuild batch-get-builds --ids $BUILD_ID \
  --query 'builds[0].logs.deepLink' \
  --output text
```

### Updating Pipelines

**Backend Pipeline:**

```bash
# Make changes to stacks/backend_pipeline_stack.py
# Then redeploy
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack
```

**Frontend Pipelines:**

```bash
# Make changes to stacks/admin_pipeline_stack.py or stacks/customer_pipeline_stack.py
# Then redeploy
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack
```

### Pausing/Resuming Pipelines

**Disable Pipeline:**

```bash
aws codepipeline disable-stage-transition \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --transition-type Inbound \
  --reason "Maintenance window"
```

**Enable Pipeline:**

```bash
aws codepipeline enable-stage-transition \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --transition-type Inbound
```

---

## Troubleshooting

### Backend Pipeline Issues

#### Issue: Pipeline Not Triggering

**Symptoms:**
- Push to master doesn't trigger pipeline
- No new executions in pipeline history

**Solutions:**

1. Check EventBridge rule:
```bash
aws events list-rules --name-prefix e-com67
```

2. Verify repository name:
```bash
aws codecommit get-repository --repository-name e-com67
```

3. Check branch name (must be `master`):
```bash
git branch --show-current
```

#### Issue: CDK Synth Fails

**Symptoms:**
- Build stage fails with CDK errors
- CloudFormation template not generated

**Solutions:**

1. Test locally:
```bash
USE_BACKEND_PIPELINE=true cdk synth
```

2. Check Python dependencies:
```bash
pip install -r requirements.txt
```

3. Review CodeBuild logs for specific errors

#### Issue: Lambda Layer Build Fails

**Symptoms:**
- Build stage fails during layer installation
- Import errors in Lambda functions

**Solutions:**

1. Verify requirements.txt files exist:
```bash
ls layers/*/requirements.txt
```

2. Test layer build locally:
```bash
pip install -r layers/powertools/requirements.txt -t layers/powertools/python/
```

3. Check for architecture-specific dependencies

### Frontend Pipeline Issues

#### Issue: npm Build Fails

**Symptoms:**
- Build stage fails with npm errors
- Missing dependencies or syntax errors

**Solutions:**

1. Test build locally:
```bash
cd frontends/admin-dashboard  # or customer-app
npm ci
npm run build
```

2. Check package.json for correct scripts:
```json
{
  "scripts": {
    "build": "vite build",
    "lint": "eslint ."
  }
}
```

3. Verify Node.js version in buildspec matches local

#### Issue: S3 Deployment Fails

**Symptoms:**
- Deploy stage fails
- Access denied errors

**Solutions:**

1. Check S3 bucket permissions:
```bash
aws s3api get-bucket-policy --bucket e-com67-admin-dashboard-ACCOUNT
```

2. Verify CodePipeline role has S3 permissions

3. Check bucket exists:
```bash
aws s3 ls | grep e-com67
```

#### Issue: CloudFront Invalidation Fails

**Symptoms:**
- Invalidation stage fails
- Old content still served

**Solutions:**

1. Check distribution status:
```bash
aws cloudfront get-distribution --id DISTRIBUTION_ID
```

2. Verify IAM permissions for invalidation

3. Manual invalidation:
```bash
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*"
```

### General Issues

#### Issue: Pipeline Stuck

**Symptoms:**
- Pipeline execution in progress for too long
- No error messages

**Solutions:**

1. Check stage details:
```bash
aws codepipeline get-pipeline-execution \
  --pipeline-name e-com67-backend-pipeline \
  --pipeline-execution-id EXECUTION_ID
```

2. Stop execution:
```bash
aws codepipeline stop-pipeline-execution \
  --pipeline-name e-com67-backend-pipeline \
  --pipeline-execution-id EXECUTION_ID \
  --abandon
```

3. Retry:
```bash
aws codepipeline retry-stage-execution \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --pipeline-execution-id EXECUTION_ID \
  --retry-mode FAILED_ACTIONS
```

---

## Best Practices

### 1. Version Control

- Always commit and push to CodeCommit
- Use meaningful commit messages
- Tag releases for easy rollback

### 2. Testing Before Push

```bash
# Test CDK synth
USE_BACKEND_PIPELINE=true cdk synth

# Test frontend builds
cd frontends/admin-dashboard && npm run build
cd frontends/customer-app && npm run build

# Run tests
python -m pytest tests/
```

### 3. Monitoring

- Set up CloudWatch alarms for pipeline failures
- Monitor CodeBuild costs
- Track deployment frequency

### 4. Security

- Regularly rotate IAM credentials
- Review pipeline IAM roles
- Enable CloudTrail for audit logs
- Use Secrets Manager for sensitive data

### 5. Cost Optimization

- Use caching in CodeBuild
- Optimize build times
- Clean up old artifacts
- Monitor S3 storage costs

### 6. Rollback Strategy

**Backend:**
```bash
# Rollback to previous stack version
aws cloudformation rollback-stack --stack-name E-Com67-ComputeStack
```

**Frontend:**
```bash
# Restore previous S3 version
aws s3api list-object-versions --bucket e-com67-admin-dashboard-ACCOUNT
aws s3api copy-object --copy-source "bucket/key?versionId=VERSION" ...
```

---

## Additional Resources

- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [AWS CDK Pipelines](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.pipelines-readme.html)
- [CloudFront Invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- [E-Com67 Main README](../README.md)

---

## Support

For issues or questions:
1. Check this guide and main README
2. Review CloudWatch logs
3. Check AWS service health dashboard
4. Open an issue in the repository
