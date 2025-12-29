"""
E-Com67 Platform Backend CI/CD Pipeline Stack

This stack creates a CI/CD pipeline using AWS CodePipeline to automatically
deploy the E-Com67 backend infrastructure when changes are pushed to the master branch.

Architecture:
    Source (CodeCommit) -> Build (CDK Synth + Layer builds) -> Deploy (Data -> Compute -> Api)

The pipeline has self-mutation disabled for stability. Pipeline changes require
manual deployment to avoid circular dependencies.
"""

from aws_cdk import (
    Stack,
    Stage,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as cpactions,
    aws_iam as iam,
    CfnOutput,
)
from aws_cdk import pipelines
from constructs import Construct

from stacks.data_stack import DataStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack


class BackendDeploymentStage(Stage):
    """
    Deployment stage containing all E-Com67 backend stacks.

    This stage bundles DataStack, ComputeStack, and ApiStack together
    for deployment as a single unit in the pipeline.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Data layer - DynamoDB tables, Cognito, OpenSearch, S3
        data_stack = DataStack(
            self,
            "E-Com67-DataStack",
            description="E-Com67 Platform - Data layer with DynamoDB tables and Cognito User Pool"
        )

        # Compute layer - Lambda functions and layers
        compute_stack = ComputeStack(
            self,
            "E-Com67-ComputeStack",
            data_stack=data_stack,
            description="E-Com67 Platform - Compute layer with Lambda functions and layers"
        )

        # API layer - API Gateway with REST endpoints
        api_stack = ApiStack(
            self,
            "E-Com67-ApiStack",
            data_stack=data_stack,
            compute_stack=compute_stack,
            description="E-Com67 Platform - API Gateway with REST endpoints and Cognito authorization"
        )

        # Dependencies are automatically inferred by CDK Pipelines
        # but we add them explicitly for clarity
        compute_stack.add_dependency(data_stack)
        api_stack.add_dependency(data_stack)
        api_stack.add_dependency(compute_stack)


class BackendPipelineStack(Stack):
    """
    CI/CD Pipeline stack for E-Com67 Backend Infrastructure.

    This stack creates a CodePipeline that:
    1. Pulls source from CodeCommit (master branch)
    2. Builds Lambda layers and synthesizes CDK
    3. Deploys all E-Com67 backend stacks in the correct order

    Self-mutation is disabled - pipeline updates require manual deployment.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        repository_name: str = "e-com67",
        branch: str = "master",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Reference the existing CodeCommit repository
        repository = codecommit.Repository.from_repository_name(
            self,
            "E-Com67-Repository",
            repository_name=repository_name
        )

        # Define the source from CodeCommit
        # Uses EventBridge events for automatic triggering on push
        source = pipelines.CodePipelineSource.code_commit(
            repository=repository,
            branch=branch,
            trigger=cpactions.CodeCommitTrigger.EVENTS
        )

        # Create the CDK Pipeline
        pipeline = pipelines.CodePipeline(
            self,
            "BackendPipeline",
            pipeline_name="e-com67-backend-pipeline",

            # Disable self-mutation for stability
            # Pipeline updates are done manually to avoid circular dependencies
            self_mutation=False,

            # Cross-account not needed for single account deployment
            cross_account_keys=False,

            # Synth step - builds the CDK app and Lambda layers
            synth=pipelines.ShellStep(
                "Synth",
                input=source,
                # Set environment variable to synthesize backend pipeline
                env={
                    "USE_BACKEND_PIPELINE": "true",
                },
                # Install dependencies and synthesize CDK
                install_commands=[
                    # Install Python dependencies for CDK
                    "pip install -r requirements.txt",
                    # Install CDK CLI
                    "npm install -g aws-cdk",
                ],
                commands=[
                    # Build Lambda layers
                    "echo 'Building Lambda layers...'",

                    # Powertools layer
                    "pip install -r layers/powertools/requirements.txt -t layers/powertools/python/ --upgrade",

                    # Stripe layer
                    "pip install -r layers/stripe/requirements.txt -t layers/stripe/python/ --upgrade",

                    # OpenSearch layer
                    "pip install -r layers/opensearch/requirements.txt -t layers/opensearch/python/ --upgrade",

                    # Strands layer (standard pip install - architecture-agnostic)
                    "echo 'Building Strands layer...'",
                    "pip install -r layers/strands/requirements-minimal.txt -t layers/strands/python/ --upgrade",
                    "find layers/strands/python -name '*.pyc' -delete",
                    "find layers/strands/python -name '__pycache__' -type d -exec rm -rf {} + || true",

                    # Note: Utils layer contains only custom Python code, no external dependencies

                    # Synthesize CDK
                    "echo 'Synthesizing CDK...'",
                    "cdk synth",
                ],
                # Primary output is the cdk.out directory
                primary_output_directory="cdk.out",
            ),

            # Use a specific CodeBuild environment for layer builds
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    # Use standard image with Python support
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    # Use medium compute type for faster builds
                    compute_type=codebuild.ComputeType.MEDIUM,
                ),
                # Grant permissions needed for deployment
                role_policy=[
                    iam.PolicyStatement(
                        actions=[
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:DescribeSecret",
                        ],
                        resources=["*"],
                        conditions={
                            "StringLike": {
                                "secretsmanager:ResourceTag/aws:cloudformation:stack-name": "E-Com67-*"
                            }
                        }
                    ),
                ],
            ),
            
            # Configure asset publishing to use compatible cdk-assets version
            # IMPORTANT: Must match the schema version generated by CDK in requirements.txt
            # CDK 2.120+ generates schema v48.x which requires cdk-assets v2.120+
            asset_publishing_code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    # Use standard image with Python support
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    # Use medium compute type for faster builds
                    compute_type=codebuild.ComputeType.MEDIUM,
                ),
                # Install latest cdk-assets version for schema compatibility
                partial_build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "commands": [
                                # Install latest cdk-assets to support schema v48.x
                                # cdk-assets versions are independent of aws-cdk-lib versions
                                # Latest version (4.x) ensures compatibility with schema generated by CDK 2.120+
                                "npm install -g cdk-assets@latest"
                            ]
                        }
                    }
                }),
            ),
        )

        # Add the deployment stage
        # The stage deploys all E-Com67 backend stacks (Data -> Compute -> Api)
        pipeline.add_stage(
            BackendDeploymentStage(
                self,
                "Deploy",
                env=kwargs.get("env"),
            )
        )

        # Build the pipeline to finalize it
        pipeline.build_pipeline()

        # Output the pipeline ARN for reference
        CfnOutput(
            self,
            "PipelineArn",
            value=pipeline.pipeline.pipeline_arn,
            description="ARN of the E-Com67 backend CI/CD pipeline"
        )

        CfnOutput(
            self,
            "PipelineName",
            value=pipeline.pipeline.pipeline_name,
            description="Name of the E-Com67 backend CI/CD pipeline"
        )

        CfnOutput(
            self,
            "RepositoryCloneUrl",
            value=repository.repository_clone_url_http,
            description="HTTP clone URL for the CodeCommit repository"
        )
