from aws_cdk import Stack, RemovalPolicy, CfnOutput
from constructs import Construct
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
)


class DataStack(Stack):
    """
    Data Layer Stack - Foundation layer for persistent data and authentication.

    Contains:
    - DynamoDB Tables (users, products, orders, cart, chat-history)
    - Cognito User Pool & Client

    Lifecycle: Rarely changes, data persistence focus
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB Tables
        self.create_dynamodb_tables()

        # Create Cognito User Pool
        self.create_cognito()

        # Create CloudFormation Outputs for cross-stack references
        self.create_outputs()

    def create_dynamodb_tables(self):
        """Create all DynamoDB tables for the e-commerce platform"""

        # Users Table
        self.users_table = dynamodb.Table(
            self, "UsersTable",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev only
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            table_name="e-com67-users",
            point_in_time_recovery=True,
            contributor_insights_enabled=True  # Enable X-Ray tracing
        )

        # Products Table with GSI
        self.products_table = dynamodb.Table(
            self, "ProductsTable",
            partition_key=dynamodb.Attribute(
                name="productId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            table_name="e-com67-products",
            point_in_time_recovery=True,
            contributor_insights_enabled=True  # Enable X-Ray tracing
        )

        # Add GSI for category-based queries
        self.products_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Orders Table with Composite Key + GSI
        self.orders_table = dynamodb.Table(
            self, "OrdersTable",
            partition_key=dynamodb.Attribute(
                name="orderId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            table_name="e-com67-orders",
            point_in_time_recovery=True,
            contributor_insights_enabled=True  # Enable X-Ray tracing
        )

        # GSI for querying user's orders sorted by timestamp
        self.orders_table.add_global_secondary_index(
            index_name="userId-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Cart Table
        self.cart_table = dynamodb.Table(
            self, "CartTable",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="productId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            table_name="e-com67-cart",
            point_in_time_recovery=True,
            contributor_insights_enabled=True  # Enable X-Ray tracing
        )

        # ChatHistory Table
        self.chat_table = dynamodb.Table(
            self, "ChatHistoryTable",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            table_name="e-com67-chat-history",
            point_in_time_recovery=True,
            contributor_insights_enabled=True  # Enable X-Ray tracing
        )

    def create_cognito(self):
        """Create Cognito User Pool for authentication"""
        self.user_pool = cognito.UserPool(
            self, "ECom67UserPool",
            user_pool_name="e-com67-user-pool",
            self_sign_up_enabled=True,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "ECom67Client",
            user_pool_client_name="e-com67-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            generate_secret=False
        )

    def create_outputs(self):
        """Create CloudFormation outputs for cross-stack references"""

        # DynamoDB Table Exports - Names
        CfnOutput(
            self, "UsersTableName",
            value=self.users_table.table_name,
            description="Users DynamoDB table name",
            export_name="ECom67-UsersTable"
        )

        CfnOutput(
            self, "ProductsTableName",
            value=self.products_table.table_name,
            description="Products DynamoDB table name",
            export_name="ECom67-ProductsTable"
        )

        CfnOutput(
            self, "OrdersTableName",
            value=self.orders_table.table_name,
            description="Orders DynamoDB table name",
            export_name="ECom67-OrdersTable"
        )

        CfnOutput(
            self, "CartTableName",
            value=self.cart_table.table_name,
            description="Cart DynamoDB table name",
            export_name="ECom67-CartTable"
        )

        CfnOutput(
            self, "ChatTableName",
            value=self.chat_table.table_name,
            description="Chat History DynamoDB table name",
            export_name="ECom67-ChatTable"
        )

        # DynamoDB Table Exports - ARNs (for IAM permissions)
        CfnOutput(
            self, "UsersTableArn",
            value=self.users_table.table_arn,
            description="Users table ARN",
            export_name="ECom67-UsersTableArn"
        )

        CfnOutput(
            self, "ProductsTableArn",
            value=self.products_table.table_arn,
            description="Products table ARN",
            export_name="ECom67-ProductsTableArn"
        )

        CfnOutput(
            self, "OrdersTableArn",
            value=self.orders_table.table_arn,
            description="Orders table ARN",
            export_name="ECom67-OrdersTableArn"
        )

        CfnOutput(
            self, "CartTableArn",
            value=self.cart_table.table_arn,
            description="Cart table ARN",
            export_name="ECom67-CartTableArn"
        )

        CfnOutput(
            self, "ChatTableArn",
            value=self.chat_table.table_arn,
            description="Chat History table ARN",
            export_name="ECom67-ChatTableArn"
        )

        # DynamoDB Stream ARNs (for future event-driven patterns)
        CfnOutput(
            self, "ProductsTableStreamArn",
            value=self.products_table.table_stream_arn,
            description="Products table stream ARN",
            export_name="ECom67-ProductsTableStreamArn"
        )

        # Cognito Exports
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="ECom67-UserPoolId"
        )

        CfnOutput(
            self, "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN",
            export_name="ECom67-UserPoolArn"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="ECom67-UserPoolClientId"
        )
