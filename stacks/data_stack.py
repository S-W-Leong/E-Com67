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
    aws_opensearchservice as opensearch,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy,
    Duration,
    Aws,
    Fn
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
        self._create_notification_tables()
        
        # Create S3 bucket for knowledge base
        self._create_knowledge_base_bucket()
        
        # Create Cognito User Pool
        self._create_user_pool()
        
        # Create OpenSearch domain for product search
        self._create_opensearch_domain()
        
        # Create cross-stack exports
        self._create_exports()

    # Note: S3 bucket notifications are configured in ComputeStack to avoid circular dependencies

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

    def _create_notification_tables(self):
        """Create notification-related tables"""
        # Notification preferences table
        self.notification_preferences_table = dynamodb.Table(
            self, "NotificationPreferencesTable",
            table_name="e-com67-notification-preferences",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )
        
        # Notification analytics table
        self.notification_analytics_table = dynamodb.Table(
            self, "NotificationAnalyticsTable",
            table_name="e-com67-notification-analytics",
            partition_key=dynamodb.Attribute(
                name="notificationId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY  # For development
        )
        
        # Add GSI for analytics queries by user and date
        self.notification_analytics_table.add_global_secondary_index(
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

    def _create_knowledge_base_bucket(self):
        """Create S3 bucket for knowledge base documents"""
        self.knowledge_base_bucket = s3.Bucket(
            self, "KnowledgeBaseBucket",
            bucket_name=f"e-com67-knowledge-base-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
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
                email_body="Welcome to E-Com67! Your verification code is: {####}",
                email_style=cognito.VerificationEmailStyle.CODE
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

        # Create User Pool Domain (required for OAuth flows)
        self.user_pool_domain = cognito.UserPoolDomain(
            self, "UserPoolDomain",
            user_pool=self.user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="e-com67-users"  # Must be globally unique across AWS
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

    def _create_opensearch_domain(self):
        """Create OpenSearch Service domain for product search and knowledge base"""
        
        # Create OpenSearch domain with cost-optimized configuration
        self.opensearch_domain = opensearch.Domain(
            self, "ProductSearchDomain",
            domain_name="e-com67-products",
            version=opensearch.EngineVersion.OPENSEARCH_2_3,
            
            # Cost-optimized capacity configuration
            capacity=opensearch.CapacityConfig(
                data_nodes=1,  # Single node for development
                data_node_instance_type="t3.small.search",  # ~$25/month vs $350+/month for serverless
                # No dedicated master nodes for cost savings in development
            ),
            
            # EBS storage configuration
            ebs=opensearch.EbsOptions(
                volume_size=20,  # 20GB should be sufficient for development
                volume_type=ec2.EbsDeviceVolumeType.GP3,  # GP3 is more cost-effective than GP2
            ),
            
            # Disable zone awareness for single node (cost optimization)
            zone_awareness=opensearch.ZoneAwarenessConfig(
                enabled=False
            ),
            
            # Security configuration
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(
                enabled=True
            ),
            enforce_https=True,
            tls_security_policy=opensearch.TLSSecurityPolicy.TLS_1_2,
            
            # Logging configuration (optional - can be disabled to save costs)
            logging=opensearch.LoggingOptions(
                slow_search_log_enabled=False,  # Disable to save CloudWatch costs
                app_log_enabled=False,          # Disable to save CloudWatch costs
                slow_index_log_enabled=False    # Disable to save CloudWatch costs
            ),
            
            # Access policy - allow access from Lambda functions and specific IP ranges
            access_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountRootPrincipal()],  # Allow access from account root
                    actions=["es:*"],
                    resources=[f"arn:aws:es:{self.region}:{self.account}:domain/e-com67-products/*"]
                )
            ],
            
            # Enable version upgrades without replacement
            enable_version_upgrade=True,
            
            # Development environment - destroy on stack deletion
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Store domain properties for exports
        self.opensearch_domain_arn = self.opensearch_domain.domain_arn
        self.opensearch_endpoint = f"https://{self.opensearch_domain.domain_endpoint}"

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
        
        # Notification table exports
        CfnOutput(
            self, "NotificationPreferencesTableName",
            value=self.notification_preferences_table.table_name,
            export_name="E-Com67-NotificationPreferencesTableName"
        )
        
        CfnOutput(
            self, "NotificationPreferencesTableArn",
            value=self.notification_preferences_table.table_arn,
            export_name="E-Com67-NotificationPreferencesTableArn"
        )
        
        CfnOutput(
            self, "NotificationAnalyticsTableName",
            value=self.notification_analytics_table.table_name,
            export_name="E-Com67-NotificationAnalyticsTableName"
        )
        
        CfnOutput(
            self, "NotificationAnalyticsTableArn",
            value=self.notification_analytics_table.table_arn,
            export_name="E-Com67-NotificationAnalyticsTableArn"
        )
        
        # S3 bucket exports
        CfnOutput(
            self, "KnowledgeBaseBucketName",
            value=self.knowledge_base_bucket.bucket_name,
            export_name="E-Com67-KnowledgeBaseBucketName"
        )
        
        CfnOutput(
            self, "KnowledgeBaseBucketArn",
            value=self.knowledge_base_bucket.bucket_arn,
            export_name="E-Com67-KnowledgeBaseBucketArn"
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
        
        # OpenSearch exports
        CfnOutput(
            self, "OpenSearchDomainArn",
            value=self.opensearch_domain_arn,
            export_name="E-Com67-OpenSearchDomainArn"
        )
        
        CfnOutput(
            self, "OpenSearchEndpoint",
            value=self.opensearch_endpoint,
            export_name="E-Com67-OpenSearchEndpoint",
            description="OpenSearch domain endpoint for search operations"
        )