# E-Com67 Platform

A comprehensive serverless e-commerce platform built on AWS demonstrating modern cloud architecture patterns, microservices design, and advanced features including AI-powered customer support, real-time search capabilities, and automated order processing.

## Architecture Overview

The platform follows a dual-frontend architecture with serverless backend:

### Backend (AWS CDK)
- **DataStack**: DynamoDB tables and Cognito User Pool
- **ComputeStack**: Lambda functions and layers
- **ApiStack**: API Gateway configuration (future)
- **InfrastructureStack**: Supporting services (future)

### Frontend Applications
- **Admin Dashboard** (`frontends/admin-dashboard/`): Administrative interface for staff
- **Customer Application** (`frontends/customer-app/`): Customer-facing shopping experience
- **Shared Components** (`frontends/shared/`): Reusable components and utilities

## Project Structure

```
├── app.py                 # CDK application entry point
├── cdk.json              # CDK configuration
├── requirements.txt      # Python dependencies
├── deploy.sh            # Deployment script
├── stacks/              # CDK stack definitions
│   ├── data_stack.py    # Data layer resources
│   └── compute_stack.py # Compute layer resources
├── lambda/              # Lambda function code
│   ├── product_crud/    # Product CRUD operations
│   └── cart/           # Shopping cart operations
├── layers/             # Lambda layers
│   ├── powertools/     # AWS Lambda Powertools
│   ├── utils/         # Common utilities
│   └── stripe/        # Stripe SDK
└── frontends/          # Frontend applications
    ├── admin-dashboard/ # Admin interface (React)
    ├── customer-app/   # Customer shopping app (React)
    ├── shared/        # Shared components library
    └── README.md      # Frontend documentation
```

## Getting Started

### Prerequisites

- Python 3.9+
- AWS CLI configured
- AWS CDK CLI installed
- Virtual environment activated

### Deployment

1. **Install dependencies:**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Deploy the platform:**
   ```bash
   ./deploy.sh
   ```

3. **Or deploy manually:**
   ```bash
   # Synthesize templates
   cdk synth --all
   
   # Deploy in order
   cdk deploy E-Com67-DataStack
   cdk deploy E-Com67-ComputeStack
   ```

## Resources Created

### DynamoDB Tables

- **e-com67-products**: Product catalog with category GSI
- **e-com67-cart**: Shopping cart with composite keys
- **e-com67-orders**: Order history with user-timestamp GSI
- **e-com67-chat-history**: AI chat conversation storage

### Cognito Resources

- **User Pool**: Authentication with email verification
- **User Pool Client**: Application client configuration
- **Admin Group**: Administrative user group

### Lambda Functions

- **ProductCrudFunction**: Product management operations
- **CartFunction**: Shopping cart operations

### Lambda Layers

- **PowertoolsLayer**: AWS Lambda Powertools for observability
- **UtilsLayer**: Common utilities and business logic
- **StripeLayer**: Stripe SDK for payment processing

## Development

The project is designed for learning AWS serverless technologies while building a production-ready e-commerce platform. Each component demonstrates best practices for:

- Infrastructure as Code with AWS CDK
- Serverless architecture patterns
- Event-driven design
- Security and compliance
- Monitoring and observability

## Next Steps

This foundation enables implementation of:

- API Gateway integration
- Payment processing with Stripe
- AI-powered chat with Amazon Bedrock
- Advanced search with OpenSearch
- Multi-channel notifications
- Administrative dashboard
- CI/CD pipeline
- Comprehensive monitoring

## Cost Management

The platform uses serverless and pay-per-use services to minimize costs:

- DynamoDB on-demand billing
- Lambda pay-per-invocation
- Cognito free tier for authentication
- CloudWatch logs and metrics

Monitor costs regularly and set up billing alerts for production deployments.