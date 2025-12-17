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

import aws_cdk as cdk
from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
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

# Add dependency to ensure proper deployment order
compute_stack.add_dependency(data_stack)

app.synth()