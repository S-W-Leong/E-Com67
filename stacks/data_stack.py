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
    aws_opensearchserverless as opensearchserverless,
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
import json


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
        """Create OpenSearch Serverless collection for product search and knowledge base"""

        # Create encryption policy - must be a single object (not an array) with Rules and AWSOwnedKey
        encryption_policy = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": ["collection/e-com67-products"]
                }
            ],
            "AWSOwnedKey": True
        }

        self.opensearch_encryption_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OpenSearchEncryptionPolicy",
            name="e-com67-encryption-policy",
            type="encryption",
            policy=json.dumps(encryption_policy)
        )

        # Create network policy for public access
        # Network policy must be an array of policy statements
        # Each statement needs: Rules (with ResourceType and Resource) and AllowFromPublic at the statement level
        # Do NOT include SourceVPCEs or SourceServices when AllowFromPublic is true
        network_policy = [
            {
                "Description": "Public access for e-com67 products collection",
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": ["collection/e-com67-products"]
                    }
                ],
                "AllowFromPublic": True
            },
            {
                "Description": "Public access for e-com67 products dashboard",
                "Rules": [
                    {
                        "ResourceType": "dashboard",
                        "Resource": ["collection/e-com67-products"]
                    }
                ],
                "AllowFromPublic": True
            }
        ]

        self.opensearch_network_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OpenSearchNetworkPolicy",
            name="e-com67-network-policy",
            type="network",
            policy=json.dumps(network_policy)
        )

        # Create the OpenSearch Serverless collection
        self.opensearch_collection = opensearchserverless.CfnCollection(
            self, "ProductSearchCollection",
            name="e-com67-products",
            description="Product search and knowledge base collection for E-Com67 platform",
            type="SEARCH"
        )

        # Collection depends on policies
        self.opensearch_collection.add_dependency(self.opensearch_encryption_policy)
        self.opensearch_collection.add_dependency(self.opensearch_network_policy)

        # Create data access policy for IAM-based access
        # This allows Lambda functions to access the collection
        self.opensearch_data_policy = opensearchserverless.CfnAccessPolicy(
            self, "OpenSearchDataPolicy",
            name="e-com67-data-policy",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "Resource": [f"collection/e-com67-products"],
                                "Permission": [
                                    "aoss:CreateCollectionItems",
                                    "aoss:DeleteCollectionItems",
                                    "aoss:UpdateCollectionItems",
                                    "aoss:DescribeCollectionItems"
                                ],
                                "ResourceType": "collection"
                            },
                            {
                                "Resource": [f"index/e-com67-products/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DeleteIndex",
                                    "aoss:UpdateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:ReadDocument",
                                    "aoss:WriteDocument"
                                ],
                                "ResourceType": "index"
                            }
                        ],
                        "Principal": [
                            f"arn:aws:iam::{Aws.ACCOUNT_ID}:root"
                        ],
                        "Description": "Data access for e-com67 products collection and knowledge base"
                    }
                ]
            )
        )

        self.opensearch_data_policy.add_dependency(self.opensearch_collection)

        # Store collection properties for exports
        self.opensearch_collection_id = self.opensearch_collection.attr_id
        self.opensearch_collection_arn = self.opensearch_collection.attr_arn
        self.opensearch_endpoint = f"https://{self.opensearch_collection.attr_collection_endpoint}"

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
        
        # OpenSearch exports (placeholder values for manual setup)
        CfnOutput(
            self, "OpenSearchCollectionId",
            value=self.opensearch_collection_id,
            export_name="E-Com67-OpenSearchCollectionId"
        )
        
        CfnOutput(
            self, "OpenSearchCollectionArn",
            value=self.opensearch_collection_arn,
            export_name="E-Com67-OpenSearchCollectionArn"
        )
        
        CfnOutput(
            self, "OpenSearchEndpoint",
            value=self.opensearch_endpoint,
            export_name="E-Com67-OpenSearchEndpoint",
            description="OpenSearch collection endpoint for search operations (to be updated manually)"
        )