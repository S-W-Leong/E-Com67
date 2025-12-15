"""
Multi-stack architecture for e-com67 platform.

This package contains separate CDK stacks organized by layer:
- DataStack: DynamoDB tables and Cognito authentication
- ComputeStack: Lambda functions and layers
- ApiStack: API Gateway and endpoints
- InfraStack: Supporting infrastructure (OpenSearch, SQS, SNS, S3, monitoring)
"""

from .data_stack import DataStack
from .compute_stack import ComputeStack
from .api_stack import ApiStack
from .infra_stack import InfraStack

__all__ = [
    "DataStack",
    "ComputeStack",
    "ApiStack",
    "InfraStack",
]
