"""
E-Com67 Platform Compute Stack

This stack contains all compute-related resources:
- Lambda layers for shared dependencies
- Lambda functions for business logic
- IAM roles and policies
"""

from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
    Fn
)
from constructs import Construct
import os


class ComputeStack(Stack):
    """Compute layer stack containing Lambda functions and layers"""

    def __init__(self, scope: Construct, construct_id: str, data_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.data_stack = data_stack
        
        # Create Lambda layers
        self._create_lambda_layers()
        
        # Create basic Lambda functions
        self._create_basic_functions()
        
        # Create cross-stack exports
        self._create_exports()

    def _create_lambda_layers(self):
        """Create Lambda layers for shared dependencies"""
        
        # AWS Lambda Powertools layer
        self.powertools_layer = _lambda.LayerVersion(
            self, "PowertoolsLayer",
            layer_version_name="e-com67-powertools",
            code=_lambda.Code.from_asset("layers/powertools"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9, _lambda.Runtime.PYTHON_3_10],
            description="AWS Lambda Powertools for structured logging and tracing",
            removal_policy=self.removal_policy
        )
        
        # Common utilities layer
        self.utils_layer = _lambda.LayerVersion(
            self, "UtilsLayer",
            layer_version_name="e-com67-utils",
            code=_lambda.Code.from_asset("layers/utils"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9, _lambda.Runtime.PYTHON_3_10],
            description="Common utilities and shared business logic",
            removal_policy=self.removal_policy
        )
        
        # Stripe SDK layer
        self.stripe_layer = _lambda.LayerVersion(
            self, "StripeLayer",
            layer_version_name="e-com67-stripe",
            code=_lambda.Code.from_asset("layers/stripe"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9, _lambda.Runtime.PYTHON_3_10],
            description="Stripe SDK for payment processing integration",
            removal_policy=self.removal_policy
        )

    def _create_basic_functions(self):
        """Create basic Lambda functions with proper IAM roles"""
        
        # Common Lambda execution role
        self.lambda_execution_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name="e-com67-lambda-execution-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add DynamoDB permissions
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem"
                ],
                resources=[
                    Fn.import_value("E-Com67-ProductsTableArn"),
                    Fn.import_value("E-Com67-CartTableArn"),
                    Fn.import_value("E-Com67-OrdersTableArn"),
                    Fn.import_value("E-Com67-ChatHistoryTableArn"),
                    f"{Fn.import_value('E-Com67-ProductsTableArn')}/index/*",
                    f"{Fn.import_value('E-Com67-OrdersTableArn')}/index/*"
                ]
            )
        )
        
        # Product CRUD function
        self.product_crud_function = _lambda.Function(
            self, "ProductCrudFunction",
            function_name="e-com67-product-crud",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="product_crud.handler",
            code=_lambda.Code.from_asset("lambda/product_crud"),
            layers=[self.powertools_layer, self.utils_layer],
            role=self.lambda_execution_role,
            environment={
                "PRODUCTS_TABLE_NAME": Fn.import_value("E-Com67-ProductsTableName"),
                "POWERTOOLS_SERVICE_NAME": "product-crud",
                "POWERTOOLS_METRICS_NAMESPACE": "E-Com67",
                "LOG_LEVEL": "INFO"
            },
            tracing=_lambda.Tracing.ACTIVE
        )
        
        # Cart function
        self.cart_function = _lambda.Function(
            self, "CartFunction",
            function_name="e-com67-cart",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="cart.handler",
            code=_lambda.Code.from_asset("lambda/cart"),
            layers=[self.powertools_layer, self.utils_layer],
            role=self.lambda_execution_role,
            environment={
                "CART_TABLE_NAME": Fn.import_value("E-Com67-CartTableName"),
                "PRODUCTS_TABLE_NAME": Fn.import_value("E-Com67-ProductsTableName"),
                "POWERTOOLS_SERVICE_NAME": "cart",
                "POWERTOOLS_METRICS_NAMESPACE": "E-Com67",
                "LOG_LEVEL": "INFO"
            },
            tracing=_lambda.Tracing.ACTIVE
        )

    def _create_exports(self):
        """Create CloudFormation exports for cross-stack resource sharing"""
        
        # Lambda layer exports
        CfnOutput(
            self, "PowertoolsLayerArn",
            value=self.powertools_layer.layer_version_arn,
            export_name="E-Com67-PowertoolsLayerArn"
        )
        
        CfnOutput(
            self, "UtilsLayerArn",
            value=self.utils_layer.layer_version_arn,
            export_name="E-Com67-UtilsLayerArn"
        )
        
        CfnOutput(
            self, "StripeLayerArn",
            value=self.stripe_layer.layer_version_arn,
            export_name="E-Com67-StripeLayerArn"
        )
        
        # Lambda function exports
        CfnOutput(
            self, "ProductCrudFunctionArn",
            value=self.product_crud_function.function_arn,
            export_name="E-Com67-ProductCrudFunctionArn"
        )
        
        CfnOutput(
            self, "CartFunctionArn",
            value=self.cart_function.function_arn,
            export_name="E-Com67-CartFunctionArn"
        )
        
        # IAM role exports
        CfnOutput(
            self, "LambdaExecutionRoleArn",
            value=self.lambda_execution_role.role_arn,
            export_name="E-Com67-LambdaExecutionRoleArn"
        )

    @property
    def removal_policy(self):
        """Get removal policy for development environment"""
        from aws_cdk import RemovalPolicy
        return RemovalPolicy.DESTROY  # For development