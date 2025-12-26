#!/usr/bin/env python3
"""
E-Com67 Platform CDK Application Entry Point

This is the main entry point for the E-Com67 serverless e-commerce platform.
The application is organized into multiple stacks for better separation of concerns:
- DataStack: DynamoDB tables, Cognito User Pool
- ComputeStack: Lambda functions and layers
- ApiStack: API Gateway configuration
- PipelineStack: CI/CD pipeline (optional)

Deployment modes:
1. Direct deployment: Deploy stacks directly using `cdk deploy --all`
2. Pipeline deployment: Deploy via CI/CD using `cdk deploy E-Com67-PipelineStack`

Set USE_PIPELINE=true environment variable to deploy the pipeline stack.
"""

import os
import aws_cdk as cdk
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-1"),
)

# Check if we should deploy the pipeline stack
# Use: USE_PIPELINE=true cdk deploy E-Com67-PipelineStack
use_pipeline = os.environ.get("USE_PIPELINE", "false").lower() == "true"

if use_pipeline:
    # Pipeline mode: Deploy the CI/CD pipeline
    # The pipeline will handle deploying Data, Compute, and Api stacks
    pipeline_stack = PipelineStack(
        app,
        "E-Com67-PipelineStack",
        repository_name="e-com67",  # CodeCommit repository name
        branch="master",
        env=env,
        description="E-Com67 Platform - CI/CD Pipeline with CodePipeline"
    )
    # Note: Individual stacks are created within the pipeline's Deploy stage
else:
    # Direct deployment mode: Deploy stacks individually
    # This is the original behavior for development and testing

    # Data layer - DynamoDB tables and Cognito
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

    # Add dependencies to ensure proper deployment order
    compute_stack.add_dependency(data_stack)
    api_stack.add_dependency(data_stack)
    api_stack.add_dependency(compute_stack)

app.synth()