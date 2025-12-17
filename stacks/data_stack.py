"""
E-Com67 Platform Data Stack

This stack contains all data-related resources:
- DynamoDB tables with proper indexing and streams
- Cognito User Pool for authentication
- Cross-stack exports for resource sharing
"""

from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    CfnOutput,
    RemovalPolicy,
    Duration
)
from constructs import Construct


class DataStack(Stack):
    """Data layer stack containing DynamoDB tables and Cognito User Pool"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB tables
        self._create_products_table()
        self._create_cart_table()
        self._create_orders_table()
        self._create_chat_history_table()
        
        # Create Cognito User Pool
        self._create_user_pool()
        
        # Create cross-stack exports
        self._create_exports()

    def _create_products_table(self):
        """Create products table with category GSI and DynamoDB Streams"""
        self.products_table = dynamodb.Table(
            self, "ProductsTable",
            table_name="e-com67-products",
            partition_key=dynamodb.Attribute(
                name="productId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            point_in_time_recovery=True,
            contributor_insights_enabled=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )
        
        # Add Global Secondary Index for category-based queries
        self.products_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

    def _create_cart_table(self):
        """Create cart table with composite key (userId, productId)"""
        self.cart_table = dynamodb.Table(
            self, "CartTable",
            table_name="e-com67-cart",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="productId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )

    def _create_orders_table(self):
        """Create orders table with userId-timestamp GSI for efficient queries"""
        self.orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="e-com67-orders",
            partition_key=dynamodb.Attribute(
                name="orderId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            contributor_insights_enabled=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )
        
        # Add Global Secondary Index for user-based order queries
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

    def _create_chat_history_table(self):
        """Create chat-history table for AI conversation storage"""
        self.chat_history_table = dynamodb.Table(
            self, "ChatHistoryTable",
            table_name="e-com67-chat-history",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )

    def _create_user_pool(self):
        """Create Cognito User Pool with proper security configuration"""
        # Create User Pool
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name="e-com67-users",
            # Email verification and password policies
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            # Account recovery
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # JWT token expiration settings
            user_verification=cognito.UserVerificationConfig(
                email_subject="E-Com67 - Verify your email",
                email_body="Welcome to E-Com67! Please verify your email by clicking: {##Verify Email##}",
                email_style=cognito.VerificationEmailStyle.LINK
            ),
            # Standard attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                given_name=cognito.StandardAttribute(required=False, mutable=True),
                family_name=cognito.StandardAttribute(required=False, mutable=True)
            ),
            removal_policy=RemovalPolicy.DESTROY  # For development
        )
        
        # Create User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self, "UserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="e-com67-client",
            # Auth flows
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            # JWT token settings
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            # Prevent user existence errors
            prevent_user_existence_errors=True,
            # OAuth settings for future use
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE]
            )
        )
        
        # Create admin user group
        self.admin_group = cognito.CfnUserPoolGroup(
            self, "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="Administrative users with elevated privileges",
            precedence=1
        )

    def _create_exports(self):
        """Create CloudFormation exports for cross-stack resource sharing"""
        # DynamoDB table exports
        CfnOutput(
            self, "ProductsTableName",
            value=self.products_table.table_name,
            export_name="E-Com67-ProductsTableName"
        )
        
        CfnOutput(
            self, "ProductsTableArn",
            value=self.products_table.table_arn,
            export_name="E-Com67-ProductsTableArn"
        )
        
        CfnOutput(
            self, "ProductsTableStreamArn",
            value=self.products_table.table_stream_arn,
            export_name="E-Com67-ProductsTableStreamArn"
        )
        
        CfnOutput(
            self, "CartTableName",
            value=self.cart_table.table_name,
            export_name="E-Com67-CartTableName"
        )
        
        CfnOutput(
            self, "CartTableArn",
            value=self.cart_table.table_arn,
            export_name="E-Com67-CartTableArn"
        )
        
        CfnOutput(
            self, "OrdersTableName",
            value=self.orders_table.table_name,
            export_name="E-Com67-OrdersTableName"
        )
        
        CfnOutput(
            self, "OrdersTableArn",
            value=self.orders_table.table_arn,
            export_name="E-Com67-OrdersTableArn"
        )
        
        CfnOutput(
            self, "ChatHistoryTableName",
            value=self.chat_history_table.table_name,
            export_name="E-Com67-ChatHistoryTableName"
        )
        
        CfnOutput(
            self, "ChatHistoryTableArn",
            value=self.chat_history_table.table_arn,
            export_name="E-Com67-ChatHistoryTableArn"
        )
        
        # Cognito exports
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name="E-Com67-UserPoolId"
        )
        
        CfnOutput(
            self, "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            export_name="E-Com67-UserPoolArn"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name="E-Com67-UserPoolClientId"
        )