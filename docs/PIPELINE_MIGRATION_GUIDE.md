# E-Com67 Pipeline Migration Guide

This guide helps you migrate from the old single-pipeline architecture to the new three-pipeline architecture.

## Overview

### What's Changing?

**Old Architecture:**
```
E-Com67-PipelineStack
  └─► Deploys: Data + Compute + Api
```

**New Architecture:**
```
E-Com67-BackendPipelineStack
  └─► Deploys: Data + Compute + Api

E-Com67-FrontendStack
  ├─► E-Com67-AdminPipelineStack
  └─► E-Com67-CustomerPipelineStack
```

### Why Migrate?

1. **Frontend Automation:** Automated deployment for React applications
2. **Faster Builds:** Only build what changed
3. **Better Separation:** Independent deployment cycles
4. **Production Ready:** Follows AWS best practices

---

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] AWS CLI configured with appropriate credentials
- [ ] CDK CLI installed (`npm install -g aws-cdk`)
- [ ] Python 3.9+ with virtual environment activated
- [ ] CodeCommit repository set up and accessible
- [ ] Backup of current pipeline configuration
- [ ] Understanding of current deployment process
- [ ] Maintenance window scheduled (if in production)

---

## Migration Steps

### Step 1: Backup Current State

```bash
# Backup pipeline stack
aws cloudformation describe-stacks \
  --stack-name E-Com67-PipelineStack \
  > backup-pipeline-stack.json

# Backup pipeline configuration
aws codepipeline get-pipeline \
  --name e-com67-pipeline \
  > backup-pipeline-config.json

# List current stacks
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  > backup-stacks-list.json

# Backup environment variables
env | grep CDK > backup-env.txt
```

### Step 2: Verify Current Deployment

```bash
# Check pipeline status
aws codepipeline get-pipeline-state --name e-com67-pipeline

# Verify all stacks are healthy
aws cloudformation describe-stacks --stack-name E-Com67-DataStack
aws cloudformation describe-stacks --stack-name E-Com67-ComputeStack
aws cloudformation describe-stacks --stack-name E-Com67-ApiStack

# Note: If any stack is in UPDATE_IN_PROGRESS or other transitional state,
# wait for it to complete before proceeding
```

### Step 3: Update Code

```bash
# Pull latest code with new pipeline implementation
git pull origin master

# Or if you're implementing manually, ensure you have:
# - stacks/backend_pipeline_stack.py
# - stacks/frontend_stack.py
# - stacks/admin_pipeline_stack.py
# - stacks/customer_pipeline_stack.py
# - Updated app.py
# - deploy_pipelines.sh

# Verify files exist
ls -la stacks/*pipeline*.py
ls -la deploy_pipelines.sh
```

### Step 4: Destroy Old Pipeline

⚠️ **Important:** This will destroy the old pipeline but NOT the application stacks.

```bash
# Destroy the old pipeline stack
cdk destroy E-Com67-PipelineStack --force

# Verify destruction
aws cloudformation describe-stacks --stack-name E-Com67-PipelineStack
# Should return: Stack with id E-Com67-PipelineStack does not exist
```

**What Gets Deleted:**
- Old CodePipeline
- Old CodeBuild projects
- Old IAM roles (pipeline-specific)

**What Stays:**
- DataStack (DynamoDB, Cognito, OpenSearch, S3)
- ComputeStack (Lambda functions and layers)
- ApiStack (API Gateway)
- All application data

### Step 5: Deploy New Backend Pipeline

```bash
# Deploy the new backend pipeline
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack --require-approval never

# Wait for deployment to complete
# This will take 5-10 minutes

# Verify deployment
aws codepipeline get-pipeline-state --name e-com67-backend-pipeline
```

**What Gets Created:**
- New CodePipeline (e-com67-backend-pipeline)
- New CodeBuild projects
- New IAM roles
- EventBridge rule for automatic triggering

**First Execution:**
The pipeline will automatically execute after deployment, redeploying:
- DataStack (updates if needed)
- ComputeStack (updates if needed)
- ApiStack (updates if needed)

### Step 6: Deploy Frontend Stack

