from aws_cdk import Stack, RemovalPolicy, Duration, CfnOutput, Fn
from constructs import Construct
from aws_cdk import (
    aws_opensearchservice as opensearch,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_s3 as s3,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_ec2 as ec2,
)


class InfraStack(Stack):
    """
    Infrastructure Layer Stack - Supporting services and infrastructure.

    Contains:
    - OpenSearch Domain
    - SQS Queues (order queue, DLQ)
    - SNS Topics (order notifications)
    - Step Functions (checkout workflow)
    - S3 Buckets (frontend, knowledge base)
    - Bedrock IAM Role
    - CloudWatch Alarms
    - EventBridge Rules

    Imports from:
    - ComputeStack: Lambda function ARNs for integrations

    Lifecycle: Infrastructure changes, monitoring updates
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import resources from other stacks
        self.import_resources()

        # Create infrastructure components
        self.create_opensearch()
        self.create_messaging()
        self.create_step_functions()
        self.create_s3_buckets()
        self.create_bedrock()
        self.create_monitoring()
        self.create_scheduled_jobs()

        # Create outputs
        self.create_outputs()

    def import_resources(self):
        """Import resources from ComputeStack"""

        # Import Lambda functions for integrations
        # These will be None if ComputeStack didn't create them
        try:
            self.payment_fn = lambda_.Function.from_function_arn(
                self, "PaymentFunctionImport",
                function_arn=Fn.import_value("ECom67-PaymentFunction")
            )
        except Exception:
            self.payment_fn = None

        try:
            self.order_processor_fn = lambda_.Function.from_function_arn(
                self, "OrderProcessorImport",
                function_arn=Fn.import_value("ECom67-OrderProcessor")
            )
            # Import the role separately for granting permissions
            self.order_processor_role = iam.Role.from_role_arn(
                self, "OrderProcessorRoleImport",
                role_arn=Fn.import_value("ECom67-OrderProcessorRoleArn")
            )
        except Exception:
            self.order_processor_fn = None
            self.order_processor_role = None

        try:
            self.cart_fn = lambda_.Function.from_function_arn(
                self, "CartFunctionImport",
                function_arn=Fn.import_value("ECom67-CartFunction")
            )
        except Exception:
            self.cart_fn = None

    def create_opensearch(self):
        """Create OpenSearch domain for product search"""
        # For development, we'll use a smaller instance
        # Note: In production, use a proper domain with multiple nodes
        self.opensearch_domain = opensearch.Domain(
            self, "ECom67SearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_9,
            capacity=opensearch.CapacityConfig(
                data_node_instance_type="t3.small.search",
                data_nodes=1,
                multi_az_with_standby_enabled=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            ebs=opensearch.EbsOptions(
                enabled=True,
                volume_size=10,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            )
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

        # Enable X-Ray tracing for SQS (via CFN escape hatch)
        cfn_queue = self.order_queue.node.default_child
        cfn_queue.add_property_override("SqsManagedSseEnabled", True)

        # Connect Lambda to SQS (only if order processor function exists)
        if self.order_processor_fn and self.order_processor_role:
            # Grant SQS permissions to Lambda's execution role
            self.order_queue.grant_consume_messages(self.order_processor_role)
            
            # Add SQS event source mapping
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
        
        # Check if required Lambda functions are available
        if not self.payment_fn or not self.order_processor_fn:
            # Fallback to simple pass state if functions not available
            definition = sfn.Pass(
                self, "CheckoutPass",
                comment="Placeholder - Lambda functions not imported"
            )
        else:
            # Define cart validation task (using cart Lambda)
            # Use payload_response_only=True to get direct Lambda response without Payload wrapper
            validate_cart = tasks.LambdaInvoke(
                self, "ValidateCart",
                lambda_function=self.cart_fn,
                payload_response_only=True,  # Returns Lambda response directly without Payload wrapper
                payload=sfn.TaskInput.from_object(
                    {
                        "action": "validate",
                        "userId": sfn.JsonPath.string_at("$.userId"),
                        "orderId": sfn.JsonPath.string_at("$.orderId"),
                        "items": sfn.JsonPath.object_at("$.items"),
                        "totalAmount": sfn.JsonPath.string_at("$.totalAmount"),
                        "paymentToken": sfn.JsonPath.string_at("$.paymentToken"),
                        "email": sfn.JsonPath.string_at("$.email")
                    }
                )
            )
            
            # Define payment failed handler
            payment_failed_handler = sfn.Pass(
                self, "PaymentFailedHandler",
                comment="Payment processing failed",
                result=sfn.Result.from_object({
                    "status": "PAYMENT_FAILED",
                    "message": "Payment processing failed after retries"
                }),
                result_path="$.error"
            )
            
            # Define payment processing task (with retry logic)
            # Use payload_response_only=True for direct Lambda response
            process_payment = tasks.LambdaInvoke(
                self, "ProcessPayment",
                lambda_function=self.payment_fn,
                payload_response_only=True,  # Returns Lambda response directly without Payload wrapper
                payload=sfn.TaskInput.from_object(
                    {
                        "orderId": sfn.JsonPath.string_at("$.orderId"),
                        "userId": sfn.JsonPath.string_at("$.userId"),
                        "amount": sfn.JsonPath.string_at("$.totalAmount"),
                        "paymentToken": sfn.JsonPath.string_at("$.paymentToken"),
                        "items": sfn.JsonPath.object_at("$.items")
                    }
                ),
                retry_on_service_exceptions=True
            )
            
            # Add retry configuration
            process_payment.add_retry(
                interval=Duration.seconds(2),
                max_attempts=3,
                backoff_rate=2.0
            )
            
            # Add catch for payment failures
            process_payment.add_catch(
                payment_failed_handler,
                errors=["States.ALL"],
                result_path="$.error"
            )
            
            # Define SQS send task - send successful order to processing queue
            send_to_queue = tasks.SqsSendMessage(
                self, "SendToQueue",
                queue=self.order_queue,
                message_body=sfn.TaskInput.from_json_path_at("$"),
                result_path="$.queueResult"
            )
            
            # Define success state
            success_state = sfn.Succeed(
                self, "CheckoutSuccess",
                comment="Order successfully submitted for processing"
            )
            
            # Define failure state
            failure_state = sfn.Fail(
                self, "CheckoutFailed",
                comment="Order checkout failed"
            )
            
            # Chain the tasks together:
            # 1. Validate cart
            # 2. Process payment (with retries)
            # 3. Send to queue
            # 4. Success
            definition = validate_cart \
                .next(process_payment) \
                .next(send_to_queue) \
                .next(success_state)

        self.checkout_state_machine = sfn.StateMachine(
            self, "CheckoutStateMachine",
            state_machine_name="e-com67-checkout",
            definition=definition,
            timeout=Duration.minutes(5),
            tracing_enabled=True  # Enable X-Ray tracing for Step Functions
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
        # Lambda Error Alarm (only if payment function exists)
        if self.payment_fn:
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
            self, "OpenSearchDomainEndpoint",
            value=self.opensearch_domain.domain_endpoint,
            description="OpenSearch domain endpoint"
        )

        CfnOutput(
            self, "OrderQueueUrl",
            value=self.order_queue.queue_url,
            description="Order processing queue URL"
        )

        CfnOutput(
            self, "OrderNotificationTopicArn",
            value=self.order_notification_topic.topic_arn,
            description="Order notification SNS topic ARN"
        )

        CfnOutput(
            self, "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="Frontend S3 bucket name"
        )

        CfnOutput(
            self, "KnowledgeBaseBucketName",
            value=self.knowledge_base_bucket.bucket_name,
            description="Knowledge base S3 bucket name"
        )

        CfnOutput(
            self, "CheckoutStateMachineArn",
            value=self.checkout_state_machine.state_machine_arn,
            description="Checkout Step Functions state machine ARN",
            export_name="ECom67-CheckoutStateMachineArn"
        )
