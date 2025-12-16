from aws_cdk import Stack, CfnOutput, Fn
from constructs import Construct
from aws_cdk import (
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_stepfunctions as sfn,
)


class ApiStack(Stack):
    """
    API Layer Stack - API Gateway and endpoint configurations.

    Contains:
    - REST API Gateway
    - API endpoints with Lambda integrations
    - Cognito authorization
    - CORS configuration

    Imports from:
    - DataStack: Cognito User Pool
    - ComputeStack: Lambda functions

    Lifecycle: Moderate updates, endpoint changes
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import resources from other stacks
        self.import_resources()

        # Create API Gateway
        self.create_api_gateway()

        # Create CloudFormation Outputs
        self.create_outputs()

    def import_resources(self):
        """Import resources from DataStack and ComputeStack"""

        # Import Cognito User Pool from DataStack
        user_pool_arn = Fn.import_value("ECom67-UserPoolArn")

        self.user_pool = cognito.UserPool.from_user_pool_arn(
            self, "ImportedUserPool",
            user_pool_arn=user_pool_arn
        )

        # Import Step Functions state machine from InfraStack
        self.checkout_state_machine_arn = Fn.import_value("ECom67-CheckoutStateMachineArn")

        # Import Lambda functions from ComputeStack
        # Note: We import using from_function_attributes instead of from_function_arn
        # to allow API Gateway to add invoke permissions
        product_fn_arn = Fn.import_value("ECom67-ProductFunction")
        product_fn_name = Fn.import_value("ECom67-ProductFunctionName")
        self.product_crud_fn = lambda_.Function.from_function_attributes(
            self, "ImportedProductFunction",
            function_arn=product_fn_arn,
            same_environment=True  # Allow permission grants
        )

        cart_fn_arn = Fn.import_value("ECom67-CartFunction")
        cart_fn_name = Fn.import_value("ECom67-CartFunctionName")
        self.cart_fn = lambda_.Function.from_function_attributes(
            self, "ImportedCartFunction",
            function_arn=cart_fn_arn,
            same_environment=True  # Allow permission grants
        )

        payment_fn_arn = Fn.import_value("ECom67-PaymentFunction")
        payment_fn_name = Fn.import_value("ECom67-PaymentFunctionName")
        self.payment_fn = lambda_.Function.from_function_attributes(
            self, "ImportedPaymentFunction",
            function_arn=payment_fn_arn,
            same_environment=True  # Allow permission grants
        )

        # Import Orders function (GET orders)
        orders_fn_arn = Fn.import_value("ECom67-OrdersFunction")
        orders_fn_name = Fn.import_value("ECom67-OrdersFunctionName")
        self.orders_fn = lambda_.Function.from_function_attributes(
            self, "ImportedOrdersFunction",
            function_arn=orders_fn_arn,
            same_environment=True
        )

    def create_api_gateway(self):
        """Create REST API with Cognito authorization"""

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
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    'Authorization',
                    'Content-Type',
                    'X-Amz-Date',
                    'X-Api-Key',
                    'X-Amz-Security-Token'
                ]
            ),
            deploy_options=apigw.StageOptions(
                tracing_enabled=True  # Enable X-Ray tracing for API Gateway
            )
        )

        # Products endpoints
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
        cart.add_method(
            "DELETE",
            apigw.LambdaIntegration(self.cart_fn),
            authorizer=authorizer
        )

        # Orders endpoint - Direct Step Functions integration
        orders = self.api.root.add_resource("orders")
        
        # Create IAM role for API Gateway to invoke Step Functions
        sfn_role = iam.Role(
            self, "ApiGatewayStepFunctionsRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="Role for API Gateway to invoke Step Functions"
        )
        
        sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[self.checkout_state_machine_arn]
            )
        )
        
        # Create Step Functions integration
        sfn_integration = apigw.AwsIntegration(
            service="states",
            action="StartExecution",
            options=apigw.IntegrationOptions(
                credentials_role=sfn_role,
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'",
                            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
                            "method.response.header.Access-Control-Allow-Methods": "'OPTIONS,POST'"
                        },
                        response_templates={
                            "application/json": '''
#set($inputRoot = $input.path('$'))
{
  "executionArn": "$inputRoot.executionArn",
  "startDate": "$inputRoot.startDate",
  "message": "Order checkout initiated successfully"
}
'''
                        }
                    ),
                    apigw.IntegrationResponse(
                        status_code="400",
                        selection_pattern="4\\d{2}",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                        response_templates={
                            "application/json": '{"error": "Bad request"}'
                        }
                    ),
                    apigw.IntegrationResponse(
                        status_code="500",
                        selection_pattern="5\\d{2}",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                        response_templates={
                            "application/json": '{"error": "Internal server error"}'
                        }
                    )
                ],
                request_templates={
                    "application/json": f'''
#set($inputRoot = $input.path('$'))
#set($context.requestOverride.header.X-Amz-Date = $context.requestTime)
{{
  "stateMachineArn": "{self.checkout_state_machine_arn}",
  "input": "$util.escapeJavaScript($input.json('$'))"
}}
'''
                }
            )
        )
        
        # Add POST method for orders with Step Functions integration
        orders.add_method(
            "POST",
            sfn_integration,
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                ),
                apigw.MethodResponse(
                    status_code="400",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                ),
                apigw.MethodResponse(
                    status_code="500",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

        # Add GET method for retrieving orders
        orders.add_method(
            "GET",
            apigw.LambdaIntegration(self.orders_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

    def create_outputs(self):
        """Create CloudFormation outputs for cross-stack references"""

        CfnOutput(
            self, "ApiUrl",
            value=self.api.url,
            description="API Gateway endpoint URL",
            export_name="ECom67-ApiUrl"
        )

        CfnOutput(
            self, "ApiId",
            value=self.api.rest_api_id,
            description="API Gateway REST API ID",
            export_name="ECom67-ApiId"
        )

        CfnOutput(
            self, "ApiRootResourceId",
            value=self.api.rest_api_root_resource_id,
            description="API Gateway root resource ID",
            export_name="ECom67-ApiRootResourceId"
        )
