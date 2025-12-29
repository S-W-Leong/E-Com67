"""
E-Com67 Platform Customer App CI/CD Pipeline Stack

This stack creates a CI/CD pipeline using AWS CodePipeline to automatically
build and deploy the customer application React app when changes are pushed
to the master branch.

Architecture:
    Source (CodeCommit) -> Build (npm build) -> Deploy (S3 + CloudFront invalidation)

The pipeline monitors the frontends/customer-app/ directory for changes.
"""

from aws_cdk import (
    Stack,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_iam as iam,
    aws_ssm as ssm,
    CfnOutput,
)
from constructs import Construct


class CustomerPipelineStack(Stack):
    """
    CI/CD Pipeline stack for E-Com67 Customer Application Frontend.

    This stack creates a CodePipeline that:
    1. Pulls source from CodeCommit (master branch)
    2. Builds the React application with npm
    3. Deploys to S3 and invalidates CloudFront cache

    The pipeline automatically triggers on changes to frontends/customer-app/
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        repository_name: str = "e-com67",
        branch: str = "master",
        customer_bucket: s3.IBucket = None,
        customer_distribution: cloudfront.IDistribution = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Reference the existing CodeCommit repository
        repository = codecommit.Repository.from_repository_name(
            self,
            "E-Com67-Repository",
            repository_name=repository_name
        )

        # Create artifacts for pipeline stages
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")

        # Source action - pull from CodeCommit
        source_action = cpactions.CodeCommitSourceAction(
            action_name="Source",
            repository=repository,
            branch=branch,
            output=source_output,
            trigger=cpactions.CodeCommitTrigger.EVENTS,  # Trigger on push
        )

        # Build project for React application
        build_project = codebuild.PipelineProject(
            self,
            "CustomerBuildProject",
            project_name="e-com67-customer-app-build",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "nodejs": "20"
                        },
                        "commands": [
                            "echo 'Installing dependencies...'",
                            "echo 'Node.js version:'",
                            "node --version",
                            "echo 'npm version:'",
                            "npm --version",
                            "echo 'Installing shared package dependencies first...'",
                            "cd frontends/shared",
                            "npm install",
                            "cd ../customer-app",
                            "echo 'Checking if package-lock.json exists...'",
                            "ls -la package*",
                            "if [ -f package-lock.json ]; then npm ci; else echo 'No package-lock.json found, using npm install' && npm install; fi",
                        ]
                    },
                    "pre_build": {
                        "commands": [
                            "echo 'Running pre-build checks...'",
                            "npm run lint || true",  # Don't fail on lint errors
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo 'Setting up environment variables from SSM Parameter Store...'",
                            "export VITE_STRIPE_PUBLISHABLE_KEY=$(aws ssm get-parameter --name /ecom67/stripe/publishable-key --query 'Parameter.Value' --output text --region $AWS_REGION)",
                            "export VITE_AWS_REGION=$AWS_REGION",
                            "export VITE_USER_POOL_ID=$(aws ssm get-parameter --name /ecom67/cognito/user-pool-id --query 'Parameter.Value' --output text --region $AWS_REGION)",
                            "export VITE_USER_POOL_CLIENT_ID=$(aws ssm get-parameter --name /ecom67/cognito/user-pool-client-id --query 'Parameter.Value' --output text --region $AWS_REGION)",
                            "export VITE_API_BASE_URL=$(aws ssm get-parameter --name /ecom67/api/base-url --query 'Parameter.Value' --output text --region $AWS_REGION)",
                            "export VITE_WEBSOCKET_URL=$(aws ssm get-parameter --name /ecom67/api/websocket-url --query 'Parameter.Value' --output text --region $AWS_REGION)",
                            "export VITE_ENV=production",
                            "echo 'Environment variables configured'",
                            "echo 'Building React application...'",
                            "npm run build",
                        ]
                    },
                },
                "artifacts": {
                    "base-directory": "frontends/customer-app/dist",
                    "files": ["**/*"]
                },
                "cache": {
                    "paths": [
                        "frontends/shared/node_modules/**/*",
                        "frontends/customer-app/node_modules/**/*"
                    ]
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.SMALL,
            ),
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.SOURCE,
                codebuild.LocalCacheMode.CUSTOM
            ),
        )

        # Grant SSM Parameter Store read permissions to build project
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter", "ssm:GetParameters"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/ecom67/*"
                ]
            )
        )

        # Build action
        build_action = cpactions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output],
        )

        # Deploy action - upload to S3
        deploy_action = cpactions.S3DeployAction(
            action_name="Deploy",
            bucket=customer_bucket,
            input=build_output,
            extract=True,  # Extract the build artifacts
        )

        # CloudFront invalidation action
        invalidation_project = codebuild.PipelineProject(
            self,
            "CustomerInvalidationProject",
            project_name="e-com67-customer-app-invalidation",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": [
                            "echo 'Invalidating CloudFront distribution...'",
                            f"aws cloudfront create-invalidation --distribution-id {customer_distribution.distribution_id} --paths '/*'",
                        ]
                    }
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.SMALL,
            ),
        )

        # Grant CloudFront invalidation permissions
        invalidation_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudfront:CreateInvalidation"],
                resources=[f"arn:aws:cloudfront::{self.account}:distribution/{customer_distribution.distribution_id}"]
            )
        )

        invalidation_action = cpactions.CodeBuildAction(
            action_name="InvalidateCache",
            project=invalidation_project,
            input=build_output,
        )

        # Create the pipeline
        pipeline = codepipeline.Pipeline(
            self,
            "CustomerPipeline",
            pipeline_name="e-com67-customer-app-pipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[source_action]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[build_action]
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[deploy_action, invalidation_action]
                ),
            ],
            cross_account_keys=False,
        )

        # Outputs
        CfnOutput(
            self,
            "PipelineName",
            value=pipeline.pipeline_name,
            description="Name of the customer app CI/CD pipeline"
        )

        CfnOutput(
            self,
            "PipelineArn",
            value=pipeline.pipeline_arn,
            description="ARN of the customer app CI/CD pipeline"
        )
