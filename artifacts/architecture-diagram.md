# E-Com67 Platform Architecture Diagram

## System Architecture Overview

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#fff'}}}%%
flowchart TB
    subgraph "Client Layer"
        WEB[Web Browser<br/>React SPA]
        MOBILE[Mobile App<br/>Future]
        ADMIN[Admin Portal<br/>React SPA]
    end

    subgraph "CDN & Edge"
        CF[CloudFront CDN<br/>Global Distribution]
        S3WEB[S3 Bucket<br/>Static Hosting]
    end

    subgraph "API Layer"
        APIGW[API Gateway<br/>REST API]
        WSAPI[API Gateway<br/>WebSocket API]
        COGNITO[Cognito<br/>User Pool]
    end

    subgraph "Compute Layer - Lambda Functions"
        PRODUCT[Product CRUD<br/>Function]
        CART[Cart Management<br/>Function]
        SEARCH[Search Sync<br/>Function]
        CHAT[AI Chat<br/>Function]
        PAYMENT[Payment<br/>Function]
        ORDER[Order Processor<br/>Function]
    end

    subgraph "Orchestration Layer"
        SFN[Step Functions<br/>Checkout Workflow]
        SQS[SQS Queue<br/>Order Processing]
        SNS[SNS Topics<br/>Notifications]
    end

    subgraph "Data Layer"
        DDB_PRODUCTS[DynamoDB<br/>Products Table]
        DDB_CART[DynamoDB<br/>Cart Table]
        DDB_ORDERS[DynamoDB<br/>Orders Table]
        DDB_CHAT[DynamoDB<br/>Chat History]
        OPENSEARCH[OpenSearch<br/>Product Index]
        STREAMS[DynamoDB Streams]
    end

    subgraph "AI & External Services"
        BEDROCK[Amazon Bedrock<br/>AI Models]
        STRIPE[Stripe API<br/>Payment Gateway]
        S3KB[S3 Bucket<br/>Knowledge Base]
    end

    subgraph "Monitoring & Observability"
        CW[CloudWatch<br/>Logs & Metrics]
        XRAY[X-Ray<br/>Distributed Tracing]
        ALARMS[CloudWatch Alarms<br/>Alerts]
    end

    subgraph "CI/CD Pipeline"
        GH[GitHub<br/>Source Control]
        GHA[GitHub Actions<br/>Build & Deploy]
        CDK[AWS CDK<br/>Infrastructure as Code]
    end

    %% Client to CDN connections
    WEB --> CF
    MOBILE --> CF
    ADMIN --> CF
    CF --> S3WEB
    CF --> APIGW
    CF --> WSAPI

    %% Authentication flow
    WEB -.Auth.-> COGNITO
    APIGW -.Authorize.-> COGNITO
    WSAPI -.Authorize.-> COGNITO

    %% API to Lambda connections
    APIGW --> PRODUCT
    APIGW --> CART
    APIGW --> SFN
    WSAPI --> CHAT

    %% Lambda to Data Layer
    PRODUCT --> DDB_PRODUCTS
    PRODUCT --> OPENSEARCH
    CART --> DDB_CART
    CART --> DDB_PRODUCTS
    CHAT --> DDB_CHAT
    CHAT --> BEDROCK
    CHAT --> S3KB
    ORDER --> DDB_ORDERS
    ORDER --> DDB_PRODUCTS
    PAYMENT --> DDB_ORDERS

    %% Stream processing
    DDB_PRODUCTS --> STREAMS
    STREAMS --> SEARCH

    %% Orchestration flows
    SFN --> CART
    SFN --> PAYMENT
    SFN --> SQS
    SQS --> ORDER
    ORDER --> SNS

    %% External integrations
    PAYMENT --> STRIPE
    SNS -.Email/SMS.-> WEB

    %% Monitoring connections
    PRODUCT -.Logs.-> CW
    CART -.Logs.-> CW
    CHAT -.Logs.-> CW
    ORDER -.Logs.-> CW
    PAYMENT -.Logs.-> CW
    APIGW -.Logs.-> CW
    SFN -.Logs.-> CW

    PRODUCT -.Traces.-> XRAY
    CART -.Traces.-> XRAY
    ORDER -.Traces.-> XRAY

    CW --> ALARMS

    %% CI/CD flow
    GH --> GHA
    GHA --> CDK
    CDK -.Deploy.-> APIGW
    CDK -.Deploy.-> PRODUCT
    CDK -.Deploy.-> DDB_PRODUCTS
    GHA -.Deploy.-> S3WEB

    %% Styling
    classDef client fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef compute fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef integration fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef monitoring fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef cicd fill:#fff9c4,stroke:#f57f17,stroke-width:2px

    class WEB,MOBILE,ADMIN,CF,S3WEB client
    class PRODUCT,CART,SEARCH,CHAT,PAYMENT,ORDER,APIGW,WSAPI,COGNITO compute
    class DDB_PRODUCTS,DDB_CART,DDB_ORDERS,DDB_CHAT,OPENSEARCH,STREAMS data
    class SFN,SQS,SNS,BEDROCK,STRIPE,S3KB integration
    class CW,XRAY,ALARMS monitoring
    class GH,GHA,CDK cicd