```bash
# Deploy S3 buckets and CloudFront distributions
cdk deploy E-Com67-FrontendStack --require-approval never

# Wait for deployment to complete
# This will take 10-15 minutes (CloudFront is slow)

# Get the outputs
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs" \
  --output table
```

**What Gets Created:**
- S3 bucket for admin dashboard
- S3 bucket for customer app
- CloudFront distribution for admin dashboard
- CloudFront distribution for customer app
- Origin Access Identities

### Step 7: Deploy Frontend Pipelines

```bash
# Deploy both frontend pipelines
USE_FRONTEND_PIPELINES=true cdk deploy \
  E-Com67-AdminPipelineStack \
  E-Com67-CustomerPipelineStack \
  --require-approval never

# Wait for deployment to complete
# This will take 3-5 minutes

# Verify deployments
aws codepipeline get-pipeline-state --name e-com67-admin-dashboard-pipeline
aws codepipeline get-pipeline-state --name e-com67-customer-app-pipeline
```

**What Gets Created:**
- CodePipeline for admin dashboard
- CodePipeline for customer app
- CodeBuild projects for npm builds
- CodeBuild projects for CloudFront invalidation

**First Execution:**
The pipelines will automatically execute, building and deploying the frontend applications.

### Step 8: Verify Migration

```bash
# Check all pipelines are running
./deploy_pipelines.sh
# Select option 5 (Show Pipeline Status)

# Verify backend stacks
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  | grep E-Com67

# Test API endpoints
curl https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/prod/products

# Test frontend URLs
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='AdminUrl'].OutputValue" \
  --output text

aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='CustomerUrl'].OutputValue" \
  --output text
```

### Step 9: Update Git Remote (If Needed)

```bash
# Verify CodeCommit remote
git remote -v

# If not set, add it
git remote add codecommit https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/e-com67

# Push to CodeCommit
git push codecommit master
```

### Step 10: Test Automatic Triggering

```bash
# Make a small change
echo "# Test change" >> README.md

# Commit and push
git add README.md
git commit -m "Test pipeline trigger"
git push codecommit master

# Watch pipelines trigger
watch -n 5 'aws codepipeline get-pipeline-state --name e-com67-backend-pipeline | grep status'
```

---

## Rollback Plan

If something goes wrong during migration:

### Rollback Step 1: Restore Old Pipeline

```bash
# Redeploy old pipeline from backup
USE_PIPELINE=true cdk deploy E-Com67-PipelineStack
```

### Rollback Step 2: Destroy New Pipelines

```bash
# Destroy new pipelines
cdk destroy E-Com67-BackendPipelineStack --force
cdk destroy E-Com67-AdminPipelineStack --force
cdk destroy E-Com67-CustomerPipelineStack --force
cdk destroy E-Com67-FrontendStack --force
```

### Rollback Step 3: Verify Old Pipeline

```bash
# Check old pipeline status
aws codepipeline get-pipeline-state --name e-com67-pipeline

# Trigger if needed
aws codepipeline start-pipeline-execution --name e-com67-pipeline
```

---

## Post-Migration Tasks

### 1. Update Documentation

- [ ] Update team documentation with new pipeline names
- [ ] Update deployment runbooks
- [ ] Update CI/CD documentation

### 2. Update Monitoring

- [ ] Add CloudWatch alarms for new pipelines
- [ ] Update dashboard with new pipeline metrics
- [ ] Configure SNS notifications (if desired)

### 3. Update Access Controls

- [ ] Review IAM permissions for new pipelines
- [ ] Update team access to CodePipeline console
- [ ] Document new deployment process

### 4. Clean Up

```bash
# Remove old pipeline artifacts (optional)
aws s3 ls | grep codepipeline-e-com67-pipeline
# If found, empty and delete the bucket

# Remove old CloudWatch log groups (optional)
aws logs describe-log-groups --log-group-name-prefix /aws/codebuild/e-com67-pipeline
# If found, delete the log groups
```

---

## Troubleshooting

### Issue: Old Pipeline Won't Destroy

**Symptoms:**
- `cdk destroy E-Com67-PipelineStack` fails
- Stack is stuck in DELETE_IN_PROGRESS

