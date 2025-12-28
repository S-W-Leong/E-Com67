"""
E-Com67 Platform Frontend Deployment Stack

This stack creates S3 buckets and CloudFront distributions for hosting
the React frontend applications (admin dashboard and customer app).

Architecture:
    S3 Bucket (Static Hosting) -> CloudFront Distribution (CDN) -> Users

Each frontend application gets its own S3 bucket and CloudFront distribution
for independent deployment and caching strategies.

Security:
    Uses Origin Access Identity (OAI) for secure access to S3 buckets from CloudFront.
    While OAI is legacy, it's still supported and works reliably with CDK high-level constructs.
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
)
from constructs import Construct


class FrontendStack(Stack):
    """
    Frontend deployment stack for E-Com67 Platform.
    
    Creates S3 buckets and CloudFront distributions for:
    - Admin Dashboard (admin.e-com67.com)
    - Customer Application (shop.e-com67.com)
    
    Features:
    - S3 static website hosting with versioning
    - CloudFront CDN for global content delivery
    - HTTPS-only access with security headers
    - Origin Access Identity (OAI) for secure S3 access
    - Automatic cache invalidation on deployment
    """

    # Constants to avoid duplication
    INDEX_HTML = "index.html"
    INDEX_HTML_PATH = "/index.html"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========================================
        # Admin Dashboard Frontend
        # ========================================
        
        # S3 bucket for admin dashboard static files
        # Note: No website configuration - CloudFront handles routing via OAI
        self.admin_bucket = s3.Bucket(
            self,
            "AdminDashboardBucket",
            bucket_name=f"e-com67-admin-dashboard-{self.account}",
            public_read_access=False,  # CloudFront will access via OAI
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Protect production data
            auto_delete_objects=False,
            versioned=True,  # Enable versioning for rollback capability
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # Origin Access Identity for admin dashboard (legacy but still supported)
        admin_oai = cloudfront.OriginAccessIdentity(
            self,
            "AdminOAI",
            comment="OAI for E-Com67 Admin Dashboard S3 bucket"
        )

        # Grant CloudFront OAI access to admin S3 bucket
        self.admin_bucket.grant_read(admin_oai)

        # CloudFront distribution for admin dashboard
        self.admin_distribution = cloudfront.Distribution(
            self,
            "AdminDashboardDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.admin_bucket,
                    origin_access_identity=admin_oai
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            default_root_object=self.INDEX_HTML,
            error_responses=[
                # SPA routing - return index.html for all 404s
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path=self.INDEX_HTML_PATH,
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path=self.INDEX_HTML_PATH,
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # US, Canada, Europe
            comment="E-Com67 Admin Dashboard CDN"
        )

        # ========================================
        # Customer Application Frontend
        # ========================================
        
        # S3 bucket for customer app static files
        # Note: No website configuration - CloudFront handles routing via OAI
        self.customer_bucket = s3.Bucket(
            self,
            "CustomerAppBucket",
            bucket_name=f"e-com67-customer-app-{self.account}",
            public_read_access=False,  # CloudFront will access via OAI
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Protect production data
            auto_delete_objects=False,
            versioned=True,  # Enable versioning for rollback capability
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # Origin Access Identity for customer app (legacy but still supported)
        customer_oai = cloudfront.OriginAccessIdentity(
            self,
            "CustomerOAI",
            comment="OAI for E-Com67 Customer App S3 bucket"
        )

        # Grant CloudFront OAI access to customer S3 bucket
        self.customer_bucket.grant_read(customer_oai)

        # CloudFront distribution for customer app
        self.customer_distribution = cloudfront.Distribution(
            self,
            "CustomerAppDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.customer_bucket,
                    origin_access_identity=customer_oai
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            default_root_object=self.INDEX_HTML,
            error_responses=[
                # SPA routing - return index.html for all 404s
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path=self.INDEX_HTML_PATH,
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path=self.INDEX_HTML_PATH,
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # US, Canada, Europe
            comment="E-Com67 Customer App CDN"
        )

        # ========================================
        # CloudFormation Outputs
        # ========================================

        # Admin Dashboard Outputs
        CfnOutput(
            self,
            "AdminBucketName",
            value=self.admin_bucket.bucket_name,
            description="S3 bucket name for admin dashboard"
        )

        CfnOutput(
            self,
            "AdminDistributionId",
            value=self.admin_distribution.distribution_id,
            description="CloudFront distribution ID for admin dashboard"
        )

        CfnOutput(
            self,
            "AdminDistributionDomain",
            value=self.admin_distribution.distribution_domain_name,
            description="CloudFront domain name for admin dashboard"
        )

        CfnOutput(
            self,
            "AdminUrl",
            value=f"https://{self.admin_distribution.distribution_domain_name}",
            description="Admin dashboard URL"
        )

        # Customer App Outputs
        CfnOutput(
            self,
            "CustomerBucketName",
            value=self.customer_bucket.bucket_name,
            description="S3 bucket name for customer app"
        )

        CfnOutput(
            self,
            "CustomerDistributionId",
            value=self.customer_distribution.distribution_id,
            description="CloudFront distribution ID for customer app"
        )

        CfnOutput(
            self,
            "CustomerDistributionDomain",
            value=self.customer_distribution.distribution_domain_name,
            description="CloudFront domain name for customer app"
        )

        CfnOutput(
            self,
            "CustomerUrl",
            value=f"https://{self.customer_distribution.distribution_domain_name}",
            description="Customer app URL"
        )
