"""
E-Com67 Platform Backend CI/CD Pipeline Stack

This stack creates a simple CI/CD pipeline using AWS CodePipeline and CodeBuild
to automatically deploy the E-Com67 backend infrastructure when changes are
pushed to the master branch.

Architecture:
    Source (CodeCommit) -> Build & Deploy (CodeBuild runs cdk deploy)

This approach uses a single CodeBuild project that builds Lambda layers and
runs `cdk deploy` directly, avoiding the asset hash mismatch issues that can
occur with CDK Pipelines' separate synth/publish/deploy stages.
"""

from aws_cdk import (
    Stack,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class BackendPipelineStack(Stack):
    """
    CI/CD Pipeline stack for E-Com67 Backend Infrastructure.

    This stack creates a CodePipeline that:
    1. Pulls source from CodeCommit (master branch)
    2. Runs a CodeBuild project that builds layers and deploys via cdk deploy

    Using `cdk deploy` directly in CodeBuild ensures layers are built and
    deployed in the same environment, eliminating asset hash mismatches.
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

        # Create CodeBuild project for building and deploying
        build_project = codebuild.PipelineProject(
            self,
            "BuildAndDeploy",
            project_name="e-com67-backend-build-deploy",
            description="Builds Lambda layers and deploys E-Com67 backend stacks",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                privileged=False,
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.11",
                            "nodejs": "18"
                        },
                        "commands": [
                            "echo 'Installing dependencies...'",
                            "pip install -r requirements.txt",
                            "npm install -g aws-cdk@latest",
                            # Build Lambda layers BEFORE CDK synth runs
                            # This ensures asset hashes match the actual layer contents
                            "echo 'Building Lambda layers...'",
                            # Clean layer directories for deterministic builds
                            # Note: utils layer is NOT cleaned because it contains only pure Python code
                            # with no external dependencies - the source files are used directly
                            "rm -rf layers/powertools/python layers/stripe/python layers/opensearch/python layers/strands/python",
                            # Install layer dependencies with platform targeting for Lambda
                            # Use --python-version 3.10 to ensure binary compatibility with Lambda Python 3.10 runtime
                            "pip install -r layers/powertools/requirements.txt -t layers/powertools/python/ --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: || pip install -r layers/powertools/requirements.txt -t layers/powertools/python/ --no-cache-dir",
                            "pip install -r layers/stripe/requirements.txt -t layers/stripe/python/ --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: || pip install -r layers/stripe/requirements.txt -t layers/stripe/python/ --no-cache-dir",
                            "pip install -r layers/opensearch/requirements.txt -t layers/opensearch/python/ --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: || pip install -r layers/opensearch/requirements.txt -t layers/opensearch/python/ --no-cache-dir",
                            # Strands layer: Use pip with explicit Python version and platform for Lambda compatibility
                            "pip install -r layers/strands/requirements-minimal.txt -t layers/strands/python/ --no-cache-dir --platform manylinux2014_x86_64 --python-version 3.10 --only-binary=:all: --implementation cp || pip install -r layers/strands/requirements-minimal.txt -t layers/strands/python/ --no-cache-dir",
                            # Utils layer has no external dependencies - just ensure the structure is correct
                            "echo 'Utils layer already contains pure Python code - no build needed'",
                            # Clean non-deterministic files that cause hash mismatches
                            "find layers/*/python -name '*.pyc' -delete 2>/dev/null || true",
                            "find layers/*/python -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true",
                            "find layers/*/python -name '*.dist-info' -type d -exec rm -rf {} + 2>/dev/null || true",
                            "find layers/*/python -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true",
                            # Show layer sizes to debug size limit issues
                            "echo 'Layer sizes:' && du -sh layers/*/python || true",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo 'Deploying backend stacks...'",
                            # Deploy stacks in order: Data -> Compute -> Api -> AdminInsights
                            # AdminInsightsStack must be deployed LAST after ComputeStack because it
                            # imports layer ARNs. This order ensures layer exports are updated before
                            # AdminInsightsStack tries to import them, avoiding export conflicts.
                            "cdk deploy E-Com67-DataStack --require-approval never",
                            "cdk deploy E-Com67-ComputeStack --require-approval never",
                            "cdk deploy E-Com67-ApiStack --require-approval never",
                            "cdk deploy E-Com67-AdminInsightsStack --require-approval never",
                        ]
                    }
                },
                "cache": {
                    "paths": [
                        "/root/.npm/**/*",
                        "/root/.cache/pip/**/*",
                    ]
                }
            }),
            cache=codebuild.Cache.local(codebuild.LocalCacheMode.CUSTOM),
        )

        # Grant CodeBuild permissions to deploy CloudFormation stacks
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudFormationFullAccess",
                actions=[
                    "cloudformation:*",
                ],
                resources=[
                    f"arn:aws:cloudformation:{self.region}:{self.account}:stack/E-Com67-*/*",
                    f"arn:aws:cloudformation:{self.region}:{self.account}:stack/CDKToolkit/*",
                ]
            )
        )

        # Grant permissions for CDK bootstrap resources
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="CDKBootstrapAccess",
                actions=[
                    "s3:*",
                ],
                resources=[
                    f"arn:aws:s3:::cdk-*-assets-{self.account}-{self.region}",
                    f"arn:aws:s3:::cdk-*-assets-{self.account}-{self.region}/*",
                ]
            )
        )

        # Grant SSM parameter access for CDK bootstrap version check
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="SSMParameterAccess",
                actions=[
                    "ssm:GetParameter",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*",
                ]
            )
        )

        # Grant IAM permissions for CDK to manage roles
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="IAMPassRole",
                actions=[
                    "iam:PassRole",
                ],
                resources=[
                    f"arn:aws:iam::{self.account}:role/cdk-*",
                ]
            )
        )

        # Grant STS permissions for CDK to assume roles
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="STSAssumeRole",
                actions=[
                    "sts:AssumeRole",
                ],
                resources=[
                    f"arn:aws:iam::{self.account}:role/cdk-*",
                ]
            )
        )

        # Grant permissions for all AWS services used by the stacks
        # This is broad but necessary for CDK to create/update resources
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                sid="AWSServicesAccess",
                actions=[
                    # Lambda
                    "lambda:*",
                    # DynamoDB
                    "dynamodb:*",
                    # API Gateway
                    "apigateway:*",
                    # Cognito
                    "cognito-idp:*",
                    # S3
                    "s3:*",
                    # SQS
                    "sqs:*",
                    # SNS
                    "sns:*",
                    # Step Functions
                    "states:*",
                    # CloudWatch Logs
                    "logs:*",
                    # IAM (for creating roles)
                    "iam:*",
                    # Secrets Manager
                    "secretsmanager:*",
                    # OpenSearch
                    "es:*",
                    "aoss:*",
                    # ECR (for any container-based lambdas)
                    "ecr:*",
                    # Events (for EventBridge)
                    "events:*",
                ],
                resources=["*"]
            )
        )

        # Create the pipeline
        pipeline = codepipeline.Pipeline(
            self,
            "BackendPipeline",
            pipeline_name="e-com67-backend-pipeline",
            pipeline_type=codepipeline.PipelineType.V2,
        )

        # Source stage - pull from CodeCommit
        source_output = codepipeline.Artifact("SourceOutput")
        source_action = cpactions.CodeCommitSourceAction(
            action_name="CodeCommit",
            repository=repository,
            branch=branch,
            output=source_output,
            trigger=cpactions.CodeCommitTrigger.EVENTS,
        )
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action],
        )

        # Build and Deploy stage
        build_action = cpactions.CodeBuildAction(
            action_name="BuildAndDeploy",
            project=build_project,
            input=source_output,
        )
        pipeline.add_stage(
            stage_name="BuildAndDeploy",
            actions=[build_action],
        )

        # Outputs
        CfnOutput(
            self,
            "PipelineArn",
            value=pipeline.pipeline_arn,
            description="ARN of the E-Com67 backend CI/CD pipeline"
        )

        CfnOutput(
            self,
            "PipelineName",
            value=pipeline.pipeline_name,
            description="Name of the E-Com67 backend CI/CD pipeline"
        )

        CfnOutput(
            self,
            "BuildProjectName",
            value=build_project.project_name,
            description="Name of the CodeBuild project"
        )

        CfnOutput(
            self,
            "RepositoryCloneUrl",
            value=repository.repository_clone_url_http,
            description="HTTP clone URL for the CodeCommit repository"
        )
