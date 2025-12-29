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
        # Use explicit stack_name to match existing manually-deployed stacks
        data_stack = DataStack(
            self,
            "E-Com67-DataStack",
            stack_name="E-Com67-DataStack",  # Override nested naming
            description="E-Com67 Platform - Data layer with DynamoDB tables and Cognito User Pool"
        )

        # Compute layer - Lambda functions and layers
        compute_stack = ComputeStack(
            self,
            "E-Com67-ComputeStack",
            stack_name="E-Com67-ComputeStack",  # Override nested naming
            data_stack=data_stack,
            description="E-Com67 Platform - Compute layer with Lambda functions and layers"
        )

        # API layer - API Gateway with REST endpoints
        api_stack = ApiStack(
            self,
            "E-Com67-ApiStack",
            stack_name="E-Com67-ApiStack",  # Override nested naming
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
                    "npm install -g aws-cdk@latest",
                ],
                commands=[
                    # Build Lambda layers
                    "echo 'Building Lambda layers...'",

                    # Clean all layer python directories first to ensure deterministic builds
                    # This prevents stale files from causing asset hash mismatches
                    "echo 'Cleaning layer directories...'",
                    "rm -rf layers/powertools/python layers/stripe/python layers/opensearch/python layers/strands/python",

                    # Powertools layer
                    "pip install -r layers/powertools/requirements.txt -t layers/powertools/python/ --no-cache-dir",

                    # Stripe layer
                    "pip install -r layers/stripe/requirements.txt -t layers/stripe/python/ --no-cache-dir",

                    # OpenSearch layer
                    "pip install -r layers/opensearch/requirements.txt -t layers/opensearch/python/ --no-cache-dir",

                    # Strands layer (standard pip install - architecture-agnostic)
                    "echo 'Building Strands layer...'",
                    "pip install -r layers/strands/requirements-minimal.txt -t layers/strands/python/ --no-cache-dir",

                    # Clean up non-deterministic files from all layers (bytecode, cache, dist-info metadata)
                    "echo 'Cleaning non-deterministic files from layers...'",
                    "find layers/*/python -name '*.pyc' -delete 2>/dev/null || true",
                    "find layers/*/python -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true",
                    "find layers/*/python -name '*.dist-info' -type d -exec rm -rf {} + 2>/dev/null || true",
                    "find layers/*/python -name 'RECORD' -delete 2>/dev/null || true",

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
            # IMPORTANT: CDK Pipelines by default installs cdk-assets@2 (schema v39)
            # but we need cdk-assets v3+ for schema v48 generated by CDK 2.120+
            # We override in BOTH install AND build phases because CDK Pipelines
            # adds its own cdk-assets@2 install command after the install phase
            asset_publishing_code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    # Use standard image with Python support
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    # Use medium compute type for faster builds
                    compute_type=codebuild.ComputeType.MEDIUM,
                ),
                # Override cdk-assets installation in pre_build phase (runs after install)
                partial_build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "commands": [
                                # This runs first, but CDK Pipelines adds cdk-assets@2 after
                                "npm install -g cdk-assets@latest"
                            ]
                        },
                        "pre_build": {
                            "commands": [
                                # Re-install latest cdk-assets AFTER CDK Pipelines installs @2
                                # This ensures we have v4.x which supports schema v48
                                "echo 'Overriding cdk-assets version for schema v48 compatibility...'",
                                "npm install -g cdk-assets@latest",
                                "cdk-assets --version"
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
