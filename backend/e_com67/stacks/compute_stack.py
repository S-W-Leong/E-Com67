from aws_cdk import Stack, Duration, CfnOutput, Fn
from constructs import Construct
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
)
import os


class ComputeStack(Stack):
    """
    Compute Layer Stack - Application logic layer.

    Contains:
    - Lambda Layers (Powertools, Common Utils)
    - Lambda Functions (products, cart, payment, order_processor)

    Imports from DataStack:
    - DynamoDB table names and ARNs

    Lifecycle: Frequent updates, code deployments
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import table references from DataStack
        self.import_data_stack_resources()

        # Create Lambda Layers
        self.create_lambda_layers()

        # Create Lambda Functions
        self.create_lambda_functions()

        # Grant IAM permissions to Lambda functions
        self.grant_permissions()

        # Create CloudFormation Outputs
        self.create_outputs()

    def import_data_stack_resources(self):
        """Import resources exported from DataStack"""

        # Import DynamoDB tables using from_table_arn for grant_* methods
        # We use table ARN which contains the table name
        self.products_table = dynamodb.Table.from_table_arn(
            self, "ImportedProductsTable",
            table_arn=Fn.import_value("ECom67-ProductsTableArn")
        )

        self.orders_table = dynamodb.Table.from_table_arn(
            self, "ImportedOrdersTable",
            table_arn=Fn.import_value("ECom67-OrdersTableArn")
        )

        self.cart_table = dynamodb.Table.from_table_arn(
            self, "ImportedCartTable",
            table_arn=Fn.import_value("ECom67-CartTableArn")
        )

        self.chat_table = dynamodb.Table.from_table_arn(
            self, "ImportedChatTable",
            table_arn=Fn.import_value("ECom67-ChatTableArn")
        )

    def create_lambda_layers(self):
        """Create Lambda layers for shared code and dependencies"""
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "..", "lambda")

        # AWS Lambda Powertools Layer
        powertools_layer_path = os.path.join(lambda_dir, "layers", "powertools")
        if os.path.exists(os.path.join(powertools_layer_path, "python")):
            # Custom layer built locally - more control over versions
            self.powertools_layer = lambda_.LayerVersion(
                self, "PowertoolsLayer",
                code=lambda_.Code.from_asset(powertools_layer_path),
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
                description="AWS Lambda Powertools for Python"
            )
        else:
            # Use AWS-managed layer (easier but version may vary by region)
            self.powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
                self, "PowertoolsLayer",
                layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:59"
            )

        # Common utilities layer - create if it doesn't exist
        common_layer_path = os.path.join(lambda_dir, "layers", "common_utils")
        if os.path.exists(common_layer_path):
            self.common_layer = lambda_.LayerVersion(
                self, "CommonUtilsLayer",
                code=lambda_.Code.from_asset(common_layer_path),
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
                description="Common utilities, logging, error handling"
            )
        else:
            self.common_layer = None

    def create_lambda_functions(self):
        """Create Lambda functions for business logic"""
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "..", "lambda")

        # Product CRUD Function
        product_fn_path = os.path.join(lambda_dir, "products")
        if os.path.exists(product_fn_path):
            self.product_crud_fn = lambda_.Function(
                self, "ProductCrudFunction",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_asset(product_fn_path),
                environment={
                    "PRODUCTS_TABLE": self.products_table.table_name,
                    "POWERTOOLS_SERVICE_NAME": "products",
                    "POWERTOOLS_METRICS_NAMESPACE": "ECom67",
                    "LOG_LEVEL": "INFO"
                },
                timeout=Duration.seconds(30),
                memory_size=512,
                tracing=lambda_.Tracing.ACTIVE,  # Enable X-Ray Active tracing
                layers=[self.powertools_layer]
            )
        else:
            self.product_crud_fn = None

        # Cart Function
        cart_fn_path = os.path.join(lambda_dir, "cart")
        if os.path.exists(cart_fn_path):
            self.cart_fn = lambda_.Function(
                self, "CartFunction",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_asset(cart_fn_path),
                environment={
                    "CART_TABLE": self.cart_table.table_name,
                    "PRODUCTS_TABLE": self.products_table.table_name,
                    "POWERTOOLS_SERVICE_NAME": "cart",
                    "POWERTOOLS_METRICS_NAMESPACE": "ECom67",
                    "LOG_LEVEL": "INFO"
                },
                timeout=Duration.seconds(10),
                tracing=lambda_.Tracing.ACTIVE,  # Enable X-Ray Active tracing
                layers=[self.powertools_layer]
            )
        else:
            self.cart_fn = None

        # Payment Function
        payment_fn_path = os.path.join(lambda_dir, "payment")
        if os.path.exists(payment_fn_path):
            self.payment_fn = lambda_.Function(
                self, "PaymentFunction",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_asset(payment_fn_path),
                environment={
                    "ORDERS_TABLE": self.orders_table.table_name,
                    "POWERTOOLS_SERVICE_NAME": "payment",
                    "POWERTOOLS_METRICS_NAMESPACE": "ECom67",
                    "LOG_LEVEL": "INFO"
                },
                timeout=Duration.seconds(30),
                tracing=lambda_.Tracing.ACTIVE,  # Enable X-Ray Active tracing
                layers=[self.powertools_layer]
            )
        else:
            self.payment_fn = None

        # Order Processor Function
        order_processor_path = os.path.join(lambda_dir, "order_processor")
        if os.path.exists(order_processor_path):
            self.order_processor_fn = lambda_.Function(
                self, "OrderProcessorFunction",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_asset(order_processor_path),
                environment={
                    "ORDERS_TABLE": self.orders_table.table_name,
                    "CART_TABLE": self.cart_table.table_name,
                    "PRODUCTS_TABLE": self.products_table.table_name,
                    "POWERTOOLS_SERVICE_NAME": "order-processor",
                    "POWERTOOLS_METRICS_NAMESPACE": "ECom67",
                    "LOG_LEVEL": "INFO"
                },
                timeout=Duration.seconds(60),
                tracing=lambda_.Tracing.ACTIVE,  # Enable X-Ray Active tracing
                layers=[self.powertools_layer]
            )
        else:
            self.order_processor_fn = None

        # Orders Function (GET orders for user)
        orders_fn_path = os.path.join(lambda_dir, "orders")
        if os.path.exists(orders_fn_path):
            self.orders_fn = lambda_.Function(
                self, "OrdersFunction",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_asset(orders_fn_path),
                environment={
                    "ORDERS_TABLE": self.orders_table.table_name,
                    "POWERTOOLS_SERVICE_NAME": "orders",
                    "POWERTOOLS_METRICS_NAMESPACE": "ECom67",
                    "LOG_LEVEL": "INFO"
                },
                timeout=Duration.seconds(30),
                tracing=lambda_.Tracing.ACTIVE,
                layers=[self.powertools_layer]
            )
        else:
            self.orders_fn = None

    def grant_permissions(self):
        """Grant IAM permissions to Lambda functions for DynamoDB access"""

        # Product CRUD Function permissions
        if self.product_crud_fn:
            self.products_table.grant_read_write_data(self.product_crud_fn)

        # Cart Function permissions
        if self.cart_fn:
            self.cart_table.grant_read_write_data(self.cart_fn)
            self.products_table.grant_read_data(self.cart_fn)

        # Payment Function permissions
        if self.payment_fn:
            self.orders_table.grant_read_write_data(self.payment_fn)

        # Order Processor Function permissions
        if self.order_processor_fn:
            self.orders_table.grant_read_write_data(self.order_processor_fn)
            self.cart_table.grant_read_write_data(self.order_processor_fn)
            self.products_table.grant_read_write_data(self.order_processor_fn)

        # Orders Function permissions
        if self.orders_fn:
            self.orders_table.grant_read_data(self.orders_fn)

    def create_outputs(self):
        """Create CloudFormation outputs for cross-stack references"""

        # Export Lambda Function ARNs
        if self.product_crud_fn:
            CfnOutput(
                self, "ProductFunctionArn",
                value=self.product_crud_fn.function_arn,
                description="Product CRUD Lambda function ARN",
                export_name="ECom67-ProductFunction"
            )

            CfnOutput(
                self, "ProductFunctionName",
                value=self.product_crud_fn.function_name,
                description="Product CRUD Lambda function name",
                export_name="ECom67-ProductFunctionName"
            )

        if self.cart_fn:
            CfnOutput(
                self, "CartFunctionArn",
                value=self.cart_fn.function_arn,
                description="Cart Lambda function ARN",
                export_name="ECom67-CartFunction"
            )

            CfnOutput(
                self, "CartFunctionName",
                value=self.cart_fn.function_name,
                description="Cart Lambda function name",
                export_name="ECom67-CartFunctionName"
            )

        if self.payment_fn:
            CfnOutput(
                self, "PaymentFunctionArn",
                value=self.payment_fn.function_arn,
                description="Payment Lambda function ARN",
                export_name="ECom67-PaymentFunction"
            )

            CfnOutput(
                self, "PaymentFunctionName",
                value=self.payment_fn.function_name,
                description="Payment Lambda function name",
                export_name="ECom67-PaymentFunctionName"
            )

        if self.order_processor_fn:
            CfnOutput(
                self, "OrderProcessorArn",
                value=self.order_processor_fn.function_arn,
                description="Order Processor Lambda function ARN",
                export_name="ECom67-OrderProcessor"
            )

            CfnOutput(
                self, "OrderProcessorName",
                value=self.order_processor_fn.function_name,
                description="Order Processor Lambda function name",
                export_name="ECom67-OrderProcessorName"
            )

        if self.orders_fn:
            CfnOutput(
                self, "OrdersFunctionArn",
                value=self.orders_fn.function_arn,
                description="Orders Lambda function ARN",
                export_name="ECom67-OrdersFunction"
            )

            CfnOutput(
                self, "OrdersFunctionName",
                value=self.orders_fn.function_name,
                description="Orders Lambda function name",
                export_name="ECom67-OrdersFunctionName"
            )
            
            CfnOutput(
                self, "OrderProcessorRoleArn",
                value=self.order_processor_fn.role.role_arn,
                description="Order Processor Lambda function role ARN",
                export_name="ECom67-OrderProcessorRoleArn"
            )
