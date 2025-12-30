# E-Com67 Platform

A comprehensive serverless e-commerce platform built on AWS demonstrating modern cloud architecture patterns, microservices design, and advanced features including AI-powered customer support, real-time search, and automated order processing.

**Latest Update**: Added Admin Insights Agent with Amazon Nova Pro, Bedrock Guardrails, and analytics tools. Meta Pixel integration for customer tracking. OpenTelemetry Lambda layer fix for Strands SDK compatibility.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [AWS Services Used](#aws-services-used)
- [Prerequisites](#prerequisites)
- [Setup and Deployment](#setup-and-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Frontend Applications](#frontend-applications)
- [API Reference](#api-reference)
- [Lambda Functions](#lambda-functions)
- [Data Models](#data-models)
- [Authentication](#authentication)
- [Payment Processing](#payment-processing)
- [AI Chat Feature](#ai-chat-feature)
- [Search Functionality](#search-functionality)
- [Notification System](#notification-system)
- [Meta Pixel Integration](#meta-pixel-integration)
- [Testing](#system-testing)
- [Monitoring and Observability](#monitoring-and-observability)
- [Technical Notes](#technical-notes)
- [Utility Scripts](#utility-scripts)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

E-Com67 implements a serverless microservices architecture on AWS with the following key characteristics:

- **Event-Driven Design**: Asynchronous processing using SQS, SNS, and Step Functions
- **API-First Approach**: RESTful APIs with WebSocket support for real-time features
- **Serverless Computing**: Lambda functions for all business logic with automatic scaling
- **Managed Services**: DynamoDB, OpenSearch, Cognito, Bedrock, and more
- **Multi-Stack CDK**: Clear separation of concerns across Data, Compute, and API layers

### High-Level Architecture

```
                          +-------------------+
                          |    CloudFront     |
                          |   (CDN - Future)  |
                          +---------+---------+
                                    |
              +---------------------+---------------------+
              |                                           |
    +---------v---------+                     +-----------v-----------+
    |    REST API       |                     |    WebSocket API      |
    |   API Gateway     |                     |    API Gateway        |
    +---------+---------+                     +-----------+-----------+
              |                                           |
    +---------v-----------------------------------------+-v-----------+
    |                       Lambda Functions                          |
    |  +------------+  +--------+  +---------+  +-------+  +-------+  |
    |  |ProductCRUD |  | Cart   |  | Orders  |  |Payment|  | Chat  |  |
    |  +------------+  +--------+  +---------+  +-------+  +-------+  |
    +------------------+----------+----------+------------+-----------+
                       |          |          |            |
         +-------------+   +------+------+   +------------+
         |                 |             |                |
    +----v----+      +-----v-----+  +----v----+     +-----v-----+
    | DynamoDB|      |Step Fns   |  |   SQS   |     | Bedrock   |
    | Tables  |      |Workflow   |  | Queues  |     | (AI/ML)   |
    +---------+      +-----------+  +---------+     +-----------+
         |
    +----v--------+
    | OpenSearch  |
    | (Search)    |
    +-------------+
```

### Stack Dependencies

```
DataStack (DynamoDB, Cognito, OpenSearch, S3)
    |
    v
ComputeStack (Lambda, SQS, SNS, Step Functions, Secrets)
    |
    +---> ApiStack (REST API Gateway, WebSocket API Gateway)
    |
    +---> AdminInsightsStack (Admin Analytics Agent, Guardrails, WebSocket API)

FrontendStack (S3 Buckets, CloudFront Distributions)
    |
    +---> AdminPipelineStack (Admin Dashboard CI/CD)
    |
    +---> CustomerPipelineStack (Customer App CI/CD)
```

### CI/CD Pipeline Architecture (Optional)

```
BackendPipelineStack (CodePipeline, CodeBuild)
    |
    v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Source    │───►│    Synth    │───►│   Deploy    │
│ (CodeCommit)│    │ (cdk synth) │    │   Stages    │
└─────────────┘    └─────────────┘    └─────────────┘
                                              |
                              ┌───────────────┼───────────────────┐
                              v               v                   v
                         DataStack      ComputeStack          ApiStack

FrontendStack (S3 + CloudFront)
    |
    +---> AdminPipelineStack (CodePipeline)
    |         |
    |         v
    |     ┌─────────┐    ┌─────────┐    ┌───────────────────────┐
    |     │ Source  │───►│  Build  │───►│ Deploy + Invalidate   │
    |     └─────────┘    └─────────┘    └───────────────────────┘
    |
    +---> CustomerPipelineStack (CodePipeline)
              |
              v
          ┌─────────┐    ┌─────────┐    ┌───────────────────────┐
          │ Source  │───►│  Build  │───►│ Deploy + Invalidate   │
          └─────────┘    └─────────┘    └───────────────────────┘
```

---

## Project Structure

```
e-com67/
├── app.py                      # CDK application entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # Python dependencies
├── deploy.sh                   # Deployment helper script
│
├── stacks/                     # AWS CDK stack definitions
│   ├── data_stack.py          # DynamoDB, Cognito, OpenSearch, S3
│   ├── compute_stack.py       # Lambda, SQS, SNS, Step Functions
│   ├── api_stack.py           # API Gateway (REST + WebSocket)
│   ├── admin_insights_stack.py # Admin Insights Agent, Guardrails, Analytics
│   ├── frontend_stack.py      # S3 buckets and CloudFront distributions
│   ├── backend_pipeline_stack.py    # Backend CI/CD Pipeline
│   ├── admin_pipeline_stack.py      # Admin dashboard CI/CD Pipeline
│   └── customer_pipeline_stack.py   # Customer app CI/CD Pipeline
│
├── lambda/                     # Lambda function implementations
│   ├── product_crud/          # Product CRUD operations
│   ├── cart/                  # Shopping cart management
│   ├── orders/                # Order retrieval and history
│   ├── payment/               # Stripe payment processing
│   ├── order_processor/       # Async order fulfillment (SQS)
│   ├── chat/                  # AI chat (Strands SDK + Bedrock)
│   │   ├── chat.py           # Main WebSocket handler
│   │   ├── strands_config.py # Strands agent configuration
│   │   ├── models.py         # Pydantic response models
│   │   ├── response_formatters.py # Response formatting utilities
│   │   ├── validation_utils.py    # Data validation helpers
│   │   └── tools/            # Custom Strands agent tools
│   │       ├── product_search_tool.py    # Product search integration
│   │       ├── cart_management_tool.py   # Cart operations
│   │       ├── order_query_tool.py       # Order queries
│   │       └── knowledge_base_tool.py    # RAG knowledge base
│   ├── search/                # OpenSearch product search
│   ├── search_sync/           # DynamoDB Streams -> OpenSearch sync
│   ├── knowledge_processor/   # RAG document processing
│   ├── knowledge_manager/     # Knowledge base management
│   ├── notification_orchestrator/  # Notification routing
│   ├── email_notification/    # SES email sending
│   ├── admin_insights_agent/  # Admin Insights AI agent
│   │   ├── handler.py         # Main agent WebSocket handler
│   │   ├── agent.py           # Bedrock AgentCore integration
│   │   ├── websocket_connect.py    # Connection handler
│   │   └── websocket_disconnect.py # Disconnect handler
│   └── admin_insights_tools/  # Admin analytics tools
│       ├── order_trends.py    # Order trends analysis
│       ├── sales_insights.py  # Sales performance analytics
│       └── product_search.py  # Product search analytics
│
├── layers/                     # Shared Lambda layers
│   ├── powertools/            # AWS Lambda Powertools
│   ├── utils/                 # Common utilities, CORS, validators
│   ├── stripe/                # Stripe SDK
│   ├── opensearch/            # OpenSearch Python client
│   └── strands/               # Strands AI agent SDK
│
├── frontends/                  # React applications
│   ├── customer-app/          # Customer shopping interface
│   ├── admin-dashboard/       # Admin management interface
│   └── shared/                # Shared components and utilities
│
├── docs/                       # Additional documentation
│   ├── api-endpoints.md
│   ├── stripe-frontend-integration.md
│   ├── knowledge-base-guide.md
│   └── notification-system-integration.md
│
├── scripts/                    # Utility scripts
│   ├── manage_knowledge_base.py    # Knowledge base management
│   ├── create_admin_insights_memory.py # Create AgentCore memory
│   ├── build_strands_layer.sh      # Build Strands SDK layer
│   └── setup-stripe-secret.sh      # Configure Stripe API key
│
├── tests/                      # Test files
│
└── buildspec.yml               # CodeBuild specification (for reference)
```

---

## AWS Services Used

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **DynamoDB** | Primary database for products, cart, orders, chat | On-demand billing, point-in-time recovery |
| **Cognito** | User authentication and authorization | Email-based sign-in, JWT tokens |
| **API Gateway** | REST API and WebSocket endpoints | Cognito authorizer, CORS enabled |
| **Lambda** | Serverless compute for all business logic | Python 3.9/3.10, X-Ray tracing |
| **Step Functions** | Order processing workflow orchestration | Checkout workflow with retry logic |
| **SQS** | Asynchronous message processing | Order processing queue with DLQ |
| **SNS** | Event notifications | Order and admin notification topics |
| **OpenSearch** | Full-text product search | t3.small.search, single node |
| **S3** | Knowledge base document storage | Versioned, encrypted |
| **Bedrock** | AI-powered chat and embeddings | Titan Text Express, Titan Embed |
| **SES** | Email notifications | Order confirmations, alerts |
| **Secrets Manager** | API key storage | Stripe API key |
| **CloudWatch** | Logging and monitoring | Structured logs, custom metrics |
| **X-Ray** | Distributed tracing | Enabled on all Lambda functions |
| **CloudFront** | CDN for frontend delivery | HTTPS-only, SPA routing support |
| **CodePipeline** | CI/CD pipeline orchestration | EventBridge triggered, three separate pipelines |
| **CodeBuild** | Build and synthesis | Lambda layers, CDK synth, npm builds |
| **CodeCommit** | Source code repository | Git-based version control |
| **Bedrock Guardrails** | AI safety and PII protection | PII detection, prompt attack filtering |
| **Amazon Nova** | AI model for Admin Insights | amazon.nova-pro-v1:0 for analytics agent |

---

## Prerequisites

- **Python 3.9+** (3.10 recommended for Strands SDK)
- **Node.js 18+** and npm
- **AWS CLI** configured with appropriate credentials
- **AWS CDK CLI** (`npm install -g aws-cdk`)
- **Stripe account** (test mode for development)

### Required AWS Permissions

Your AWS credentials must have permissions to create:
- IAM roles and policies
- DynamoDB tables
- Lambda functions and layers
- API Gateway APIs
- Cognito user pools
- OpenSearch domains
- S3 buckets
- SQS queues and SNS topics
- Step Functions state machines
- Secrets Manager secrets
- CloudWatch log groups

---

## Setup and Deployment

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd e-com67

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Install Lambda Layer Dependencies

```bash
# Install dependencies for each layer
cd layers/powertools && pip install -r requirements.txt -t python/ && cd ../..
cd layers/stripe && pip install -r requirements.txt -t python/ && cd ../..
cd layers/opensearch && pip install -r requirements.txt -t python/ && cd ../..
cd layers/strands && pip install -r requirements.txt -t python/ && cd ../..
```

### 3. Configure Environment

Set the required environment variables:

```bash
export CDK_DEFAULT_ACCOUNT=<your-aws-account-id>
export CDK_DEFAULT_REGION=ap-southeast-1  # or your preferred region
```

### 4. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION
```

### 5. Deploy the Stacks

```bash
# Deploy all stacks in order
cdk deploy E-Com67-DataStack --require-approval never
cdk deploy E-Com67-ComputeStack --require-approval never
cdk deploy E-Com67-ApiStack --require-approval never

# Or deploy all at once
cdk deploy --all --require-approval never
```

### 6. Configure Stripe API Key

After deployment, update the Stripe secret in AWS Secrets Manager:

```bash
aws secretsmanager update-secret \
  --secret-id e-com67/stripe/api-key \
  --secret-string '{"api_key": "sk_test_your_stripe_key"}'
```

### 7. Get API Endpoints

```bash
# Get the REST API endpoint
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='RestApiEndpoint'].OutputValue" \
  --output text

# Get the WebSocket API endpoint
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketApiUrl'].OutputValue" \
  --output text
```

---

## CI/CD Pipeline

E-Com67 uses a **three-pipeline architecture** for automated deployments:

1. **Backend Pipeline** - Deploys infrastructure (Data, Compute, API stacks)
2. **Admin Dashboard Pipeline** - Builds and deploys admin React app
3. **Customer App Pipeline** - Builds and deploys customer React app

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CodeCommit Repository                            │
│                            (master branch)                               │
└────────────┬────────────────────────┬────────────────────────┬──────────┘
             │                        │                        │
             ▼                        ▼                        ▼
┌────────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│  Backend Pipeline      │ │  Admin Pipeline    │ │  Customer Pipeline │
│  ─────────────────     │ │  ──────────────    │ │  ─────────────     │
│  Source → Synth →      │ │  Source → Build →  │ │  Source → Build →  │
│  Deploy (Data →        │ │  Deploy (S3) →     │ │  Deploy (S3) →     │
│  Compute → Api)        │ │  Invalidate CF     │ │  Invalidate CF     │
└────────────────────────┘ └────────────────────┘ └────────────────────┘
```

### Key Features

| Feature | Backend Pipeline | Frontend Pipelines |
|---------|-----------------|-------------------|
| **Trigger** | EventBridge on push to master | EventBridge on push to master |
| **Build** | CDK synth + Lambda layers | npm build (React) |
| **Deploy** | CloudFormation stacks | S3 + CloudFront invalidation |
| **Self-Mutation** | Disabled (manual updates) | N/A |
| **Dependencies** | Data → Compute → Api | Requires FrontendStack |

### Deployment Modes

E-Com67 supports multiple deployment modes:

| Mode | Command | Use Case |
|------|---------|----------|
| **Direct** | `cdk deploy --all` | Development, testing, manual deployments |
| **Backend Pipeline** | `USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack` | Automated backend infrastructure |
| **Frontend Pipelines** | `USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack` | Automated frontend deployments |

### Manual Setup

#### Prerequisites

1. **Create CodeCommit Repository** (if not exists):

```bash
# Create the repository
aws codecommit create-repository --repository-name e-com67 --region ap-southeast-1

# Add CodeCommit as a remote
git remote add codecommit https://git-codecommit.ap-southeast-1.amazonaws.com/v1/repos/e-com67

# Push code to CodeCommit
git push codecommit master
```

#### Step 1: Deploy Backend Pipeline

```bash
# Deploy the backend infrastructure pipeline
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack --require-approval never
```

This creates the pipeline that will automatically deploy:
- DataStack (DynamoDB, Cognito, OpenSearch, S3)
- ComputeStack (Lambda functions and layers)
- ApiStack (API Gateway)

#### Step 2: Deploy Frontend Stack

```bash
# Deploy S3 buckets and CloudFront distributions
cdk deploy E-Com67-FrontendStack --require-approval never
```

This creates:
- S3 bucket for admin dashboard (`e-com67-admin-dashboard-{account}`)
- S3 bucket for customer app (`e-com67-customer-app-{account}`)
- CloudFront distributions for both apps with:
  - Origin Access Identity (OAI) for secure S3 access
  - HTTPS-only redirection
  - SPA routing support (404 → index.html)
  - Gzip compression enabled
  - Price Class 100 (US, Canada, Europe)

#### Step 3: Deploy Frontend Pipelines

```bash
# Deploy both frontend pipelines (requires FrontendStack to be deployed first)
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack --require-approval never
```

This creates two separate pipelines that will automatically:
- **Admin Dashboard Pipeline**: Build and deploy `frontends/admin-dashboard/`
- **Customer App Pipeline**: Build and deploy `frontends/customer-app/`

Each pipeline performs:
1. npm install/ci (with shared package support for customer app)
2. npm run build (React → static files)
3. S3 deployment (upload to respective bucket)
4. CloudFront cache invalidation (clear CDN cache)

### Triggering Pipelines

All pipelines automatically trigger on push to `master`:

```bash
git add .
git commit -m "Your changes"
git push codecommit master
```

Or manually trigger specific pipelines:

```bash
# Backend pipeline
aws codepipeline start-pipeline-execution --name e-com67-backend-pipeline

# Admin dashboard pipeline
aws codepipeline start-pipeline-execution --name e-com67-admin-dashboard-pipeline

# Customer app pipeline
aws codepipeline start-pipeline-execution --name e-com67-customer-app-pipeline
```

### Pipeline Details

#### Backend Pipeline Stages

| Stage | Description | CodeBuild Specs |
|-------|-------------|-----------------|
| **Source** | Pulls latest code from CodeCommit `master` branch | EventBridge trigger on push |
| **Synth** | Installs Python dependencies, builds Lambda layers (powertools, utils, stripe, opensearch, strands), runs `cdk synth` | Standard 7.0, Medium compute |
| **Deploy** | Deploys DataStack → ComputeStack → ApiStack sequentially using CDK Pipelines | CloudFormation changesets |

**Key Features:**
- Self-mutation disabled for stability
- Lambda layers built during synth stage
- Compatible cdk-assets version (2.233.0)
- Secrets Manager access for deployment

#### Frontend Pipeline Stages

| Pipeline | Stage | Description | Build Details |
|----------|-------|-------------|---------------|
| **Admin Dashboard** | Source | Pulls from CodeCommit `master` | EventBridge trigger |
| | Build | Runs `npm ci/install` and `npm run build` in `frontends/admin-dashboard/` | Node.js 20, outputs to `dist/` |
| | Deploy | Uploads to S3 + CloudFront invalidation | S3DeployAction + CodeBuild invalidation |
| **Customer App** | Source | Pulls from CodeCommit `master` | EventBridge trigger |
| | Build | Installs shared package deps, then builds in `frontends/customer-app/` | Node.js 20, outputs to `dist/` |
| | Deploy | Uploads to S3 + CloudFront invalidation | S3DeployAction + CodeBuild invalidation |

**Key Features:**
- Separate pipelines for independent deployment
- Local caching for node_modules
- Lint check (non-blocking)
- CloudFront invalidation creates a new CodeBuild project for cache clearing

### Updating Pipelines

**Backend Pipeline:**
Self-mutation is disabled for stability. To update the pipeline itself:

```bash
USE_BACKEND_PIPELINE=true cdk deploy E-Com67-BackendPipelineStack
```

**Frontend Pipelines:**
Frontend pipelines are standard CodePipeline resources. Update them with:

```bash
USE_FRONTEND_PIPELINES=true cdk deploy E-Com67-AdminPipelineStack E-Com67-CustomerPipelineStack
```

### Monitoring Pipeline Execution

```bash
# View backend pipeline status
aws codepipeline get-pipeline-state --name e-com67-backend-pipeline

# View admin dashboard pipeline status
aws codepipeline get-pipeline-state --name e-com67-admin-dashboard-pipeline

# View customer app pipeline status
aws codepipeline get-pipeline-state --name e-com67-customer-app-pipeline

# View execution history
aws codepipeline list-pipeline-executions --pipeline-name e-com67-backend-pipeline

# Get pipeline outputs
aws cloudformation describe-stacks \
  --stack-name E-Com67-BackendPipelineStack \
  --query "Stacks[0].Outputs" \
  --output table
```

### Accessing Deployed Frontends

After FrontendStack is deployed, you can access the CloudFront URLs:

```bash
# Get admin dashboard CloudFront URL
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='AdminUrl'].OutputValue" \
  --output text

# Get customer app CloudFront URL
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='CustomerUrl'].OutputValue" \
  --output text

# Get S3 bucket names
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'BucketName')].{Key:OutputKey, Value:OutputValue}" \
  --output table

# Get CloudFront distribution IDs
aws cloudformation describe-stacks \
  --stack-name E-Com67-FrontendStack \
  --query "Stacks[0].Outputs[?contains(OutputKey, 'DistributionId')].{Key:OutputKey, Value:OutputValue}" \
  --output table
```

**CloudFront Features:**
- HTTPS-only access with automatic redirection
- SPA routing support (404/403 errors redirect to index.html)
- Gzip compression enabled for faster load times
- Origin Access Identity (OAI) prevents direct S3 access
- Price Class 100 (optimized for US, Canada, Europe)

### Troubleshooting Pipelines

**Backend Pipeline Issues:**

1. **Pipeline Not Triggering:**
   - Verify EventBridge rule exists for the repository
   - Check that you're pushing to the `master` branch
   - Ensure CodeCommit repository name matches (`e-com67`)

2. **Build Failures:**
   - Check CodeBuild logs in CloudWatch
   - Verify Lambda layer dependencies are compatible
   - Ensure CDK synth runs successfully locally first

3. **Deployment Failures:**
   - Review CloudFormation events for the failing stack
   - Check IAM permissions for the pipeline role
   - Verify resource limits haven't been exceeded

**Frontend Pipeline Issues:**

1. **Build Failures:**
   - Check CodeBuild logs for npm errors
   - Verify package.json and dependencies are correct
   - Ensure build script exists in package.json

2. **Deployment Failures:**
   - Verify S3 bucket permissions
   - Check CloudFront distribution status
   - Ensure build output directory matches buildspec

3. **Cache Invalidation Failures:**
   - Verify CloudFront invalidation permissions
   - Check distribution ID is correct
   - Review CloudWatch logs for invalidation project

### Cost Considerations

**Pipeline Costs:**
- CodePipeline: $1/month per active pipeline × 3 pipelines = $3/month
- CodeBuild: $0.005/minute (build time)
  - Backend builds: ~5-8 minutes (Lambda layers + CDK synth)
  - Frontend builds: ~2-3 minutes each (npm build)
- S3: Storage for artifacts (~$0.023/GB)
- CloudFront:
  - Data transfer: $0.085/GB (first 10TB)
  - Requests: $0.0075 per 10,000 HTTPS requests
  - Origin fetch: Free from S3 in same region

**Estimated Monthly Costs:**
- 3 pipelines (backend + 2 frontends): $3/month
- Build time (10 builds/month):
  - Backend: ~$0.40/month (8 min × 10 builds × $0.005)
  - Frontends: ~$0.30/month (3 min × 2 × 10 builds × $0.005)
- Artifacts storage: <$1/month
- CloudFront (dev/low traffic): ~$1-5/month
  - 2 distributions (admin + customer)
  - Caching reduces origin requests

**Total:** ~$6-10/month for CI/CD infrastructure
**Total with CloudFront:** ~$10-20/month (including frontend delivery)

---

## Frontend Applications

### Customer App

The customer-facing React application for shopping.

```bash
cd frontends/customer-app

# Install dependencies
npm install

# Configure environment
cat > .env.local << EOF
VITE_API_BASE_URL=https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/prod
VITE_WEBSOCKET_URL=wss://<websocket-id>.execute-api.ap-southeast-1.amazonaws.com/prod
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
EOF

# Start development server
npm run dev  # Runs on http://localhost:3001

# Build for production
npm run build
```

**Tech Stack:**
- React 18 + Vite
- Tailwind CSS
- AWS Amplify (authentication)
- Stripe.js (payments)
- React Router

### Admin Dashboard

The administrative interface for managing products and orders.

```bash
cd frontends/admin-dashboard

# Install dependencies
npm install

# Configure environment (same as customer app)

# Start development server
npm run dev  # Runs on http://localhost:3002

# Build for production
npm run build
```

---

## API Reference

### Base URL

```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```

### Authentication

Protected endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <id-token>
```

### Endpoints

#### Products (Public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| GET | `/products/{id}` | Get product details |
| GET | `/search?q={query}` | Search products |
| GET | `/search/suggest?q={query}` | Get search suggestions |

**Query Parameters for GET /products:**
- `category` - Filter by category
- `limit` - Number of items (default: 20)
- `lastKey` - Pagination key

**Query Parameters for GET /search:**
- `q` - Search query (required)
- `category` - Filter by category
- `minPrice` / `maxPrice` - Price range
- `limit` - Number of results

#### Products (Admin - Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/products` | Create product |
| PUT | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Delete product |
| GET | `/admin/products` | List with admin details |

#### Cart (Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cart` | Get cart contents |
| POST | `/cart` | Add/update item |
| DELETE | `/cart?productId={id}` | Remove item |

**POST /cart Body:**
```json
{
  "productId": "uuid",
  "quantity": 1
}
```

#### Orders (Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | Get order history |
| GET | `/orders/{id}` | Get order details |
| POST | `/orders` | Place order (triggers Step Functions) |

**POST /orders Body:**
```json
{
  "paymentMethodId": "pm_xxx",
  "shippingAddress": {
    "street": "123 Main St",
    "city": "Singapore",
    "state": "SG",
    "zipCode": "123456",
    "country": "Singapore"
  }
}
```

#### Payment (Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payment` | Create payment intent |
| GET | `/payment/status` | Get payment status |
| POST | `/payment/webhook` | Stripe webhook (public) |
| POST | `/payment/refund` | Process refund (admin) |

#### Admin (Requires Auth + Admin Role)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/orders` | List all orders |
| PUT | `/admin/orders/{id}` | Update order status |

#### Chat (Requires Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `wss://{websocket-id}.execute-api.{region}.amazonaws.com/prod` | Real-time chat |

**WebSocket Routes:**
- `$connect` - Establish connection with authentication
- `$disconnect` - Clean up connection and session
- `sendMessage` - Send message to Strands AI agent

**Message Format:**
```json
{
  "action": "sendMessage",
  "message": "Help me find a gaming laptop under $1000",
  "sessionId": "session-uuid",
  "metadata": {}
}
```

**Response Format:**
```json
{
  "type": "message",
  "message": "I found 5 gaming laptops under $1000!",
  "data": {
    "response_type": "product_list",
    "products": [...],
    "suggestions": ["Would you like to see more details?"],
    "tools_used": ["product_search"],
    "action_buttons": [
      {"text": "View Details", "action": "view_product"},
      {"text": "Add to Cart", "action": "add_to_cart"}
    ]
  },
  "timestamp": 1703425200000,
  "sessionId": "session-uuid"
}
```

#### Admin Insights Agent (Requires Auth + Admin Role)

| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `wss://{admin-insights-websocket-id}.execute-api.{region}.amazonaws.com/prod` | Admin analytics agent |

**WebSocket Routes:**
- `$connect` - Establish connection with token authentication
- `$disconnect` - Clean up connection and terminate session
- `sendMessage` - Send analytics query to Admin Insights Agent

**Message Format:**
```json
{
  "action": "sendMessage",
  "message": "What were the top selling products this week?",
  "sessionId": "session-uuid"
}
```

**Response Format:**
```json
{
  "type": "message",
  "message": "Based on this week's data, here are the top selling products...",
  "data": {
    "tools_used": ["order_trends", "sales_insights"],
    "analytics": {...}
  },
  "sessionId": "session-uuid"
}
```

**Guardrails:**
- PII (email, phone, credit card, SSN, addresses) is automatically blocked
- Prompt injection attacks are filtered
- Blocked requests receive appropriate error messages

### Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "The requested product could not be found",
    "details": {
      "productId": "invalid-uuid",
      "timestamp": "2025-12-24T10:30:00Z",
      "requestId": "req-uuid"
    }
  }
}
```

---

## Lambda Functions

### Product CRUD (`e-com67-product-crud`)

Handles all product catalog operations including create, read, update, and delete.

**Key Features:**
- Category-based filtering using GSI
- Pagination support
- Soft delete (sets `isActive=false`)
- Input validation

### Cart (`e-com67-cart`)

Manages user shopping carts with real-time pricing validation.

**Key Features:**
- Stock availability checking
- Real-time price updates
- Tax calculation (8% hardcoded)
- Cart validation for checkout

### Orders (`e-com67-orders`)

Handles order history retrieval and order details.

**Key Features:**
- Pagination using userId-timestamp GSI
- Cursor-based pagination
- Order status tracking

### Payment (`e-com67-payment`)

Processes payments through Stripe integration.

**Key Features:**
- Payment intent creation
- Fraud detection scoring
- Multiple currency support (USD, EUR, GBP, AUD, CAD)
- Webhook signature verification

### Order Processor (`e-com67-order-processor`)

Asynchronous order fulfillment triggered by SQS.

**Key Features:**
- Creates order records
- Updates inventory
- Sends notifications via SNS
- Clears user cart

### Chat (`e-com67-chat`)

AI-powered customer support using **Strands AI Agent SDK** with Amazon Bedrock integration.

**Key Features:**
- **Strands Agent Integration**: Enhanced conversational AI with custom tool system
- **WebSocket Connection Handling**: Real-time bidirectional communication
- **Custom Tools System**: Direct integration with E-Com67 platform APIs
  - Product search with OpenSearch integration
  - Cart management with real-time validation
  - Order queries with user access control
  - Knowledge base with RAG capabilities
- **Conversation Context Management**: Session persistence and history tracking
- **Structured Responses**: Type-safe responses using Pydantic models
- **Error Handling & Fallbacks**: Graceful degradation and retry mechanisms
- **Performance Optimization**: Lazy initialization and efficient caching

### Search (`e-com67-search`)

Full-text product search using OpenSearch.

**Key Features:**
- Fuzzy matching for typo tolerance
- Category and price filtering
- Result highlighting
- Faceted search with aggregations

### Search Sync (`e-com67-search-sync`)

Keeps OpenSearch index synchronized with DynamoDB.

**Key Features:**
- DynamoDB Streams trigger
- Real-time index updates
- Handles insert, modify, delete events

### Admin Insights Agent (`e-com67-admin-insights-agent`)

AI-powered analytics agent for admin dashboard using Amazon Nova and Bedrock AgentCore.

**Key Features:**
- Bedrock AgentCore with session-based memory
- Amazon Nova Pro v1 model for natural language understanding
- Bedrock Guardrails for PII protection and prompt attack filtering
- WebSocket-based real-time communication
- Integrates with analytics tools (Order Trends, Sales Insights, Product Search)

### Admin Insights Analytics Tools

Three specialized Lambda functions for business analytics:

| Function | Description |
|----------|-------------|
| `e-com67-admin-insights-order-trends` | Analyzes order patterns, revenue trends, and growth rates with configurable time grouping |
| `e-com67-admin-insights-sales-insights` | Provides sales performance metrics and product analytics |
| `e-com67-admin-insights-product-search` | Product discovery and search analytics using OpenSearch |

**Guardrails Protection:**
- PII detection (email, phone, credit card, SSN, addresses)
- Prompt attack filtering
- Blocked content messaging for sensitive information

---

## Data Models

### Products Table (`e-com67-products`)

| Attribute | Type | Description |
|-----------|------|-------------|
| productId | String (PK) | UUID |
| name | String | Product name |
| description | String | Product description |
| price | Number | Price in dollars |
| category | String | Product category (GSI) |
| stock | Number | Available quantity |
| imageUrl | String | Product image URL |
| tags | List | Searchable tags |
| isActive | Boolean | Active status |
| createdAt | Number | Unix timestamp |
| updatedAt | Number | Unix timestamp |

**GSI:** `category-index` (category)

### Cart Table (`e-com67-cart`)

| Attribute | Type | Description |
|-----------|------|-------------|
| userId | String (PK) | Cognito user sub |
| productId | String (SK) | Product ID |
| quantity | Number | Item quantity |
| price | Number | Price at time of adding |
| name | String | Product name |
| imageUrl | String | Product image |
| addedAt | Number | Unix timestamp |

### Orders Table (`e-com67-orders`)

| Attribute | Type | Description |
|-----------|------|-------------|
| orderId | String (PK) | UUID |
| userId | String | Cognito user sub |
| items | List | Order items |
| subtotal | Number | Subtotal amount |
| tax | Number | Tax amount |
| totalAmount | Number | Total amount |
| status | String | Order status |
| paymentId | String | Stripe payment intent ID |
| shippingAddress | Map | Shipping details |
| timestamp | Number | Unix timestamp (GSI SK) |

**GSI:** `userId-timestamp-index` (userId, timestamp)

### Chat History Table (`e-com67-chat-history`)

| Attribute | Type | Description |
|-----------|------|-------------|
| userId | String (PK) | Cognito user sub |
| timestamp | Number (SK) | Unix timestamp |
| messageId | String | Message UUID |
| role | String | "user", "assistant", or "system" |
| content | String | Message content |
| sessionId | String | Session UUID |
| messageType | String | Message type (message, summary, etc.) |
| metadata | Map | Additional message data |

**Features:**
- Conversation history with session grouping
- Message type classification for different content
- Metadata support for structured responses
- Automatic cleanup of old conversations

### Admin Insights Connections Table (`e-com67-admin-insights-connections`)

| Attribute | Type | Description |
|-----------|------|-------------|
| connectionId | String (PK) | WebSocket connection ID |
| sessionId | String | Agent session ID |
| actorId | String | Admin user ID (GSI) |
| connectedAt | Number | Connection timestamp |
| ttl | Number | Time-to-live for auto cleanup (24 hours) |

**GSI:** `actorId-index` (actorId)

**Features:**
- WebSocket connection tracking for Admin Insights Agent
- Session-based memory management
- TTL-based automatic cleanup of stale connections
- Actor-based querying for admin operations

---

## Authentication

E-Com67 uses Amazon Cognito for authentication.

### User Pool Configuration

- **Sign-in:** Email-based
- **Password Policy:** 8+ chars, uppercase, lowercase, digit, symbol
- **Verification:** Email code verification
- **Token Validity:**
  - Access/ID: 1 hour
  - Refresh: 30 days

### User Groups

- **admin:** Administrative privileges for product and order management

### Frontend Integration

```javascript
import { Amplify } from 'aws-amplify'
import { fetchAuthSession } from 'aws-amplify/auth'

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: '<user-pool-id>',
      userPoolClientId: '<client-id>',
      loginWith: {
        email: true
      }
    }
  }
})

// Get auth token for API calls
const getAuthToken = async () => {
  const session = await fetchAuthSession()
  return session.tokens?.idToken?.toString()
}
```

---

## Payment Processing

E-Com67 uses Stripe for payment processing.

### Flow

1. Frontend creates PaymentMethod using Stripe.js
2. Backend creates PaymentIntent via Lambda
3. Step Functions orchestrates the checkout workflow
4. Order processor creates order and clears cart

### Test Cards

| Card Number | Scenario |
|-------------|----------|
| 4242 4242 4242 4242 | Success |
| 4000 0025 0000 3155 | 3D Secure required |
| 4000 0000 0000 9995 | Declined |

### Frontend Integration

```javascript
import { loadStripe } from '@stripe/stripe-js'
import { Elements, CardElement, useStripe } from '@stripe/react-stripe-js'

const stripePromise = loadStripe(process.env.VITE_STRIPE_PUBLISHABLE_KEY)

function CheckoutForm() {
  const stripe = useStripe()

  const handleSubmit = async () => {
    const { paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card: elements.getElement(CardElement)
    })

    // Send paymentMethod.id to backend
    await orderApi.placeOrder({
      paymentMethodId: paymentMethod.id,
      shippingAddress: { ... }
    })
  }
}
```

See [docs/stripe-frontend-integration.md](docs/stripe-frontend-integration.md) for complete integration guide.

---

## AI Chat Feature

The AI chat feature provides intelligent customer support using the **Strands AI Agent SDK** with Amazon Bedrock integration, offering sophisticated conversational AI with direct platform integration.

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Chat    │    │   WebSocket     │    │  Strands Agent  │
│   Widget        │◄──►│   Lambda        │◄──►│   (Enhanced)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
                ┌──────▼──────┐              ┌──────────▼──────────┐              ┌──────▼──────┐
                │  Product    │              │   Cart Management   │              │   Order     │
                │ Search Tool │              │       Tool          │              │ Query Tool  │
                └──────┬──────┘              └──────────┬──────────┘              └──────┬──────┘
                       │                                │                                 │
                ┌──────▼──────┐              ┌──────────▼──────────┐              ┌──────▼──────┐
                │ OpenSearch  │              │     DynamoDB        │              │  DynamoDB   │
                │ (Products)  │              │     (Cart)          │              │  (Orders)   │
                └─────────────┘              └─────────────────────┘              └─────────────┘
```

### Key Features

#### 1. Strands AI Agent Integration
- **Enhanced Conversational AI**: Powered by Strands SDK for sophisticated natural language understanding
- **Custom Tool Integration**: Direct integration with E-Com67 platform APIs
- **Context Management**: Maintains conversation history and user context across sessions
- **Structured Responses**: Type-safe responses using Pydantic models

#### 2. Custom Tools System

**Product Search Tool:**
- OpenSearch integration with fuzzy matching
- Category and price filtering
- Intelligent product recommendations with reasoning
- Search suggestions for no-results scenarios

**Cart Management Tool:**
- Real-time cart operations (add, update, remove, clear)
- Stock validation and availability checking
- Current pricing updates and tax calculation
- Cart state consistency validation

**Order Query Tool:**
- Order history retrieval with pagination
- Comprehensive order tracking and status
- User-specific access control
- Date-based filtering and search

**Knowledge Base Tool:**
- RAG-powered information retrieval
- Platform-specific help and documentation
- Fallback static knowledge base for reliability
- Multi-source information synthesis

#### 3. Real-Time WebSocket Communication
- Instant message delivery and typing indicators
- Connection management with automatic reconnection
- Session persistence and context restoration
- Structured message formatting

### Models Used

- **amazon.titan-text-express-v1:** Main conversational AI model
- **amazon.titan-embed-text-v1:** Document embeddings for RAG
- **Strands Agent SDK:** Enhanced agent capabilities and tool integration

### Configuration

The chat system automatically configures based on deployment stage:

| Stage | Memory Limit | Tool Timeout | Debug Mode |
|-------|-------------|--------------|------------|
| Development | 10 messages | 15 seconds | Enabled |
| Staging | 15 messages | 20 seconds | Enabled |
| Production | 20 messages | 25 seconds | Disabled |

### Frontend Integration

The React ChatWidget provides a polished user experience:

```jsx
import ChatWidget from './components/ChatWidget'

function App() {
  return (
    <div>
      {/* Your app content */}
      <ChatWidget />
    </div>
  )
}
```

**Features:**
- Minimizable chat window
- Message history persistence
- Product recommendation display
- Typing indicators and connection status
- Mobile-responsive design

### Knowledge Base (RAG)

Documents stored in S3 are processed into embeddings and stored in OpenSearch for retrieval-augmented generation.

**Supported File Types:**
- `.txt`, `.md`, `.rst`
- `.json`, `.csv`
- `.html`, `.xml`
- `.yaml`

### Managing Knowledge Base

```bash
# Upload sample documents
python scripts/manage_knowledge_base.py upload-samples

# Upload individual document
python scripts/manage_knowledge_base.py upload path/to/document.txt

# List documents
python scripts/manage_knowledge_base.py list

# Test knowledge base integration
python lambda/chat/test_knowledge_base_enhanced.py
```

### Chat API Usage

**WebSocket Connection:**
```javascript
const wsUrl = `wss://${websocketId}.execute-api.${region}.amazonaws.com/prod`
const ws = new WebSocket(wsUrl)

// Send message
ws.send(JSON.stringify({
  action: 'sendMessage',
  message: 'Help me find a gaming laptop under $1000',
  sessionId: 'session-123'
}))
```

**Structured Response Example:**
```json
{
  "type": "message",
  "message": "I found 5 gaming laptops under $1000 for you!",
  "data": {
    "response_type": "product_list",
    "products": [...],
    "suggestions": ["Would you like to see more details?"],
    "action_buttons": [
      {"text": "View Details", "action": "view_product"},
      {"text": "Add to Cart", "action": "add_to_cart"}
    ]
  },
  "timestamp": 1703425200000,
  "sessionId": "session-123"
}
```

### Testing

```bash
# Test Strands agent setup
python lambda/chat/test_strands_setup.py

# Test tool integration
python lambda/chat/test_tools_integration.py

# Run comprehensive integration tests
python -m pytest tests/test_strands_integration_comprehensive.py -v
```

See [docs/knowledge-base-guide.md](docs/knowledge-base-guide.md) for complete guide.

---

## Search Functionality

Product search is powered by OpenSearch.

### Features

- Full-text search across name and description
- Fuzzy matching for typo tolerance
- Category and price range filtering
- Result highlighting
- Faceted aggregations

### Search Query Example

```
GET /search?q=laptop&category=Electronics&minPrice=500&maxPrice=2000&limit=10
```

### Index Synchronization

The `search_sync` Lambda is triggered by DynamoDB Streams to keep the search index up-to-date with product changes.

---

## Notification System

Multi-channel notifications for order updates and admin alerts.

### Components

- **SNS Topics:**
  - `e-com67-order-notifications` - Customer notifications
  - `e-com67-admin-notifications` - Admin alerts

- **Lambda Functions:**
  - `notification_orchestrator` - Routes to appropriate channels
  - `email_notification` - Sends emails via SES

### Notification Types

- Order confirmation
- Shipping updates
- Delivery notifications
- Admin alerts (low stock, high-value orders)

See [docs/notification-system-integration.md](docs/notification-system-integration.md) for details.

---

## Meta Pixel Integration

The customer app includes Meta Pixel tracking for ad optimization, audience building, and conversion tracking.

### Setup

1. **Install dependency:**
```bash
cd frontends/customer-app
npm install react-facebook-pixel
```

2. **Configure environment:**
```bash
# .env.local
VITE_META_PIXEL_ID=your_pixel_id_here
```

3. **For production, store in AWS SSM:**
```bash
aws ssm put-parameter \
  --name "/e-com67/meta-pixel-id" \
  --value "YOUR_PRODUCTION_PIXEL_ID" \
  --type "String" \
  --region ap-southeast-1
```

### Tracked Events

| Event | Description |
|-------|-------------|
| `PageView` | Automatic on route changes |
| `ViewContent` | Product detail page views |
| `Search` | Product search queries |
| `AddToCart` | Items added to cart |
| `InitiateCheckout` | Checkout page loads |
| `Purchase` | Completed orders |

### Validation

- Use **Meta Pixel Helper** Chrome extension for testing
- Monitor events in **Meta Business Suite > Events Manager**
- Check browser console for debug logs

See [META_PIXEL_IMPLEMENTATION.md](META_PIXEL_IMPLEMENTATION.md) for complete implementation checklist.

---

## System Testing

### Backend Tests

```bash
# Install test dependencies
pip install pytest hypothesis moto

# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_chat*.py -v          # Chat functionality
python -m pytest tests/test_strands*.py -v      # Strands integration
python -m pytest tests/test_product*.py -v      # Product operations

# Run integration tests
python -m pytest tests/test_strands_integration_comprehensive.py -v

# Run with coverage
python -m pytest tests/ --cov=lambda

# Run property-based tests
python -m pytest tests/test_chat_properties.py -v
```

**Test Categories:**
- **Unit Tests**: Individual function and component testing
- **Integration Tests**: End-to-end workflow testing
- **Property-Based Tests**: Hypothesis-driven testing for edge cases
- **Strands Agent Tests**: AI agent functionality and tool integration

### Frontend Tests

```bash
cd frontends/customer-app

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

### Distributed Load Testing on AWS

DLT console: https://d359mw8nc2z8h2.cloudfront.net/ 

DLT MCP Server Endpoint: https://dlt-mcp-server-hf3pwfbt6m.gateway.bedrock-agentcore.ap-southeast-1.amazonaws.com/mcp

---

## Monitoring and Observability

### CloudWatch Logs

All Lambda functions log to CloudWatch with structured JSON format.

**Log Groups:**
- `/aws/lambda/e-com67-*` - Lambda function logs
- `/aws/apigateway/e-com67-api` - API Gateway access logs
- `/aws/stepfunctions/e-com67-checkout-workflow` - Step Functions execution logs

### X-Ray Tracing

Distributed tracing is enabled on all Lambda functions and API Gateway.

### Custom Metrics

Metrics are published to the `E-Com67` namespace:
- Request counts and latencies
- Error rates
- Business metrics (orders, cart operations)

### Viewing Traces

```bash
# View recent traces
aws xray get-service-graph --start-time $(date -v-1H +%s) --end-time $(date +%s)
```

---

## Technical Notes

### OpenTelemetry Lambda Layer Compatibility

When using multiple Lambda layers that include OpenTelemetry dependencies (e.g., Strands SDK layer with AWS Lambda Powertools), context initialization conflicts can occur. This project includes a fix in `layers/strands/python/otel_fix.py`.

**Environment Variables:**
```bash
OTEL_SDK_DISABLED=true
OTEL_PYTHON_CONTEXT=contextvars_context
OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=all
```

**How it works:**
- The fix disables OpenTelemetry SDK to prevent conflicts
- Provides a minimal context implementation using Python's `contextvars`
- Implements import hooks to patch OpenTelemetry modules safely
- Must be imported BEFORE any OpenTelemetry imports in Lambda handlers

**Usage in Lambda:**
```python
# Import at the very top of your handler file
import otel_fix  # Must be first import

# Then import other dependencies
from aws_lambda_powertools import Logger
```

---

## Utility Scripts

| Script | Description |
|--------|-------------|
| `scripts/manage_knowledge_base.py` | Upload documents, list items, and manage the RAG knowledge base |
| `scripts/create_admin_insights_memory.py` | Create Bedrock AgentCore memory for Admin Insights Agent |
| `scripts/build_strands_layer.sh` | Build Strands SDK Lambda layer with Docker (x86_64) |
| `scripts/rebuild_strands_layer.sh` | Rebuild and redeploy Strands layer |
| `scripts/setup-stripe-secret.sh` | Configure Stripe API key in Secrets Manager |
| `scripts/setup-ssm-parameters.sh` | Configure SSM parameters for the application |
| `scripts/debug_opensearch.py` | Debug OpenSearch connectivity and queries |
| `scripts/recreate_index.py` | Recreate OpenSearch index with proper mappings |
| `scripts/test_websocket_message.py` | Test WebSocket API connections |

**Example Usage:**
```bash
# Create Admin Insights memory (required before deploying AdminInsightsStack)
python scripts/create_admin_insights_memory.py

# Rebuild Strands layer after dependency changes
./scripts/build_strands_layer.sh

# Upload knowledge base documents
python scripts/manage_knowledge_base.py upload-samples
```

---

## Cost Optimization

E-Com67 is designed for cost efficiency:

| Resource | Optimization | Estimated Cost (Dev) |
|----------|-------------|---------------------|
| DynamoDB | On-demand billing, no idle costs | ~$5-10/month |
| Lambda | Pay per invocation only | <$1/month |
| OpenSearch | t3.small.search (~$25/month vs $350+/month serverless) | ~$25/month |
| Cognito | Free tier for authentication (first 50k MAUs) | Free |
| API Gateway | Pay per request | <$1/month |
| S3 | Versioning enabled, minimal storage | <$1/month |
| CloudFront | 2 distributions, Price Class 100 (US/EU/CA only) | ~$1-5/month |
| CodePipeline | 3 pipelines (optional CI/CD) | $3/month |
| CodeBuild | Build minutes (optional CI/CD) | ~$1/month |
| Secrets Manager | 1 secret (Stripe key) | ~$0.40/month |
| SES | Email sending (low volume) | <$1/month |

### Estimated Monthly Costs

**Base Infrastructure (without CI/CD):**
- DynamoDB: ~$5-10
- OpenSearch: ~$25
- Lambda + API Gateway: <$2
- CloudFront (2 distributions): ~$1-5
- S3 + SES + Secrets + Other: ~$3-5

**Subtotal:** ~$35-50/month

**With CI/CD Pipelines:**
- Add CodePipeline: +$3/month
- Add CodeBuild: +$1/month

**Total (with CI/CD):** ~$40-55/month for development

**Production Considerations:**
- DynamoDB: Switch to provisioned capacity with auto-scaling for predictable traffic
- OpenSearch: Consider serverless for true auto-scaling (trade-off: higher base cost)
- CloudFront: Upgrade to Price Class All for global reach
- Lambda: Consider Provisioned Concurrency for critical functions
- Implement CloudWatch cost anomaly detection

---

## Troubleshooting

### Common Issues

#### CORS Errors

Ensure CORS headers are included in all Lambda responses:

```python
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}
```

#### Authentication Failures

1. Verify Cognito User Pool ID and Client ID
2. Check token expiration
3. Ensure user is verified

#### Payment Failures

1. Verify Stripe secret key in Secrets Manager
2. Check Stripe dashboard for declined payments
3. Verify webhook endpoint configuration

#### Chat Issues

**Agent Not Responding:**
1. Check Strands SDK installation in layer
2. Verify Bedrock model access permissions
3. Check conversation history table access
4. Verify tool integration with platform APIs

**Tool Execution Failures:**
1. Check DynamoDB table permissions
2. Verify OpenSearch domain access
3. Check user authentication and authorization
4. Review tool-specific error logs

**WebSocket Connection Issues:**
1. Verify WebSocket API Gateway configuration
2. Check connection authentication
3. Review connection timeout settings
4. Check for proper CORS configuration

**Conversation Context Issues:**
1. Check session ID generation and persistence
2. Verify conversation history storage
3. Review memory limit configuration
4. Check conversation summary generation

#### Admin Insights Agent Issues

**Agent Not Responding:**
1. Verify Bedrock AgentCore memory was created (`scripts/create_admin_insights_memory.py`)
2. Check Amazon Nova model access permissions in Bedrock
3. Verify `MEMORY_ID` environment variable is set correctly
4. Review guardrail configuration and blocked content logs

**Analytics Tool Failures:**
1. Check DynamoDB table permissions for Orders and Products tables
2. Verify OpenSearch domain access for Product Search tool
3. Review tool Lambda function logs in CloudWatch
4. Check cross-stack export values are correct

**WebSocket Connection Issues:**
1. Verify token is passed in query string (`?token=...`)
2. Check connections table for stale entries
3. Review WebSocket connect handler logs
4. Verify API Gateway WebSocket stage is deployed

**Guardrail Blocking:**
1. Check if input contains PII (email, phone, credit card, etc.)
2. Review blocked content messaging configuration
3. Test with sanitized queries
4. Check guardrail metrics in CloudWatch

### Useful Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name E-Com67-DataStack

# View Lambda logs
aws logs tail /aws/lambda/e-com67-chat --follow

# Test API endpoint
curl https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/prod/products

# Check DynamoDB table
aws dynamodb scan --table-name e-com67-products --max-items 5

# Test WebSocket connection
wscat -c wss://<websocket-id>.execute-api.ap-southeast-1.amazonaws.com/prod

# Test Strands agent configuration
python lambda/chat/test_strands_setup.py

# Run chat integration tests
python -m pytest tests/test_strands_integration_comprehensive.py -v

# Get Admin Insights WebSocket URL
aws cloudformation describe-stacks \
  --stack-name E-Com67-AdminInsightsStack \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketURL'].OutputValue" \
  --output text

# View Admin Insights agent logs
aws logs tail /aws/lambda/e-com67-admin-insights-agent --follow

# Check guardrail status
aws bedrock get-guardrail --guardrail-identifier <guardrail-id>
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the coding standards
4. Run tests
5. Submit a pull request

### Coding Standards

- **Python:** PEP 8, type hints encouraged
- **JavaScript:** ESLint configuration provided
- **CDK:** Follow existing patterns for resource naming

---

## License

This project is proprietary software. All rights reserved.

---

## Support

For issues and questions:
- Check existing documentation in the `docs/` folder
- Review CloudWatch logs for error details
- Open an issue in the repository
