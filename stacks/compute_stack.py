"""
E-Com67 Platform Compute Stack

This stack contains all compute-related resources:
- Lambda layers for shared dependencies
- Lambda functions for business logic
- Step Functions state machine for order processing
- SQS queues for asynchronous processing
- SNS topics for notifications
- IAM roles and policies
"""

from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    CfnOutput,
    Fn,
    Duration
)
from constructs import Construct
import os
import json


class ComputeStack(Stack):
    """Compute layer stack containing Lambda functions and layers"""

    def __init__(self, scope: Construct, construct_id: str, data_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.data_stack = data_stack
        
        # Create Lambda layers
        self._create_lambda_layers()
        
        # Create messaging infrastructure
        self._create_messaging_infrastructure()
        
        # Create secrets for external services
        self._create_secrets()
        
        # Create Lambda functions
        self._create_lambda_functions()
        
        # Create Step Functions workflow
        self._create_step_functions_workflow()
        
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

    def _create_messaging_infrastructure(self):
        """Create SQS queues and SNS topics for messaging"""
        
        # Dead Letter Queue for failed order processing
        self.order_processing_dlq = sqs.Queue(
            self, "OrderProcessingDLQ",
            queue_name="e-com67-order-processing-dlq",
            retention_period=Duration.days(14),
            removal_policy=self.removal_policy
        )
        
        # Main queue for order processing
        self.order_processing_queue = sqs.Queue(
            self, "OrderProcessingQueue",
            queue_name="e-com67-order-processing",
            visibility_timeout=Duration.minutes(5),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.order_processing_dlq
            ),
            removal_policy=self.removal_policy
        )
        
        # SNS topic for order notifications
        self.order_notifications_topic = sns.Topic(
            self, "OrderNotificationsTopic",
            topic_name="e-com67-order-notifications",
            display_name="E-Com67 Order Notifications"
        )
        
        # SNS topic for admin notifications
        self.admin_notifications_topic = sns.Topic(
            self, "AdminNotificationsTopic",
            topic_name="e-com67-admin-notifications",
            display_name="E-Com67 Admin Notifications"
        )
    
    def _create_secrets(self):
        """Create secrets for external service API keys"""
        
        # Stripe API key secret (placeholder - would be set manually or via CI/CD)
        self.stripe_secret = secretsmanager.Secret(
            self, "StripeApiKeySecret",
            secret_name="e-com67/stripe/api-key",
            description="Stripe API key for payment processing",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"api_key": ""}',
                generate_string_key="api_key",
                exclude_characters=' "%@/\\'
            ),
            removal_policy=self.removal_policy
        )

    def _create_lambda_functions(self):
        """Create Lambda functions with proper IAM roles"""
        
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
        
        # Add SQS permissions
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes"
                ],
                resources=[
                    self.order_processing_queue.queue_arn,
                    self.order_processing_dlq.queue_arn
                ]
            )
        )
        
        # Add SNS permissions
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish"
                ],
                resources=[
                    self.order_notifications_topic.topic_arn,
                    self.admin_notifications_topic.topic_arn
                ]
            )
        )
        
        # Add Secrets Manager permissions
        self.lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue"
                ],
                resources=[
                    self.stripe_secret.secret_arn
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
        
        # Payment function
        self.payment_function = _lambda.Function(
            self, "PaymentFunction",
            function_name="e-com67-payment",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="payment.handler",
            code=_lambda.Code.from_asset("lambda/payment"),
            layers=[self.powertools_layer, self.utils_layer, self.stripe_layer],
            role=self.lambda_execution_role,
            environment={
                "ORDERS_TABLE_NAME": Fn.import_value("E-Com67-OrdersTableName"),
                "STRIPE_SECRET_NAME": self.stripe_secret.secret_name,
                "PAYMENT_TEST_MODE": "false",  # Set to "true" to bypass Stripe for testing
                "POWERTOOLS_SERVICE_NAME": "payment",
                "POWERTOOLS_METRICS_NAMESPACE": "E-Com67",
                "LOG_LEVEL": "INFO"
            },
            tracing=_lambda.Tracing.ACTIVE,
            timeout=Duration.seconds(30)
        )
        
        # Order processor function
        self.order_processor_function = _lambda.Function(
            self, "OrderProcessorFunction",
            function_name="e-com67-order-processor",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="order_processor.handler",
            code=_lambda.Code.from_asset("lambda/order_processor"),
            layers=[self.powertools_layer, self.utils_layer],
            role=self.lambda_execution_role,
            environment={
                "ORDERS_TABLE_NAME": Fn.import_value("E-Com67-OrdersTableName"),
                "PRODUCTS_TABLE_NAME": Fn.import_value("E-Com67-ProductsTableName"),
                "CART_TABLE_NAME": Fn.import_value("E-Com67-CartTableName"),
                "ORDER_NOTIFICATIONS_TOPIC_ARN": self.order_notifications_topic.topic_arn,
                "ADMIN_NOTIFICATIONS_TOPIC_ARN": self.admin_notifications_topic.topic_arn,
                "POWERTOOLS_SERVICE_NAME": "order-processor",
                "POWERTOOLS_METRICS_NAMESPACE": "E-Com67",
                "LOG_LEVEL": "INFO"
            },
            tracing=_lambda.Tracing.ACTIVE,
            timeout=Duration.minutes(5)
        )
        
        # Configure SQS trigger for order processor
        self.order_processor_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue=self.order_processing_queue,
                batch_size=1,  # Process one order at a time
                max_batching_window=Duration.seconds(5)
            )
        )
    
    def _create_step_functions_workflow(self):
        """Create Step Functions state machine for order processing workflow"""
        
        # Create IAM role for Step Functions
        self.step_functions_role = iam.Role(
            self, "StepFunctionsRole",
            role_name="e-com67-step-functions-role",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole")
            ]
        )
        
        # Add SQS permissions for Step Functions
        self.step_functions_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage"
                ],
                resources=[
                    self.order_processing_queue.queue_arn
                ]
            )
        )
        
        # Define Step Functions tasks
        
        # Task 1: Validate cart
        validate_cart_task = sfn_tasks.LambdaInvoke(
            self, "ValidateCartTask",
            lambda_function=self.cart_function,
            payload=sfn.TaskInput.from_object({
                "source": "step-functions",
                "input": sfn.JsonPath.entire_payload
            }),
            result_path="$.cartValidation",
            retry_on_service_exceptions=True
        )
        
        # Task 2: Process payment with retry logic
        process_payment_task = sfn_tasks.LambdaInvoke(
            self, "ProcessPaymentTask",
            lambda_function=self.payment_function,
            payload=sfn.TaskInput.from_object({
                "source": "step-functions",
                "input": sfn.JsonPath.entire_payload
            }),
            result_path="$.paymentResult",
            retry_on_service_exceptions=True
        )
        
        # Add exponential backoff retry for payment failures
        process_payment_task.add_retry(
            errors=["States.ALL"],
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2.0
        )
        
        # Task 3: Send order to processing queue
        send_to_queue_task = sfn_tasks.SqsSendMessage(
            self, "SendToQueueTask",
            queue=self.order_processing_queue,
            message_body=sfn.TaskInput.from_json_path_at("$"),
            result_path="$.queueResult"
        )
        
        # Define failure states
        cart_validation_failed = sfn.Fail(
            self, "CartValidationFailed",
            cause="Cart validation failed",
            error="CART_VALIDATION_ERROR"
        )
        
        payment_failed = sfn.Fail(
            self, "PaymentFailed",
            cause="Payment processing failed after retries",
            error="PAYMENT_PROCESSING_ERROR"
        )
        
        queue_failed = sfn.Fail(
            self, "QueueFailed",
            cause="Failed to send order to processing queue",
            error="QUEUE_SEND_ERROR"
        )
        
        # Define success state
        order_success = sfn.Succeed(
            self, "OrderSuccess",
            comment="Order processing workflow completed successfully"
        )
        
        # Define workflow logic with error handling
        workflow_definition = validate_cart_task.add_catch(
            cart_validation_failed,
            errors=["States.ALL"],
            result_path="$.error"
        ).next(
            sfn.Choice(self, "CartValidationChoice")
            .when(
                sfn.Condition.boolean_equals("$.cartValidation.Payload.isValid", True),
                process_payment_task.add_catch(
                    payment_failed,
                    errors=["States.ALL"],
                    result_path="$.error"
                ).next(
                    sfn.Choice(self, "PaymentChoice")
                    .when(
                        sfn.Condition.boolean_equals("$.paymentResult.Payload.success", True),
                        send_to_queue_task.add_catch(
                            queue_failed,
                            errors=["States.ALL"],
                            result_path="$.error"
                        ).next(order_success)
                    )
                    .otherwise(payment_failed)
                )
            )
            .otherwise(cart_validation_failed)
        )
        
        # Create the state machine
        self.checkout_state_machine = sfn.StateMachine(
            self, "CheckoutStateMachine",
            state_machine_name="e-com67-checkout-workflow",
            definition_body=sfn.DefinitionBody.from_chainable(workflow_definition),
            role=self.step_functions_role,
            timeout=Duration.minutes(15),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self, "CheckoutStateMachineLogGroup",
                    log_group_name="/aws/stepfunctions/e-com67-checkout-workflow",
                    removal_policy=self.removal_policy
                ),
                level=sfn.LogLevel.ALL,
                include_execution_data=True
            )
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
        
        CfnOutput(
            self, "PaymentFunctionArn",
            value=self.payment_function.function_arn,
            export_name="E-Com67-PaymentFunctionArn"
        )
        
        CfnOutput(
            self, "OrderProcessorFunctionArn",
            value=self.order_processor_function.function_arn,
            export_name="E-Com67-OrderProcessorFunctionArn"
        )
        
        # Step Functions exports
        CfnOutput(
            self, "CheckoutStateMachineArn",
            value=self.checkout_state_machine.state_machine_arn,
            export_name="E-Com67-CheckoutStateMachineArn"
        )
        
        # SQS exports
        CfnOutput(
            self, "OrderProcessingQueueArn",
            value=self.order_processing_queue.queue_arn,
            export_name="E-Com67-OrderProcessingQueueArn"
        )
        
        CfnOutput(
            self, "OrderProcessingQueueUrl",
            value=self.order_processing_queue.queue_url,
            export_name="E-Com67-OrderProcessingQueueUrl"
        )
        
        # SNS exports
        CfnOutput(
            self, "OrderNotificationsTopicArn",
            value=self.order_notifications_topic.topic_arn,
            export_name="E-Com67-OrderNotificationsTopicArn"
        )
        
        CfnOutput(
            self, "AdminNotificationsTopicArn",
            value=self.admin_notifications_topic.topic_arn,
            export_name="E-Com67-AdminNotificationsTopicArn"
        )
        
        # IAM role exports
        CfnOutput(
            self, "LambdaExecutionRoleArn",
            value=self.lambda_execution_role.role_arn,
            export_name="E-Com67-LambdaExecutionRoleArn"
        )
        
        CfnOutput(
            self, "StepFunctionsRoleArn",
            value=self.step_functions_role.role_arn,
            export_name="E-Com67-StepFunctionsRoleArn"
        )

    @property
    def removal_policy(self):
        """Get removal policy for development environment"""
        from aws_cdk import RemovalPolicy
        return RemovalPolicy.DESTROY  # For development