```

## Component Details

### Client Layer
- **Web Browser**: React SPA with Amplify authentication
- **Mobile App**: Future mobile application support
- **Admin Portal**: Administrative interface for platform management

### CDN & Edge Layer
- **CloudFront**: Global content delivery network
- **S3 Static Hosting**: Frontend application hosting

### API Layer
- **API Gateway (REST)**: HTTP API endpoints for CRUD operations
- **API Gateway (WebSocket)**: Real-time chat communication
- **Cognito User Pool**: User authentication and authorization

### Compute Layer (Lambda Functions)
- **Product CRUD**: Product catalog management
- **Cart Management**: Shopping cart operations
- **Search Sync**: OpenSearch index synchronization
- **AI Chat**: Bedrock-powered customer support
- **Payment**: Stripe payment processing
- **Order Processor**: Asynchronous order fulfillment

### Orchestration Layer
- **Step Functions**: Checkout workflow orchestration
- **SQS**: Asynchronous order processing queue
- **SNS**: Notification distribution (email/SMS)

### Data Layer
- **DynamoDB Tables**: Products, Cart, Orders, Chat History
- **OpenSearch**: Full-text product search
- **DynamoDB Streams**: Change data capture for sync

### External Services
- **Amazon Bedrock**: AI language models
- **Stripe API**: Payment processing
- **S3 Knowledge Base**: AI training data

### Monitoring & Observability
- **CloudWatch**: Centralized logging and metrics
- **X-Ray**: Distributed request tracing
- **CloudWatch Alarms**: Automated alerting

### CI/CD Pipeline
- **GitHub**: Source code management
- **GitHub Actions**: Build automation and testing
- **AWS CDK**: Infrastructure as code deployment

## Key Data Flows

### 1. User Browse & Search Flow
```
User → CloudFront → API Gateway → Product Lambda → DynamoDB/OpenSearch → Response
```

### 2. Checkout & Payment Flow
```
User → API Gateway → Step Functions → Cart Validation → Payment Processing → SQS → Order Creation → Notifications
```

### 3. AI Chat Flow
```
User → WebSocket API → Chat Lambda → Bedrock (with S3 Knowledge Base) → Response + Chat History Storage
```

### 4. Product Update Flow
```
Admin → API Gateway → Product Lambda → DynamoDB → Streams → Search Sync Lambda → OpenSearch
```

### 5. CI/CD Deployment Flow
```
Git Push → GitHub Actions → Build & Test → CDK Synth → AWS Deployment → CloudFront Invalidation
```

## Architecture Principles

1. **Serverless-First**: All compute uses Lambda for automatic scaling
2. **Event-Driven**: Asynchronous processing via SQS, SNS, and Streams
3. **Managed Services**: Minimize operational overhead with AWS managed services
4. **Security by Design**: Cognito auth, encryption at rest/transit, least privilege IAM
5. **Observability**: Comprehensive logging, metrics, and distributed tracing
6. **Infrastructure as Code**: Complete CDK-based infrastructure management
7. **Global Distribution**: CloudFront CDN for low-latency worldwide access
8. **Resilient Design**: Retry logic, circuit breakers, and graceful degradation

## Scalability Considerations

- **Auto-scaling**: Lambda and DynamoDB scale automatically based on demand
- **Caching**: CloudFront edge caching and OpenSearch query caching
- **Database Design**: GSIs for efficient query patterns, streams for async processing
- **Queue-based Processing**: SQS decouples order processing from checkout flow
- **Search Offloading**: OpenSearch handles complex queries without impacting DynamoDB
