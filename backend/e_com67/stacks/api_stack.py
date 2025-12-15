from aws_cdk import Stack, CfnOutput, Fn
from constructs import Construct
from aws_cdk import (
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
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
        user_pool_id = Fn.import_value("ECom67-UserPoolId")

        self.user_pool = cognito.UserPool.from_user_pool_arn(
            self, "ImportedUserPool",
            user_pool_arn=user_pool_arn
        )

        # Import Lambda functions from ComputeStack
        # Only import if they exist (check the pattern used in original stack)
        try:
            product_fn_arn = Fn.import_value("ECom67-ProductFunction")
            self.product_crud_fn = lambda_.Function.from_function_arn(
                self, "ImportedProductFunction",
                function_arn=product_fn_arn
            )
        except:
            self.product_crud_fn = None

        try:
            cart_fn_arn = Fn.import_value("ECom67-CartFunction")
            self.cart_fn = lambda_.Function.from_function_arn(
                self, "ImportedCartFunction",
                function_arn=cart_fn_arn
            )
        except:
            self.cart_fn = None

        try:
            payment_fn_arn = Fn.import_value("ECom67-PaymentFunction")
            self.payment_fn = lambda_.Function.from_function_arn(
                self, "ImportedPaymentFunction",
                function_arn=payment_fn_arn
            )
        except:
            self.payment_fn = None

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
                allow_methods=apigw.Cors.ALL_METHODS
            ),
            deploy_options=apigw.StageOptions(
                tracing_enabled=True  # Enable X-Ray tracing for API Gateway
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
