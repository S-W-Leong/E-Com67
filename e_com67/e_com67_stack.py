from aws_cdk import Stack, RemovalPolicy, Duration, CfnOutput
from constructs import Construct
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_opensearchservice as opensearch,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_lambda_event_sources as lambda_event_sources,
    aws_cloudwatch as cloudwatch
)
import os
import json

class ECom67Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # 1. Create DynamoDB Tables
        self.create_dynamodb_tables()
        
        # 2. Create Cognito User Pool
        self.create_cognito()
        
        # 3. Create Lambda Layers
        self.create_lambda_layers()
        
        # 4. Create Lambda Functions
        self.create_lambda_functions()
        
        # 5. Create API Gateway
        self.create_api_gateway()
        
        # 6. Create OpenSearch
        self.create_opensearch()
        
        # 7. Create SQS/SNS
        self.create_messaging()
        
        # 8. Create Step Functions
        self.create_step_functions()
        
        # 9. Create S3 Buckets
        self.create_s3_buckets()
        
        # 10. Create Bedrock Integration
        self.create_bedrock()
        
        # 11. Create Monitoring
        self.create_monitoring()
        
        # 12. Create EventBridge Rules
        self.create_scheduled_jobs()
        
        # 13. Output important values
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
            table_name="e-com67-users"
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
            table_name="e-com67-products"
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
            table_name="e-com67-orders"
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
            table_name="e-com67-cart"
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
            table_name="e-com67-chat-history"
        )

    def create_cognito(self):
        """Create Cognito User Pool for authentication"""
        self.user_pool = cognito.UserPool(
            self, "ECom67UserPool",
            user_pool_name="e-com67-user-pool",
            self_sign_up_enabled=True,
            auto_verified_attributes=[cognito.UserPoolEmail.ADDRESS],
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

    def create_lambda_layers(self):
        """Create Lambda layers for shared code and dependencies"""
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")
        
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
            # Create a minimal layer if it doesn't exist
            self.common_layer = None

    def create_lambda_functions(self):
        """Create Lambda functions for business logic"""
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")
        
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
                },
                timeout=Duration.seconds(30),
                memory_size=512
            )
            self.products_table.grant_read_write_data(self.product_crud_fn)
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
                    "PRODUCTS_TABLE": self.products_table.table_name
                },
                timeout=Duration.seconds(10)
            )
            self.cart_table.grant_read_write_data(self.cart_fn)
            self.products_table.grant_read_data(self.cart_fn)
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
                    "ORDERS_TABLE": self.orders_table.table_name
                },
                timeout=Duration.seconds(30)
            )
            self.orders_table.grant_read_write_data(self.payment_fn)
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
                },
                timeout=Duration.seconds(60)
            )
            self.orders_table.grant_read_write_data(self.order_processor_fn)
            self.cart_table.grant_read_write_data(self.order_processor_fn)
            self.products_table.grant_read_write_data(self.order_processor_fn)
        else:
            self.order_processor_fn = None

    def create_api_gateway(self):
        """Create REST API with Cognito authorization"""
        if not self.user_pool:
            return
        
        # Create Cognito Authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "ECom67Authorizer",
            cognito_user_pools=[self.user_pool]
        )
        
        # Create REST API
        self.api = apigw.RestApi(
            self, "ECom67Api",
            rest_api_name="e-com67-api",
            description="Serverless e-com67 API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )
        
        # Products endpoints
        if self.product_crud_fn:
            products = self.api.root.add_resource("products")
            products.add_method(
                "GET",
                apigw.LambdaIntegration(self.product_crud_fn)
            )
            products.add_method(
                "POST",
                apigw.LambdaIntegration(self.product_crud_fn),
                authorizer=authorizer,
                authorization_type=apigw.AuthorizationType.COGNITO
            )
            
            product = products.add_resource("{productId}")
            product.add_method("GET", apigw.LambdaIntegration(self.product_crud_fn))
            product.add_method(
                "PUT",
                apigw.LambdaIntegration(self.product_crud_fn),
                authorizer=authorizer
            )
            product.add_method(
                "DELETE",
                apigw.LambdaIntegration(self.product_crud_fn),
                authorizer=authorizer
            )
        
        # Cart endpoints
        if self.cart_fn:
            cart = self.api.root.add_resource("cart")
            cart.add_method(
                "GET",
                apigw.LambdaIntegration(self.cart_fn),
                authorizer=authorizer
            )
            cart.add_method(
                "POST",
                apigw.LambdaIntegration(self.cart_fn),
                authorizer=authorizer
            )

    def create_opensearch(self):
        """Create OpenSearch domain for product search"""
        # For development, we'll use a smaller instance
        # Note: In production, use a proper domain with multiple nodes
        self.opensearch_domain = opensearch.Domain(
            self, "ECom67SearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_9,
            capacity=opensearch.Capacity(
                data_node_instance_type="t3.small.opensearch",
                data_nodes=1
            ),
            removal_policy=RemovalPolicy.DESTROY,
            ebs=opensearch.Ebs(
                enabled=True,
                volume_size=10,
                volume_type=ec2_volume_type.EbsDeviceVolumeType.GP3
            ) if 'ec2_volume_type' in dir() else None
        )

    def create_messaging(self):
        """Create SQS queues and SNS topics"""
        # Dead Letter Queue
        dlq = sqs.Queue(
            self, "OrderDLQ",
            queue_name="e-com67-order-dlq",
            retention_period=Duration.days(14)
        )
        
        # Order Processing Queue
        self.order_queue = sqs.Queue(
            self, "OrderQueue",
            queue_name="e-com67-order-queue",
            visibility_timeout=Duration.seconds(90),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            )
        )
        
        # Connect Lambda to SQS if order processor exists
        if self.order_processor_fn:
            self.order_processor_fn.add_event_source(
                lambda_event_sources.SqsEventSource(self.order_queue, batch_size=10)
            )
        
        # SNS Topic for Order Notifications
        self.order_notification_topic = sns.Topic(
            self, "OrderNotificationTopic",
            display_name="Order Notifications",
            topic_name="e-com67-order-notifications"
        )

    def create_step_functions(self):
        """Create Step Functions for checkout workflow"""
        if not self.payment_fn:
            return
        
        # For now, create a simple state machine
        # In a real scenario, this would include validation, payment, and queue tasks
        definition = sfn.Pass(
            self, "CheckoutPass",
            comment="Placeholder for checkout state machine"
        )
        
        self.checkout_state_machine = sfn.StateMachine(
            self, "CheckoutStateMachine",
            state_machine_name="e-com67-checkout",
            definition=definition,
            timeout=Duration.minutes(5)
        )

    def create_s3_buckets(self):
        """Create S3 buckets for assets and data"""
        # Frontend bucket
        self.frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name=f"e-com67-frontend-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # Knowledge base bucket for AI chat
        self.knowledge_base_bucket = s3.Bucket(
            self, "KnowledgeBaseBucket",
            bucket_name=f"e-com67-kb-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

    def create_bedrock(self):
        """Create Bedrock integration for AI chat"""
        # Create IAM role for Bedrock access
        bedrock_role = iam.Role(
            self, "BedrockRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Lambda to invoke Bedrock"
        )
        
        bedrock_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["arn:aws:bedrock:*:*:foundation-model/*"],
                effect=iam.Effect.ALLOW
            )
        )

    def create_monitoring(self):
        """Create CloudWatch alarms and dashboards"""
        if self.payment_fn:
            # Lambda Error Alarm
            self.payment_fn.metric_errors().create_alarm(
                self, "PaymentErrorAlarm",
                threshold=5,
                evaluation_periods=1,
                alarm_description="Payment function errors"
            )
        
        # SQS Queue Depth Alarm
        self.order_queue.metric_approximate_number_of_messages_visible().create_alarm(
            self, "QueueDepthAlarm",
            threshold=100,
            evaluation_periods=1,
            alarm_description="Order queue depth alarm"
        )

    def create_scheduled_jobs(self):
        """Create EventBridge rules for scheduled tasks"""
        # Example: Daily inventory check at 2 AM
        inventory_rule = events.Rule(
            self, "DailyInventoryCheck",
            schedule=events.Schedule.cron(hour="2", minute="0"),
            description="Daily inventory check"
        )

    def create_outputs(self):
        """Create CloudFormation outputs"""
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )
        
        CfnOutput(
            self, "ApiEndpoint",
            value=self.api.url,
            description="API Gateway endpoint"
        )
        
        CfnOutput(
            self, "UsersTableName",
            value=self.users_table.table_name,
            description="Users DynamoDB table name"
        )
        
        CfnOutput(
            self, "ProductsTableName",
            value=self.products_table.table_name,
            description="Products DynamoDB table name"
        )
        
        CfnOutput(
            self, "OrdersTableName",
            value=self.orders_table.table_name,
            description="Orders DynamoDB table name"
        )
        
        CfnOutput(
            self, "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="Frontend S3 bucket name"
        )

    