#!/usr/bin/env python3
"""
E-Com67 Platform CDK Application Entry Point

This is the main entry point for the E-Com67 serverless e-commerce platform.
The application is organized into multiple stacks for better separation of concerns:
- DataStack: DynamoDB tables, Cognito User Pool, OpenSearch, S3
- ComputeStack: Lambda functions and layers
- ApiStack: API Gateway configuration
- FrontendStack: S3 buckets and CloudFront distributions for React apps
- BackendPipelineStack: CI/CD pipeline for backend infrastructure (optional)
- AdminPipelineStack: CI/CD pipeline for admin dashboard (optional)
- CustomerPipelineStack: CI/CD pipeline for customer app (optional)

Deployment modes:
1. Direct deployment: Deploy stacks directly using `cdk deploy --all`
2. Backend pipeline: Deploy via CI/CD using `USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack`
3. Frontend pipelines: Deploy after FrontendStack is deployed

Environment variables:
- USE_BACKEND_PIPELINE=true: Deploy backend CI/CD pipeline
- USE_FRONTEND_PIPELINES=true: Deploy frontend CI/CD pipelines
"""

import os
import aws_cdk as cdk
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack
from stacks.backend_pipeline_stack import BackendPipelineStack
from stacks.admin_pipeline_stack import AdminPipelineStack
from stacks.customer_pipeline_stack import CustomerPipelineStack

# Import AdminInsightsStack only if available (requires aws_bedrock)
try:
    from stacks.admin_insights_stack import AdminInsightsStack
    ADMIN_INSIGHTS_AVAILABLE = True
except ImportError:
    ADMIN_INSIGHTS_AVAILABLE = False

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-1"),
)

# Check deployment mode
use_backend_pipeline = os.environ.get("USE_BACKEND_PIPELINE", "false").lower() == "true"
use_frontend_pipelines = os.environ.get("USE_FRONTEND_PIPELINES", "false").lower() == "true"

if use_backend_pipeline:
    # Backend Pipeline mode: Deploy the backend CI/CD pipeline
    # The pipeline will handle deploying Data, Compute, and Api stacks
    backend_pipeline_stack = BackendPipelineStack(
        app,
        "E-Com67-BackendPipelineStack",
        repository_name="e-com67",  # CodeCommit repository name
        branch="master",
        env=env,
        description="E-Com67 Platform - Backend CI/CD Pipeline with CodePipeline"
    )
    # Note: Individual backend stacks are created within the pipeline's Deploy stage

elif use_frontend_pipelines:
    # Frontend Pipelines mode: Deploy frontend CI/CD pipelines
    # Requires FrontendStack to be deployed first
    
    # Import the existing frontend stack resources
    frontend_stack = FrontendStack(
        app,
        "E-Com67-FrontendStack",
        env=env,
        description="E-Com67 Platform - Frontend hosting with S3 and CloudFront"
    )
    
    # Admin Dashboard Pipeline
    admin_pipeline_stack = AdminPipelineStack(
        app,
        "E-Com67-AdminPipelineStack",
        repository_name="e-com67",
        branch="master",
        admin_bucket=frontend_stack.admin_bucket,
        admin_distribution=frontend_stack.admin_distribution,
        env=env,
        description="E-Com67 Platform - Admin Dashboard CI/CD Pipeline"
    )
    admin_pipeline_stack.add_dependency(frontend_stack)
    
    # Customer App Pipeline
    customer_pipeline_stack = CustomerPipelineStack(
        app,
        "E-Com67-CustomerPipelineStack",
        repository_name="e-com67",
        branch="master",
        customer_bucket=frontend_stack.customer_bucket,
        customer_distribution=frontend_stack.customer_distribution,
        env=env,
        description="E-Com67 Platform - Customer App CI/CD Pipeline"
    )
    customer_pipeline_stack.add_dependency(frontend_stack)

else:
    # Direct deployment mode: Deploy stacks individually
    # This is the default behavior for development and testing

    # Data layer - DynamoDB tables, Cognito, OpenSearch, S3
    data_stack = DataStack(
        app,
        "E-Com67-DataStack",
        env=env,
        description="E-Com67 Platform - Data layer with DynamoDB tables and Cognito User Pool"
    )

    # Compute layer - Lambda functions and layers
    compute_stack = ComputeStack(
        app,
        "E-Com67-ComputeStack",
        data_stack=data_stack,
        env=env,
        description="E-Com67 Platform - Compute layer with Lambda functions and layers"
    )

    # API layer - API Gateway with REST endpoints
    api_stack = ApiStack(
        app,
        "E-Com67-ApiStack",
        data_stack=data_stack,
        compute_stack=compute_stack,
        env=env,
        description="E-Com67 Platform - API Gateway with REST endpoints and Cognito authorization"
    )

    # Frontend layer - S3 and CloudFront for React applications
    frontend_stack = FrontendStack(
        app,
        "E-Com67-FrontendStack",
        env=env,
        description="E-Com67 Platform - Frontend hosting with S3 and CloudFront"
    )

    # Admin Insights layer - AI agent for admin analytics (optional)
    if ADMIN_INSIGHTS_AVAILABLE:
        admin_insights_stack = AdminInsightsStack(
            app,
            "E-Com67-AdminInsightsStack",
            data_stack=data_stack,
            env=env,
            description="E-Com67 Platform - Admin Insights Agent with Bedrock AgentCore"
        )
        admin_insights_stack.add_dependency(data_stack)

    # Add dependencies to ensure proper deployment order
    compute_stack.add_dependency(data_stack)
    api_stack.add_dependency(data_stack)
    api_stack.add_dependency(compute_stack)
    # Frontend stack is independent and can be deployed in parallel

app.synth()