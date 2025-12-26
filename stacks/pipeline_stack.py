"""
E-Com67 Platform Pipeline Stack

This stack creates a CI/CD pipeline using AWS CodePipeline to automatically
deploy the E-Com67 platform when changes are pushed to the master branch.

Architecture:
    Source (CodeCommit) -> Build (CDK Synth + Layer builds) -> Deploy (Data -> Compute -> Api)

The pipeline is self-mutating, meaning it will update itself when pipeline
code changes are pushed to the repository.
"""

from aws_cdk import (
    Stack,
    Stage,
    Environment,
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


class E_Com67Stage(Stage):
    """
    Deployment stage containing all E-Com67 stacks.

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


class PipelineStack(Stack):
    """
    CI/CD Pipeline stack for E-Com67 Platform.

    This stack creates a self-mutating CodePipeline that:
    1. Pulls source from CodeCommit (master branch)
    2. Builds Lambda layers and synthesizes CDK
    3. Deploys all E-Com67 stacks in the correct order

    The pipeline automatically updates itself when changes are detected
    in the pipeline definition.
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
        # If it doesn't exist, you'll need to create it first
        repository = codecommit.Repository.from_repository_name(
            self,
            "E-Com67-Repository",
            repository_name=repository_name
        )

        # Define the source from CodeCommit
        # Uses EventBridge events by default for faster triggering
        source = pipelines.CodePipelineSource.code_commit(
            repository=repository,
            branch=branch,
            # EVENTS = trigger on push via EventBridge (faster)
            # POLL = poll for changes (slower but works without EventBridge)
            # NONE = no automatic trigger
            trigger=cpactions.CodeCommitTrigger.EVENTS
        )

        # Create the CDK Pipeline with self-mutation disabled
        # Pipeline changes require manual deployment:
        #   USE_PIPELINE=true cdk deploy E-Com67-PipelineStack
        pipeline = pipelines.CodePipeline(
            self,
            "E-Com67-Pipeline",
            pipeline_name="e-com67-pipeline",

            # Disable self-mutation - pipeline updates are done manually
            # This prevents pipeline failures from blocking application deployments
            self_mutation=False,

            # Cross-account not needed for single account deployment
            cross_account_keys=False,

            # Synth step - builds the CDK app and Lambda layers
            # IMPORTANT: Strands layer requires Linux ARM64 binaries for Lambda compatibility
            synth=pipelines.ShellStep(
                "Synth",
                input=source,
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

                    # Strands layer (use Docker to build for ARM64 architecture)
                    "echo 'Building Strands layer for ARM64 using Docker...'",
                    "docker run --rm -v $(pwd)/layers/strands:/workspace -w /workspace --platform linux/arm64 python:3.10-slim bash -c 'pip install -r requirements-minimal.txt -t python/ --no-cache-dir && find python -name \"*.pyc\" -delete && find python -name \"__pycache__\" -type d -exec rm -rf {} + || true'",

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
                    # Use standard image with Python support and Docker
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    # Use medium compute for Docker builds
                    compute_type=codebuild.ComputeType.MEDIUM,
                    # Enable privileged mode for Docker
                    privileged=True,
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
        )

        # Add the deployment stage
        # The stage deploys all E-Com67 stacks (Data -> Compute -> Api)
        pipeline.add_stage(
            E_Com67Stage(
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
            description="ARN of the E-Com67 CI/CD pipeline"
        )

        CfnOutput(
            self,
            "RepositoryCloneUrl",
            value=repository.repository_clone_url_http,
            description="HTTP clone URL for the CodeCommit repository"
        )
