"""
E-Com67 Platform Admin Insights Stack

This stack contains resources for the Admin Insights Agent:
- Bedrock Guardrails for PII detection and prompt attack prevention
- IAM roles for agent execution, tool execution, and MCP gateway
- Lambda functions for analytics tools (Order Trends, Sales Insights, Product Search)
- Lambda function for Admin Insights Agent runtime
- API Gateway endpoints for agent interaction
"""

from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    CfnOutput,
    Fn,
    Duration
)
from constructs import Construct


class AdminInsightsStack(Stack):
    """Admin Insights Agent stack with Bedrock AgentCore, guardrails, and analytics tools"""

    def __init__(self, scope: Construct, construct_id: str, data_stack, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.data_stack = data_stack
        
        # Create Bedrock Guardrail for security
        self._create_guardrail()
        
        # Create IAM roles
        self._create_iam_roles()
        
        # Create Lambda layers
        self._create_lambda_layers()
        
        # Create analytics tool Lambda functions
        self._create_analytics_tool_lambdas()
        
        # Create cross-stack exports
        self._create_exports()

    def _create_guardrail(self):
        """Create Bedrock Guardrail with PII detection and prompt attack filters"""
        self.guardrail = bedrock.CfnGuardrail(
            self, "AdminInsightsGuardrail",
            name="admin-insights-guardrail",
            description="Guardrail for Admin Insights Agent to detect PII and prompt attacks",
            blocked_input_messaging="Your request contains content that cannot be processed. Please remove any sensitive information and try again.",
            blocked_outputs_messaging="The response contains sensitive information and cannot be displayed.",
            
            # PII detection and blocking
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    # Email addresses
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="EMAIL",
                        action="BLOCK"
                    ),
                    # Phone numbers
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PHONE",
                        action="BLOCK"
                    ),
                    # Credit card numbers
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_NUMBER",
                        action="BLOCK"
                    ),
                    # Social Security Numbers
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="US_SOCIAL_SECURITY_NUMBER",
                        action="BLOCK"
                    ),
                    # Addresses
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="ADDRESS",
                        action="BLOCK"
                    )
                ]
            ),
            
            # Prompt attack detection
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="PROMPT_ATTACK",
                        input_strength="MEDIUM",
                        output_strength="NONE"  # Only scan inputs for prompt attacks
                    )
                ]
            )
        )

    def _create_iam_roles(self):
        """Create IAM roles for agent execution, tool execution, and MCP gateway"""
        
        # Agent Execution Role - for the main agent Lambda function
        self.agent_execution_role = iam.Role(
            self, "AgentExecutionRole",
            role_name="e-com67-admin-insights-agent-execution",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Admin Insights Agent with Bedrock, Guardrails, Memory, and Lambda permissions",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add Bedrock permissions for model invocation
        self.agent_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    # Allow Amazon Nova models
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-*",
                    "arn:aws:bedrock:*:*:inference-profile/apac.amazon.nova-*"
                ]
            )
        )
        
        # Add Bedrock Guardrails permissions
        self.agent_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ApplyGuardrail"
                ],
                resources=[
                    self.guardrail.attr_guardrail_arn
                ]
            )
        )
        
        # Add Bedrock AgentCore Memory permissions
        self.agent_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:CreateMemory",
                    "bedrock:GetMemory",
                    "bedrock:UpdateMemory",
                    "bedrock:DeleteMemory",
                    "bedrock:ListMemories"
                ],
                resources=["*"]  # Memory resources are account-scoped
            )
        )
        
        # Add Lambda invoke permissions for analytics tools
        self.agent_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:e-com67-admin-insights-*"
                ]
            )
        )
        
        # Tool Execution Role - for analytics tool Lambda functions
        self.tool_execution_role = iam.Role(
            self, "ToolExecutionRole",
            role_name="e-com67-admin-insights-tool-execution",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Admin Insights analytics tools with DynamoDB and OpenSearch permissions",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess")
            ]
        )
        
        # Add DynamoDB permissions for analytics queries
        self.tool_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem"
                ],
                resources=[
                    Fn.import_value("E-Com67-OrdersTableArn"),
                    Fn.import_value("E-Com67-ProductsTableArn"),
                    f"{Fn.import_value('E-Com67-OrdersTableArn')}/index/*",
                    f"{Fn.import_value('E-Com67-ProductsTableArn')}/index/*"
                ]
            )
        )
        
        # Add OpenSearch permissions for product search
        self.tool_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "es:ESHttpGet",
                    "es:ESHttpPost"
                ],
                resources=[
                    Fn.import_value("E-Com67-OpenSearchDomainArn"),
                    f"{Fn.import_value('E-Com67-OpenSearchDomainArn')}/*"
                ]
            )
        )
        
        # MCP Gateway Role - for external system access
        self.mcp_gateway_role = iam.Role(
            self, "MCPGatewayRole",
            role_name="e-com67-admin-insights-mcp-gateway",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Execution role for MCP Gateway to invoke analytics tools",
        )
        
        # Add Lambda invoke permissions for MCP Gateway
        self.mcp_gateway_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:e-com67-admin-insights-*"
                ]
            )
        )

    def _create_lambda_layers(self):
        """Reference Lambda layers from ComputeStack"""
        # Reference existing layers by ARN pattern
        # These layers are created in ComputeStack and we reference them here
        self.powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayerRef",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:e-com67-powertools:1"
        )
        
        self.utils_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "UtilsLayerRef",
            layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:e-com67-utils:1"
        )

    def _create_analytics_tool_lambdas(self):
        """Create Lambda functions for analytics tools"""
        
        # Lambda function for Order Trends Tool
        self.order_trends_lambda = _lambda.Function(
            self, "OrderTrendsLambda",
            function_name="e-com67-admin-insights-order-trends",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="order_trends.handler",
            code=_lambda.Code.from_asset("lambda/admin_insights_tools"),
            role=self.tool_execution_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "ORDERS_TABLE_NAME": Fn.import_value("E-Com67-OrdersTableName"),
                "PRODUCTS_TABLE_NAME": Fn.import_value("E-Com67-ProductsTableName"),
                "REGION": self.region,
                "POWERTOOLS_SERVICE_NAME": "admin-insights-order-trends",
                "LOG_LEVEL": "INFO"
            },
            layers=[self.powertools_layer, self.utils_layer],
            description="Analytics tool for order trends analysis",
            tracing=_lambda.Tracing.ACTIVE
        )
        
        # Lambda function for Sales Insights Tool
        self.sales_insights_lambda = _lambda.Function(
            self, "SalesInsightsLambda",
            function_name="e-com67-admin-insights-sales-insights",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="sales_insights.handler",
            code=_lambda.Code.from_asset("lambda/admin_insights_tools"),
            role=self.tool_execution_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "ORDERS_TABLE_NAME": Fn.import_value("E-Com67-OrdersTableName"),
                "PRODUCTS_TABLE_NAME": Fn.import_value("E-Com67-ProductsTableName"),
                "REGION": self.region,
                "POWERTOOLS_SERVICE_NAME": "admin-insights-sales-insights",
                "LOG_LEVEL": "INFO"
            },
            layers=[self.powertools_layer, self.utils_layer],
            description="Analytics tool for sales insights and product performance",
            tracing=_lambda.Tracing.ACTIVE
        )
        
        # Lambda function for Product Search Tool
        self.product_search_lambda = _lambda.Function(
            self, "ProductSearchLambda",
            function_name="e-com67-admin-insights-product-search",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="product_search.handler",
            code=_lambda.Code.from_asset("lambda/admin_insights_tools"),
            role=self.tool_execution_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "OPENSEARCH_ENDPOINT": Fn.import_value("E-Com67-OpenSearchEndpoint"),
                "REGION": self.region,
                "POWERTOOLS_SERVICE_NAME": "admin-insights-product-search",
                "LOG_LEVEL": "INFO"
            },
            layers=[self.powertools_layer, self.utils_layer],
            description="Analytics tool for product search using OpenSearch",
            tracing=_lambda.Tracing.ACTIVE
        )

    def _create_exports(self):
        """Create CloudFormation exports for cross-stack resource sharing"""
        
        # Guardrail exports
        CfnOutput(
            self, "GuardrailId",
            value=self.guardrail.attr_guardrail_id,
            export_name="E-Com67-AdminInsightsGuardrailId",
            description="Admin Insights Guardrail ID"
        )
        
        CfnOutput(
            self, "GuardrailArn",
            value=self.guardrail.attr_guardrail_arn,
            export_name="E-Com67-AdminInsightsGuardrailArn",
            description="Admin Insights Guardrail ARN"
        )
        
        # IAM role exports
        CfnOutput(
            self, "AgentExecutionRoleArn",
            value=self.agent_execution_role.role_arn,
            export_name="E-Com67-AdminInsightsAgentExecutionRoleArn",
            description="Admin Insights Agent Execution Role ARN"
        )
        
        CfnOutput(
            self, "ToolExecutionRoleArn",
            value=self.tool_execution_role.role_arn,
            export_name="E-Com67-AdminInsightsToolExecutionRoleArn",
            description="Admin Insights Tool Execution Role ARN"
        )
        
        CfnOutput(
            self, "MCPGatewayRoleArn",
            value=self.mcp_gateway_role.role_arn,
            export_name="E-Com67-AdminInsightsMCPGatewayRoleArn",
            description="Admin Insights MCP Gateway Role ARN"
        )
        
        # Lambda function exports
        CfnOutput(
            self, "OrderTrendsLambdaArn",
            value=self.order_trends_lambda.function_arn,
            export_name="E-Com67-AdminInsightsOrderTrendsLambdaArn",
            description="Order Trends Analytics Tool Lambda ARN"
        )
        
        CfnOutput(
            self, "SalesInsightsLambdaArn",
            value=self.sales_insights_lambda.function_arn,
            export_name="E-Com67-AdminInsightsSalesInsightsLambdaArn",
            description="Sales Insights Analytics Tool Lambda ARN"
        )
        
        CfnOutput(
            self, "ProductSearchLambdaArn",
            value=self.product_search_lambda.function_arn,
            export_name="E-Com67-AdminInsightsProductSearchLambdaArn",
            description="Product Search Analytics Tool Lambda ARN"
        )
