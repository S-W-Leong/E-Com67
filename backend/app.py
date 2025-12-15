#!/usr/bin/env python3
import aws_cdk as cdk
from e_com67.stacks import DataStack, ComputeStack, ApiStack, InfraStack

app = cdk.App()

# Define environment
env = cdk.Environment(
    account='724542698940',
    region='ap-southeast-1'
)

# Create stacks in dependency order
# DataStack is the foundation - contains DynamoDB tables and Cognito
data_stack = DataStack(app, "ECom67-DataStack", env=env)

# ComputeStack contains Lambda functions - depends on DataStack
compute_stack = ComputeStack(app, "ECom67-ComputeStack", env=env)
compute_stack.add_dependency(data_stack)

# ApiStack contains API Gateway - depends on ComputeStack and DataStack
api_stack = ApiStack(app, "ECom67-ApiStack", env=env)
api_stack.add_dependency(compute_stack)
api_stack.add_dependency(data_stack)

# InfraStack contains supporting services - depends on ComputeStack
infra_stack = InfraStack(app, "ECom67-InfraStack", env=env)
infra_stack.add_dependency(compute_stack)

app.synth()