**Solutions:**

1. Check for dependencies:
```bash
aws cloudformation describe-stack-resources --stack-name E-Com67-PipelineStack
```

2. Force delete from console:
   - Go to CloudFormation console
   - Select E-Com67-PipelineStack
   - Actions → Delete Stack
   - Check "Retain resources" if needed

3. Manual cleanup:
```bash
# Delete pipeline
aws codepipeline delete-pipeline --name e-com67-pipeline

# Delete stack
aws cloudformation delete-stack --stack-name E-Com67-PipelineStack
```

### Issue: New Pipeline Fails to Deploy

**Symptoms:**
- `cdk deploy E-Com67-BackendPipelineStack` fails
- CloudFormation rollback occurs

**Solutions:**

1. Check CDK synth:
```bash
USE_BACKEND_PIPELINE=true cdk synth
```

2. Check for resource conflicts:
```bash
aws codepipeline get-pipeline --name e-com67-backend-pipeline
# Should return error if doesn't exist
```

3. Review CloudFormation events:
```bash
aws cloudformation describe-stack-events --stack-name E-Com67-BackendPipelineStack
```

### Issue: Frontend Stack Takes Too Long

**Symptoms:**
- CloudFront distribution creation takes 15+ minutes
- Deployment appears stuck

**Solutions:**

1. This is normal - CloudFront distributions take 10-20 minutes to create
2. Check status:
```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='E-Com67 Admin Dashboard CDN'].Status"
```

3. Wait patiently - do not cancel the deployment

### Issue: Pipelines Don't Trigger Automatically

**Symptoms:**
- Push to master doesn't trigger pipelines
- No new executions

**Solutions:**

1. Check EventBridge rules:
```bash
aws events list-rules --name-prefix e-com67
```

2. Verify repository name:
```bash
aws codecommit get-repository --repository-name e-com67
```

3. Check branch name:
```bash
git branch --show-current
# Should be "master"
```

4. Manual trigger:
```bash
aws codepipeline start-pipeline-execution --name e-com67-backend-pipeline
```

---

## FAQ

### Q: Will my application experience downtime during migration?

**A:** No. The migration only affects the CI/CD pipelines, not the running application. Your DataStack, ComputeStack, and ApiStack remain untouched.

### Q: What happens to my data during migration?

**A:** Nothing. All data in DynamoDB, S3, and other services remains intact. The migration only changes how deployments happen.

### Q: Can I migrate in stages?

**A:** Yes. You can:
1. Deploy backend pipeline first
2. Test it thoroughly
3. Deploy frontend stack and pipelines later

### Q: How long does the migration take?

**A:** Approximately 30-45 minutes:
- Destroy old pipeline: 5 minutes
- Deploy backend pipeline: 10 minutes
- Deploy frontend stack: 15 minutes (CloudFront)
- Deploy frontend pipelines: 5 minutes
- Verification: 5 minutes

### Q: Can I keep both old and new pipelines?

**A:** Not recommended. They would conflict on resource names and cause confusion. Choose one architecture.

### Q: What if I need to rollback?

**A:** Follow the rollback plan above. The old pipeline code is still in git history, so you can redeploy it.

### Q: Do I need to update my frontend applications?

**A:** No. The frontend applications don't need any code changes. Only the deployment process changes.

### Q: Will this affect my costs?

**A:** Yes, slightly. You'll have 3 pipelines instead of 1, increasing costs by ~$4/month. See the implementation summary for details.

---

## Support

If you encounter issues during migration:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review [Pipeline Deployment Guide](./pipeline-deployment-guide.md)
3. Check [Implementation Summary](./PIPELINE_IMPLEMENTATION_SUMMARY.md)
4. Review CloudWatch logs for specific errors
5. Open an issue in the repository

---

## Conclusion

The migration to the new three-pipeline architecture provides:
- ✅ Complete automation for backend and frontend
- ✅ Faster deployment cycles
- ✅ Better separation of concerns
- ✅ Production-ready CI/CD

Take your time with the migration, follow the steps carefully, and don't hesitate to use the rollback plan if needed.

**Good luck with your migration!** 🚀
