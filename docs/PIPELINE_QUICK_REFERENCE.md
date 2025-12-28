# E-Com67 Pipeline Quick Reference

Quick reference for common pipeline operations.

## 🚀 Initial Setup

```bash
# 1. Create CodeCommit repository (if needed)
aws codecommit create-repository --repository-name e-com67 --region ap-southeast-1

# 2. Add remote and push
git remote add codecommit https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/e-com67
git push codecommit master

# 3. Run interactive deployment
./deploy_pipelines.sh
```

## 📦 Deployment Commands

### Backend Pipeline

```bash
# Deploy backend pipeline
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack --require-approval never

# Update backend pipeline
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack

# Trigger manually
aws codepipeline start-pipeline-execution --name e-com67-backend-pipeline
```

### Frontend Stack

```bash
# Deploy S3 + CloudFront
cdk deploy E-Com67-FrontendStack --require-approval never

# Get URLs
aws cloudformation describe-stacks --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs" --output table
```

### Frontend Pipelines

```bash
# Deploy both frontend pipelines
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack --require-approval never

# Trigger admin pipeline
aws codepipeline start-pipeline-execution --name e-com67-admin-dashboard-pipeline

# Trigger customer pipeline
aws codepipeline start-pipeline-execution --name e-com67-customer-app-pipeline
```

## 📊 Monitoring

### Pipeline Status

```bash
# Backend pipeline
aws codepipeline get-pipeline-state --name e-com67-backend-pipeline

# Admin pipeline
aws codepipeline get-pipeline-state --name e-com67-admin-dashboard-pipeline

# Customer pipeline
aws codepipeline get-pipeline-state --name e-com67-customer-app-pipeline

# All pipelines (using script)
./deploy_pipelines.sh  # Select option 5
```

### Execution History

```bash
# List recent executions
aws codepipeline list-pipeline-executions --pipeline-name e-com67-backend-pipeline --max-items 5

# Get execution details
aws codepipeline get-pipeline-execution \
  --pipeline-name e-com67-backend-pipeline \
  --pipeline-execution-id <execution-id>
```

### Build Logs

```bash
# List builds for a project
aws codebuild list-builds-for-project --project-name <project-name>

# Get build details
aws codebuild batch-get-builds --ids <build-id>
```

## 🔧 Troubleshooting

### Test Locally

```bash
# Test CDK synth
USE_BACKEND_PIPELINE=true cdk synth

# Test frontend builds
cd frontends/admin-dashboard && npm run build
cd frontends/customer-app && npm run build
```

### Pipeline Controls

```bash
# Stop execution
aws codepipeline stop-pipeline-execution \
  --pipeline-name e-com67-backend-pipeline \
  --pipeline-execution-id <execution-id> \
  --abandon

# Retry failed stage
aws codepipeline retry-stage-execution \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --pipeline-execution-id <execution-id> \
  --retry-mode FAILED_ACTIONS

# Disable stage transition
aws codepipeline disable-stage-transition \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --transition-type Inbound \
  --reason "Maintenance"

# Enable stage transition
aws codepipeline enable-stage-transition \
  --pipeline-name e-com67-backend-pipeline \
  --stage-name Deploy \
  --transition-type Inbound
```

### CloudFront

```bash
# Manual cache invalidation
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*"

# List invalidations
aws cloudfront list-invalidations --distribution-id <distribution-id>
```

## 🗑️ Cleanup

### Destroy Pipelines

```bash
# Destroy backend pipeline
cdk destroy E-Com67-BackendPipelineStack --force

# Destroy frontend pipelines
cdk destroy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack --force

# Destroy frontend stack
cdk destroy E-Com67-FrontendStack --force

# Destroy old pipeline (if exists)
cdk destroy E-Com67-PipelineStack --force
```

### Clean Artifacts

```bash
# List artifact buckets
aws s3 ls | grep codepipeline

# Empty and delete artifact bucket
aws s3 rm s3://<bucket-name> --recursive
aws s3 rb s3://<bucket-name>
```

## 📝 Common Workflows

### Deploy Everything from Scratch

```bash
./deploy_pipelines.sh
# Select option 6 (Deploy All)
```

### Update Backend Infrastructure

```bash
# Make changes to stacks/
git add .
git commit -m "Update backend infrastructure"
git push codecommit master
# Pipeline automatically triggers
```

### Update Frontend Application

```bash
# Make changes to frontends/
git add .
git commit -m "Update frontend"
git push codecommit master
# Pipelines automatically trigger
```

### Update Pipeline Configuration

```bash
# Make changes to stacks/*_pipeline_stack.py
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack
# or
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack
```

## 🔗 Useful Links

- [Full Deployment Guide](docs/pipeline-deployment-guide.md)
- [Implementation Summary](docs/PIPELINE_IMPLEMENTATION_SUMMARY.md)
- [Main README](README.md)
- [AWS CodePipeline Console](https://console.aws.amazon.com/codesuite/codepipeline/pipelines)
- [CloudFormation Console](https://console.aws.amazon.com/cloudformation)

## 💡 Tips

1. **Always test locally before pushing:**
   ```bash
   cdk synth && npm run build
   ```

2. **Monitor pipeline execution:**
   ```bash
   watch -n 5 'aws codepipeline get-pipeline-state --name e-com67-backend-pipeline'
   ```

3. **Check CloudWatch logs for errors:**
   ```bash
   aws logs tail /aws/codebuild/<project-name> --follow
   ```

4. **Use the interactive script for complex operations:**
   ```bash
   ./deploy_pipelines.sh
   ```

5. **Keep CodeCommit in sync:**
   ```bash
   git push codecommit master
   ```
