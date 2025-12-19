#!/usr/bin/env python3
"""
E-Com67 Platform CDK Application Entry Point

This is the main entry point for the E-Com67 serverless e-commerce platform.
The application is organized into multiple stacks for better separation of concerns:
- DataStack: DynamoDB tables, Cognito User Pool
- ComputeStack: Lambda functions and layers
- ApiStack: API Gateway configuration
- InfrastructureStack: Supporting services
"""

import os
import aws_cdk as cdk
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

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