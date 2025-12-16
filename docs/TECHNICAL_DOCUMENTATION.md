# E-Com67 - Technical Documentation

**Version:** 1.0
**Last Updated:** December 2025
**AWS Account:** 724542698940
**Region:** ap-southeast-1 (Singapore)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Backend Infrastructure](#backend-infrastructure)
6. [Lambda Functions](#lambda-functions)
7. [API Reference](#api-reference)
8. [Frontend Application](#frontend-application)
9. [Database Schema](#database-schema)
10. [Authentication & Authorization](#authentication--authorization)
11. [Deployment Guide](#deployment-guide)
12. [Local Development Setup](#local-development-setup)
13. [Monitoring & Logging](#monitoring--logging)
14. [Troubleshooting](#troubleshooting)
15. [Planned Features](#planned-features)

---

## Project Overview

E-Com67 is a fully serverless e-commerce platform built on AWS, demonstrating modern cloud architecture patterns. The application provides a complete online shopping experience including product browsing, cart management, order processing, and payment handling.

### Key Features

**Implemented:**
- User authentication via AWS Cognito
- Product catalog with category filtering
- Shopping cart management (session-based per user)
- Order processing workflow with Step Functions
- Payment processing (ready for Stripe integration)
- Asynchronous order handling via SQS
- Real-time monitoring with CloudWatch and X-Ray
- OpenSearch domain for full-text search capability
- SNS notifications for order confirmations

**Planned:**
- Stripe payment integration
- AI-powered chat support via Amazon Bedrock
- Advanced product search with OpenSearch
- Email notifications via SES
- Admin dashboard for inventory management

---

## Architecture

### High-Level Architecture

The application follows a multi-stack CDK architecture pattern with clear separation of concerns:

**Four Core Stacks:**
1. **DataStack** - Database and identity management (DynamoDB, Cognito)
2. **ComputeStack** - Application logic (Lambda functions, layers)
3. **ApiStack** - API Gateway with Cognito authorization
4. **InfraStack** - Supporting services (OpenSearch, SQS, SNS, Step Functions, S3)

### Core User Flows

#### Authentication Flow
```
User → React App (Amplify Auth) → Cognito User Pool → JWT Token
  ↓
JWT Token stored in browser → Axios interceptor adds to all API requests
  ↓
API Gateway validates token via Cognito Authorizer → Lambda execution
```

#### Product Discovery Flow
```
User browses → API Gateway → ProductCrudFunction → DynamoDB
  ↓
Category filter? → DynamoDB GSI (category-index) → Filtered results
```

#### Shopping Cart Flow
```
User adds item → API Gateway (JWT validated) → CartFunction
  ↓
CartFunction validates product → Updates cart table → Returns cart with total
```

#### Checkout & Order Processing Flow
```
User clicks "Place Order" → API Gateway → Step Function (Checkout Workflow)
  ├─ Step 1: Validate Cart (CartFunction)
  ├─ Step 2: Process Payment (PaymentFunction) [with retry: 3x]
  ├─ Step 3: Send to SQS (Order Queue)
  └─ Failure → Return error to user

SQS Order Queue → OrderProcessorFunction (batch: 10)
  ├─ Create Order in DynamoDB
  ├─ Clear user's cart
  ├─ Update product stock
  └─ Send SNS notification

SNS Topic → Order Confirmation (email/webhook)
```

---

## Technology Stack

### Backend
- **Infrastructure as Code:** AWS CDK (Python 3.11)
- **Runtime:** Python 3.11 (Lambda functions)
- **Database:** Amazon DynamoDB (4 tables)
- **Authentication:** Amazon Cognito User Pools
- **API:** Amazon API Gateway (REST)
- **Compute:** AWS Lambda
- **Orchestration:** AWS Step Functions
- **Messaging:** Amazon SQS, Amazon SNS
- **Search:** Amazon OpenSearch Service 2.9
- **Storage:** Amazon S3
- **Monitoring:** AWS CloudWatch, AWS X-Ray
- **Logging:** AWS Lambda Powertools for Python

### Frontend
- **Framework:** React 18.3
- **Build Tool:** Vite 5
- **Styling:** Tailwind CSS 3.4
- **Routing:** React Router 6
- **AWS Integration:** AWS Amplify 6.6
- **HTTP Client:** Axios 1.7
- **Notifications:** React Hot Toast

---

## Project Structure

```
e-com67/
├── backend/                              # AWS CDK Infrastructure
│   ├── app.py                           # CDK app entry point
│   ├── cdk.json                         # CDK configuration
│   ├── requirements.txt                 # Python dependencies
│   │
│   ├── e_com67/                         # CDK stacks
│   │   ├── __init__.py
│   │   └── stacks/
│   │       ├── data_stack.py           # DynamoDB tables, Cognito
│   │       ├── compute_stack.py        # Lambda functions, layers
│   │       ├── api_stack.py            # API Gateway, authorizer
│   │       └── infra_stack.py          # OpenSearch, SQS, SNS, Step Functions
│   │
│   ├── lambda/                          # Lambda function handlers
│   │   ├── products/
│   │   │   └── index.py                # Product CRUD operations
│   │   ├── cart/
│   │   │   └── index.py                # Cart management
│   │   ├── payment/
│   │   │   └── index.py                # Payment processing
│   │   ├── order_processor/
│   │   │   └── index.py                # SQS order processor
│   │   └── layers/                      # Lambda layers
│   │       └── powertools/             # AWS Lambda Powertools
│   │
│   └── scripts/                         # Utility scripts
│       └── populate_products.py        # Seed product data
│
├── frontend/                            # React application
│   ├── src/
│   │   ├── pages/                      # Page components
│   │   │   ├── Login.jsx              # Authentication
│   │   │   ├── Products.jsx           # Product listing
│   │   │   ├── Cart.jsx               # Shopping cart
│   │   │   ├── Checkout.jsx           # Order checkout
│   │   │   ├── Orders.jsx             # Order history
│   │   │   └── NotFound.jsx           # 404 page
│   │   │
│   │   ├── components/                 # Reusable components
│   │   │   ├── Navbar.jsx             # Navigation bar
│   │   │   ├── ProductCard.jsx        # Product display
│   │   │   ├── SearchBar.jsx          # Search interface
│   │   │   ├── ChatWidget.jsx         # AI chat (planned)
│   │   │   ├── ErrorBoundary.jsx      # Error handling
│   │   │   └── LoadingSpinner.jsx     # Loading state
│   │   │
│   │   ├── services/
│   │   │   ├── api.js                 # API client
│   │   │   └── websocket.js           # WebSocket service (planned)
│   │   │
│   │   ├── config/
│   │   │   └── aws-config.js          # AWS Amplify configuration
│   │   │
│   │   ├── App.jsx                    # Main app component
│   │   └── main.jsx                   # React entry point
│   │
│   ├── package.json                    # Node dependencies
│   ├── vite.config.js                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind CSS config
│   └── .env.local                     # Environment variables (not committed)
│
└── docs/                               # Documentation
    ├── guide.md                       # Implementation guide
    └── TECHNICAL_DOCUMENTATION.md     # This file
```

---

## Backend Infrastructure

### DataStack - Foundation Layer

**File:** `backend/e_com67/stacks/data_stack.py`

#### DynamoDB Tables

| Table Name | Partition Key | Sort Key | GSI | Purpose |
|------------|---------------|----------|-----|---------|
| `e-com67-products` | productId (String) | - | category-index | Product catalog |
| `e-com67-cart` | userId (String) | productId (String) | - | Shopping cart items |
| `e-com67-orders` | orderId (String) | userId (String) | userId-timestamp-index | Order records |
| `e-com67-chat-history` | userId (String) | timestamp (Number) | - | Chat conversations |

**Table Features:**
- Billing Mode: Pay-per-request (on-demand)
- Point-in-Time Recovery: Enabled
- Contributor Insights: Enabled for monitoring
- Removal Policy: DESTROY (for development)

#### Cognito User Pool

**Configuration:**
- Pool Name: `e-com67-user-pool`
- Sign-in: Email only
- Auto-verify: Email addresses
- Password Policy:
  - Minimum length: 8 characters
  - Requires: Uppercase, lowercase, digits
  - No special characters required
- Self-service sign-up: Enabled
- MFA: Optional (not enforced)

**App Client:**
- Name: `e-com67-client`
- Auth Flows: USER_PASSWORD_AUTH, USER_SRP_AUTH, ADMIN_NO_SRP_AUTH

**CloudFormation Exports:**
- `ECom67-UserPoolId`
- `ECom67-UserPoolArn`
- `ECom67-ProductsTableName`
- `ECom67-ProductsTableArn`
- `ECom67-CartTableName`
- `ECom67-CartTableArn`
- `ECom67-OrdersTableName`
- `ECom67-OrdersTableArn`

---

### ComputeStack - Application Logic Layer

**File:** `backend/e_com67/stacks/compute_stack.py`

#### Lambda Layers

**Powertools Layer:**
- Runtime: Python 3.11
- Contents: AWS Lambda Powertools for structured logging, tracing, metrics
- Compatibility: All Lambda functions in the stack
- Purpose: Centralized observability utilities

**Common Utils Layer:**
- Runtime: Python 3.11
- Purpose: Shared utilities and helper functions (optional)

#### Lambda Functions

| Function | Handler | Timeout | Memory | Env Variables | Permissions |
|----------|---------|---------|--------|---------------|-------------|
| ProductCrudFunction | products/index.py | 30s | 512MB | PRODUCTS_TABLE | Read/Write products table |
| CartFunction | cart/index.py | 10s | 128MB | CART_TABLE, PRODUCTS_TABLE | Read/Write cart, Read products |
| PaymentFunction | payment/index.py | 30s | 128MB | ORDERS_TABLE | Read/Write orders |
| OrderProcessorFunction | order_processor/index.py | 60s | 128MB | ORDERS_TABLE, CART_TABLE, PRODUCTS_TABLE, SNS_TOPIC_ARN | Read/Write all tables, Publish to SNS |

**Common Configuration:**
- Runtime: Python 3.11
- X-Ray Tracing: Active
- Powertools Environment Variables:
  - `POWERTOOLS_SERVICE_NAME`: Function-specific name
  - `POWERTOOLS_METRICS_NAMESPACE`: "ECom67"
  - `LOG_LEVEL`: "INFO"

---

### ApiStack - API Gateway Layer

**File:** `backend/e_com67/stacks/api_stack.py`

#### REST API Configuration

- **API Name:** `e-com67-api`
- **Description:** Serverless E-Commerce API
- **CORS Settings:**
  - Allow Origins: `*` (all origins)
  - Allow Methods: `OPTIONS, GET, PUT, POST, DELETE`
  - Allow Headers: `Authorization, Content-Type, X-Amz-Date, X-Api-Key, X-Amz-Security-Token`
- **Tracing:** X-Ray enabled

#### Cognito Authorizer

- **Type:** Cognito User Pools
- **Identity Source:** Authorization header
- **Validation:** JWT token signature and expiration

#### API Endpoints

See [API Reference](#api-reference) section for detailed endpoint documentation.

---

### InfraStack - Supporting Services Layer

**File:** `backend/e_com67/stacks/infra_stack.py`

#### OpenSearch Domain

- **Domain Name:** `e-com67-search`
- **Version:** OpenSearch 2.9
- **Instance Type:** t3.small.search
- **Instance Count:** 1 (single-node for development)
- **Storage:** 10GB GP3 EBS
- **Network:** VPC-based deployment (optional)
- **Purpose:** Full-text product search (integration pending)

#### SQS Queues

**Order Queue:**
- Name: `e-com67-order-queue`
- Visibility Timeout: 90 seconds
- Message Retention: 4 days
- Dead Letter Queue: `e-com67-order-dlq` (max receives: 3)

**Dead Letter Queue:**
- Name: `e-com67-order-dlq`
- Retention Period: 14 days
- Purpose: Failed order processing for manual review

**Lambda Event Source Mapping:**
- Queue: Order Queue
- Function: OrderProcessorFunction
- Batch Size: 10 messages
- Batch Window: Default

#### SNS Topics

**Order Notifications:**
- Name: `e-com67-order-notifications`
- Display Name: "Order Notifications"
- Purpose: Order confirmation notifications
- Subscribers: Email endpoints (configured post-deployment)

#### Step Functions State Machine

**Checkout Workflow:**
- Name: `e-com67-checkout`
- Type: STANDARD
- Timeout: 5 minutes
- X-Ray Tracing: Enabled

**Workflow Steps:**
1. **ValidateCart** - Invokes CartFunction to verify cart contents
2. **ProcessPayment** - Invokes PaymentFunction with retry policy:
   - Max Attempts: 3
   - Interval: 2 seconds
   - Backoff Rate: 2.0
   - Retry on: Service exceptions
3. **SendToQueue** - Sends order to SQS for async processing
4. **Success/Failure** - Terminal states

**State Machine Definition:**
```
ValidateCart → ProcessPayment → SendToQueue → Success
                     ↓ (on error)
                  Failure
```

#### S3 Buckets

**Frontend Bucket:**
- Name: `e-com67-frontend-{account-id}`
- Public Read Access: Enabled
- Website Hosting: Enabled
- Auto-Delete Objects: On stack deletion

**Knowledge Base Bucket:**
- Name: `e-com67-kb-{account-id}`
- Purpose: Store documents for AI chat RAG
- Versioning: Disabled
- Auto-Delete Objects: On stack deletion

#### CloudWatch Alarms

**Payment Function Error Alarm:**
- Metric: Lambda Errors
- Threshold: 5 errors
- Evaluation Periods: 1
- Action: SNS notification (configured post-deployment)

**Order Queue Depth Alarm:**
- Metric: ApproximateNumberOfMessagesVisible
- Threshold: 100 messages
- Evaluation Periods: 1
- Purpose: Detect processing bottlenecks

#### EventBridge Rules

**Daily Inventory Check:**
- Schedule: `cron(0 2 * * ? *)` (2 AM UTC daily)
- Target: Lambda function (placeholder, not implemented)
- Purpose: Automated inventory audits

---

## Lambda Functions

### 1. ProductCrudFunction

**File:** `backend/lambda/products/index.py`

**Purpose:** Manage product catalog operations (Create, Read, Update, Delete)

**Supported Methods:**

| HTTP Method | Path | Description | Authentication |
|-------------|------|-------------|----------------|
| GET | /products | List all products or filter by category | Public |
| GET | /products/{productId} | Get single product details | Public |
| POST | /products | Create new product | Protected |
| PUT | /products/{productId} | Update product fields | Protected |
| DELETE | /products/{productId} | Delete product | Protected |

**Key Features:**
- Category filtering via DynamoDB GSI (`category-index`)
- UUID generation for new products
- Dynamic update expressions for PUT requests
- Decimal type handling for prices
- Powertools Logger and Tracer decorators

**Sample Product Object:**
```json
{
  "productId": "uuid-v4",
  "name": "Product Name",
  "description": "Product description",
  "price": 29.99,
  "category": "Electronics",
  "stock": 100,
  "imageUrl": "https://example.com/image.jpg"
}
```

---

### 2. CartFunction

**File:** `backend/lambda/cart/index.py`

**Purpose:** Manage user shopping cart

**Supported Methods:**

| HTTP Method | Path | Description | Authentication |
|-------------|------|-------------|----------------|
| GET | /cart | Get user's cart items with total | Protected |
| POST | /cart | Add/update item quantity | Protected |
| DELETE | /cart | Remove item from cart | Protected |

**Key Features:**
- User ID extracted from Cognito JWT claims (`event['requestContext']['authorizer']['claims']['sub']`)
- Product validation before adding to cart
- Automatic cart total calculation on GET
- Fetch product details for pricing integrity

**Request Body (POST):**
```json
{
  "productId": "uuid",
  "quantity": 2
}
```

**Response (GET):**
```json
{
  "items": [
    {
      "userId": "cognito-sub",
      "productId": "uuid",
      "name": "Product Name",
      "price": 29.99,
      "quantity": 2,
      "description": "...",
      "imageUrl": "..."
    }
  ],
  "total": 59.98
}
```

---

### 3. PaymentFunction

**File:** `backend/lambda/payment/index.py`

**Purpose:** Process payment transactions

**Status:** Stub implementation (ready for Stripe integration)

**Request Body:**
```json
{
  "orderId": "uuid",
  "userId": "cognito-sub",
  "amount": 59.98,
  "paymentToken": "stripe-token"
}
```

**Response:**
```json
{
  "orderId": "uuid",
  "status": "PAID",
  "message": "Payment processed successfully"
}
```

**TODO:**
- Integrate Stripe SDK
- Add Stripe secret key from Secrets Manager
- Implement payment intent creation
- Handle 3D Secure authentication
- Add payment failure handling

---

### 4. OrderProcessorFunction

**File:** `backend/lambda/order_processor/index.py`

**Purpose:** Asynchronous order processing triggered by SQS

**Trigger:** SQS Queue (`e-com67-order-queue`)

**Processing Steps:**
1. Parse order message from SQS batch
2. Create order record in DynamoDB with status "PROCESSING"
3. Clear all cart items for the user
4. Update product stock (decrement by quantity ordered)
5. Publish order confirmation to SNS topic

**Order Object Structure:**
```json
{
  "orderId": "uuid",
  "userId": "cognito-sub",
  "items": [
    {
      "productId": "uuid",
      "name": "Product",
      "price": 29.99,
      "quantity": 2
    }
  ],
  "totalAmount": 59.98,
  "status": "PROCESSING",
  "paymentId": "payment-id",
  "timestamp": 1702555200
}
```

**Error Handling:**
- Exceptions logged with order context
- Failed messages sent to DLQ after 3 attempts
- Retries with exponential backoff via SQS

---

## API Reference

### Base URL
```
https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod
```

### Authentication
Protected endpoints require JWT token in Authorization header:
```
Authorization: Bearer {jwt-token}
```

### API Endpoints Quick Reference

#### Products

| Method | Endpoint | Auth | Description | Query Params |
|--------|----------|------|-------------|--------------|
| GET | `/products` | Public | List products | `?category=Electronics` |
| GET | `/products/{productId}` | Public | Get product by ID | - |
| POST | `/products` | Protected | Create product | - |
| PUT | `/products/{productId}` | Protected | Update product | - |
| DELETE | `/products/{productId}` | Protected | Delete product | - |

**POST /products Request:**
```json
{
  "name": "Laptop",
  "description": "High-performance laptop",
  "price": 999.99,
  "category": "Electronics",
  "stock": 50,
  "imageUrl": "https://example.com/laptop.jpg"
}
```

**GET /products Response:**
```json
[
  {
    "productId": "uuid-1",
    "name": "Laptop",
    "price": 999.99,
    "category": "Electronics",
    "stock": 50,
    ...
  }
]
```

#### Cart

| Method | Endpoint | Auth | Description | Query Params |
|--------|----------|------|-------------|--------------|
| GET | `/cart` | Protected | Get user's cart | - |
| POST | `/cart` | Protected | Add/update item | - |
| DELETE | `/cart` | Protected | Remove item | `?productId={id}` |

**POST /cart Request:**
```json
{
  "productId": "uuid",
  "quantity": 2
}
```

**GET /cart Response:**
```json
{
  "items": [...],
  "total": 59.98
}
```

**DELETE /cart:**
```
DELETE /cart?productId=uuid-123
```

#### Orders

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/orders` | Protected | Place order (triggers Step Function) |
| GET | `/orders` | Protected | Get user's order history |
| GET | `/orders/{orderId}` | Protected | Get order details |

**POST /orders Request:**
```json
{
  "paymentToken": "stripe-token-or-mock"
}
```

**Response:**
```json
{
  "orderId": "uuid",
  "status": "PROCESSING",
  "message": "Order placed successfully"
}
```

### Error Responses

**401 Unauthorized:**
```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid authentication token"
}
```

**404 Not Found:**
```json
{
  "error": "Product not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

---

## Frontend Application

### Technology Overview

**React 18.3 + Vite 5**
- Modern build tooling with hot module replacement
- Fast development server with instant feedback
- Optimized production builds

**AWS Amplify 6.6**
- Native Cognito authentication integration
- JWT token management
- Auth state management with Hub events

**Tailwind CSS 3.4**
- Utility-first styling
- Responsive design system
- Custom theme configuration

### Application Structure

#### Pages

**Login Page** (`src/pages/Login.jsx`)
- User signup with email verification
- Email/password authentication
- Form validation with error display
- Automatic redirect after successful login
- Toggle between signup and signin modes

**Products Page** (`src/pages/Products.jsx`)
- Product grid layout (responsive: 1/3/4 columns)
- Category filtering (Electronics, Clothing, Books, Home)
- Search functionality with SearchBar component
- Add to cart functionality via ProductCard
- Loading states and error handling

**Cart Page** (`src/pages/Cart.jsx`)
- Display cart items with product details
- Update quantity with inline controls
- Remove items from cart
- Real-time total calculation
- Proceed to checkout button
- Empty cart state with CTA

**Checkout Page** (`src/pages/Checkout.jsx`)
- Order summary with item breakdown
- Mock Stripe payment form
- Order placement via Step Function
- Success/error notifications
- Redirect to orders page on success

**Orders Page** (`src/pages/Orders.jsx`)
- Order history list for authenticated user
- Order details (items, total, status, date)
- Chronological sorting (newest first)
- Loading and empty states

**NotFound Page** (`src/pages/NotFound.jsx`)
- 404 error page
- Navigation back to products

#### Components

**Navbar** (`src/components/Navbar.jsx`)
- Navigation links (Products, Cart, Orders)
- User email display
- Logout functionality
- Responsive design

**ProductCard** (`src/components/ProductCard.jsx`)
- Product image, name, price, category
- Stock availability indicator
- Add to cart button with loading state
- Toast notifications on success/error

**SearchBar** (`src/components/SearchBar.jsx`)
- Text input for product search
- Debounced search (500ms delay)
- Clear search functionality

**ChatWidget** (`src/components/ChatWidget.jsx`)
- Placeholder for AI chat interface
- Floating widget design
- Expandable/collapsible panel (planned)

**ErrorBoundary** (`src/components/ErrorBoundary.jsx`)
- Global error catching
- Fallback UI for React errors
- Error logging

**LoadingSpinner** (`src/components/LoadingSpinner.jsx`)
- Reusable loading indicator
- Centered spinner animation

### Services

#### API Service (`src/services/api.js`)

**Axios Instance Configuration:**
- Base URL from environment variable
- Request interceptor: Adds JWT token to Authorization header
- Response interceptor: Handles 401 errors (triggers logout)
- Timeout: 30 seconds

**Products API:**
```javascript
productsAPI.getAll(category)       // GET /products?category=...
productsAPI.getById(id)            // GET /products/{id}
productsAPI.create(data)           // POST /products
productsAPI.update(id, data)       // PUT /products/{id}
productsAPI.delete(id)             // DELETE /products/{id}
productsAPI.search(query)          // GET /search?q=...
```

**Cart API:**
```javascript
cartAPI.get()                      // GET /cart
cartAPI.add(productId, quantity)   // POST /cart
cartAPI.update(productId, quantity)// POST /cart
cartAPI.remove(productId)          // DELETE /cart?productId=...
cartAPI.clear()                    // DELETE /cart (all items)
```

**Orders API:**
```javascript
ordersAPI.getAll()                 // GET /orders
ordersAPI.getById(id)              // GET /orders/{id}
ordersAPI.create(orderData)        // POST /orders
```

**Payment API (Mock):**
```javascript
paymentAPI.createPaymentIntent(amount)    // Simulated delay
paymentAPI.confirmPayment(paymentIntentId) // Returns mock token
```

#### WebSocket Service (`src/services/websocket.js`)

**Status:** Placeholder for future Bedrock chat integration

**Planned Features:**
- WebSocket connection to API Gateway WebSocket endpoint
- Real-time message streaming
- Connection state management
- Reconnection logic

### AWS Configuration

**File:** `src/config/aws-config.js`

```javascript
import { Amplify } from 'aws-amplify';

const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_APP_CLIENT_ID,
      region: import.meta.env.VITE_AWS_REGION,
    }
  }
};

Amplify.configure(awsConfig);
```

### Environment Variables

**File:** `.env.local` (not committed to Git)

```env
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_xxxxxxxxx
VITE_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_AWS_REGION=ap-southeast-1
VITE_API_GATEWAY_ENDPOINT=https://xxxxxxxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
```

**Access in code:**
```javascript
const apiEndpoint = import.meta.env.VITE_API_GATEWAY_ENDPOINT;
```

### Routing

**File:** `src/App.jsx`

Protected routes require authentication. Unauthenticated users are redirected to `/login`.

```
/                    → Redirect to /products (if authenticated) or /login
/login               → Login/Signup page
/products            → Product listing (protected)
/cart                → Shopping cart (protected)
/checkout            → Order checkout (protected)
/orders              → Order history (protected)
/*                   → 404 Not Found
```

**Route Protection Logic:**
```javascript
useEffect(() => {
  checkUser(); // Verify current authenticated user on mount
}, []);

// If not authenticated, redirect to /login
// If authenticated, allow access to protected routes
```

---

## Database Schema

### DynamoDB Tables

#### products Table

```
Partition Key: productId (String)

Attributes:
- productId: String (UUID)
- name: String
- description: String
- price: Number (Decimal)
- category: String
- stock: Number (Integer)
- imageUrl: String
- createdAt: Number (Unix timestamp)
- updatedAt: Number (Unix timestamp)

Global Secondary Indexes:
- category-index
  - Partition Key: category (String)
  - Projection: ALL
  - Purpose: Filter products by category
```

**Example Item:**
```json
{
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Wireless Headphones",
  "description": "Noise-cancelling Bluetooth headphones",
  "price": 149.99,
  "category": "Electronics",
  "stock": 25,
  "imageUrl": "https://example.com/headphones.jpg",
  "createdAt": 1702555200,
  "updatedAt": 1702555200
}
```

---

#### cart Table

```
Partition Key: userId (String)
Sort Key: productId (String)

Attributes:
- userId: String (Cognito sub)
- productId: String (UUID)
- name: String (denormalized from products)
- price: Number (denormalized from products)
- quantity: Number (Integer)
- description: String (denormalized)
- imageUrl: String (denormalized)
- addedAt: Number (Unix timestamp)
```

**Example Item:**
```json
{
  "userId": "cognito-uuid-sub-123",
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Wireless Headphones",
  "price": 149.99,
  "quantity": 2,
  "description": "Noise-cancelling Bluetooth headphones",
  "imageUrl": "https://example.com/headphones.jpg",
  "addedAt": 1702555200
}
```

**Query Pattern:**
- Get user's cart: `Query(userId = "cognito-sub")`
- Remove item: `DeleteItem(userId = "cognito-sub", productId = "uuid")`

---

#### orders Table

```
Partition Key: orderId (String)
Sort Key: userId (String)

Attributes:
- orderId: String (UUID)
- userId: String (Cognito sub)
- items: List (Array of order items)
- totalAmount: Number (Decimal)
- status: String (PROCESSING | COMPLETED | FAILED)
- paymentId: String
- timestamp: Number (Unix timestamp)
- createdAt: Number (Unix timestamp)

Global Secondary Indexes:
- userId-timestamp-index
  - Partition Key: userId (String)
  - Sort Key: timestamp (Number)
  - Projection: ALL
  - Purpose: Query user's orders sorted by date
```

**Example Item:**
```json
{
  "orderId": "order-uuid-123",
  "userId": "cognito-uuid-sub-123",
  "items": [
    {
      "productId": "product-uuid-1",
      "name": "Wireless Headphones",
      "price": 149.99,
      "quantity": 2
    }
  ],
  "totalAmount": 299.98,
  "status": "PROCESSING",
  "paymentId": "payment-intent-123",
  "timestamp": 1702555200,
  "createdAt": 1702555200
}
```

**Query Pattern:**
- Get order by ID: `GetItem(orderId = "uuid", userId = "sub")`
- Get user's orders: `Query(userId-timestamp-index, userId = "sub", SortOrder = DESC)`

---

#### chat-history Table

```
Partition Key: userId (String)
Sort Key: timestamp (Number)

Attributes:
- userId: String (Cognito sub)
- timestamp: Number (Unix timestamp)
- messageId: String (UUID)
- role: String (user | assistant)
- content: String
- sessionId: String (optional)
```

**Example Item:**
```json
{
  "userId": "cognito-uuid-sub-123",
  "timestamp": 1702555200,
  "messageId": "msg-uuid-123",
  "role": "user",
  "content": "What headphones do you recommend?",
  "sessionId": "session-uuid-456"
}
```

**Query Pattern:**
- Get chat history: `Query(userId = "sub", timestamp > startTime, SortOrder = ASC)`

---

## Authentication & Authorization

### Cognito User Pool

**Pool Configuration:**
- Sign-in Attribute: Email
- Auto-verified Attributes: Email
- Password Policy: 8+ chars, uppercase, lowercase, digits
- MFA: Optional (not enforced)

### User Lifecycle

1. **Sign Up:**
   - User submits email + password via frontend
   - Cognito sends verification code to email
   - User confirms email to activate account

2. **Sign In:**
   - User submits email + password
   - Cognito validates credentials
   - Returns JWT tokens (ID token, Access token, Refresh token)
   - Frontend stores tokens in memory (Amplify handles this)

3. **Authenticated Requests:**
   - Frontend adds `Authorization: Bearer {idToken}` to API requests
   - API Gateway validates token signature via Cognito Authorizer
   - Lambda receives user claims in `event.requestContext.authorizer.claims`

4. **Token Refresh:**
   - Amplify automatically refreshes tokens using refresh token
   - Tokens expire after 1 hour (default)

5. **Sign Out:**
   - User clicks logout
   - Frontend calls `Auth.signOut()`
   - Tokens cleared from memory
   - Redirected to login page

### JWT Token Structure

**ID Token Claims (example):**
```json
{
  "sub": "cognito-uuid-user-id",
  "email": "user@example.com",
  "email_verified": true,
  "cognito:username": "user@example.com",
  "aud": "app-client-id",
  "token_use": "id",
  "auth_time": 1702555200,
  "iss": "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_xxxxx",
  "exp": 1702558800,
  "iat": 1702555200
}
```

### Extracting User ID in Lambda

```python
def handler(event, context):
    # Get user ID from Cognito authorizer claims
    user_id = event['requestContext']['authorizer']['claims']['sub']

    # Use user_id for database operations
    response = cart_table.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )
```

### API Gateway Authorization

**Public Endpoints:**
- GET /products
- GET /products/{id}

**Protected Endpoints (require JWT):**
- POST /products
- PUT /products/{id}
- DELETE /products/{id}
- GET /cart
- POST /cart
- DELETE /cart
- POST /orders
- GET /orders
- GET /orders/{id}

**Authorizer Configuration:**
```python
authorizer = apigw.CognitoUserPoolsAuthorizer(
    self, "ECom67Authorizer",
    cognito_user_pools=[user_pool]
)

# Apply to protected endpoint
cart.add_method(
    "GET",
    apigw.LambdaIntegration(cart_fn),
    authorizer=authorizer,
    authorization_type=apigw.AuthorizationType.COGNITO
)
```

---

## Deployment Guide

### Prerequisites

**AWS CLI:**
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Configure credentials
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (ap-southeast-1)
```

**Python 3.11:**
```bash
# macOS
brew install python@3.11

# Verify
python3 --version  # Should be 3.11.x
```

**Node.js 18+:**
```bash
# macOS
brew install node@18

# Verify
node --version  # Should be 18.x or higher
npm --version
```

**AWS CDK:**
```bash
npm install -g aws-cdk

# Verify
cdk --version  # Should be 2.120.0 or higher
```

---

### Backend Deployment (AWS CDK)

#### Step 1: Setup Python Environment

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Bootstrap CDK (First-time only)

```bash
# Set environment variables
export AWS_ACCOUNT_ID=724542698940
export AWS_REGION=ap-southeast-1

# Bootstrap CDK in your account/region
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
```

This creates the CDK toolkit stack with S3 bucket for assets and necessary IAM roles.

#### Step 3: Synthesize CloudFormation Templates

```bash
# Generate CloudFormation templates
cdk synth

# Review templates in cdk.out/ directory
ls cdk.out/
```

**Output:**
```
ECom67DataStack.template.json
ECom67ComputeStack.template.json
ECom67ApiStack.template.json
ECom67InfraStack.template.json
manifest.json
tree.json
```

#### Step 4: Deploy Stacks

**Option A: Deploy all stacks**
```bash
cdk deploy --all --require-approval never
```

**Option B: Deploy specific stack**
```bash
# Deploy in dependency order
cdk deploy ECom67DataStack
cdk deploy ECom67ComputeStack
cdk deploy ECom67ApiStack
cdk deploy ECom67InfraStack
```

**Deployment Time:** ~8-12 minutes (depends on OpenSearch domain provisioning)

#### Step 5: Capture Stack Outputs

```bash
# Get all stack outputs
aws cloudformation describe-stacks \
  --region ap-southeast-1 \
  --query 'Stacks[].Outputs' \
  --output json > outputs.json

# Or get specific output
aws cloudformation describe-stacks \
  --stack-name ECom67ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

**Important Outputs:**
- `ApiEndpoint` - API Gateway URL
- `UserPoolId` - Cognito User Pool ID
- `UserPoolClientId` - Cognito App Client ID
- `FrontendBucketName` - S3 bucket for frontend

---

### Frontend Deployment

#### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

#### Step 2: Configure Environment Variables

Create `.env.local` file with CDK outputs:

```bash
cat > .env.local << EOF
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_xxxxxxxxx
VITE_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_AWS_REGION=ap-southeast-1
VITE_API_GATEWAY_ENDPOINT=https://xxxxxxxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
EOF
```

**Get values from CDK outputs:**
```bash
# User Pool ID
aws cloudformation describe-stacks \
  --stack-name ECom67DataStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text

# Client ID
aws cloudformation describe-stacks \
  --stack-name ECom67DataStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text

# API Endpoint
aws cloudformation describe-stacks \
  --stack-name ECom67ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

#### Step 3: Test Locally

```bash
npm run dev
```

Access at: `http://localhost:5173`

#### Step 4: Build for Production

```bash
npm run build
```

**Output:** `dist/` directory with optimized static files

#### Step 5: Deploy to S3

```bash
# Get bucket name from CDK outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name ECom67InfraStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

# Sync build to S3
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete

# Verify
aws s3 ls s3://$BUCKET_NAME/
```

#### Step 6: Access Application

```bash
# Get website URL
echo "http://$BUCKET_NAME.s3-website-ap-southeast-1.amazonaws.com"
```

---

### Post-Deployment Steps

#### 1. Seed Product Data

```bash
cd backend/scripts
python populate_products.py
```

This script creates sample products in the DynamoDB table.

#### 2. Configure SNS Email Subscriptions

```bash
# Get SNS topic ARN
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name ECom67InfraStack \
  --query 'Stacks[0].Outputs[?OutputKey==`OrderNotificationTopicArn`].OutputValue' \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email
```

#### 3. Test API Endpoints

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ECom67ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Test public endpoint
curl $API_ENDPOINT/products

# Should return list of products
```

---

### Update Deployment

```bash
# Make code changes...

# Backend updates
cd backend
cdk deploy --all

# Frontend updates
cd frontend
npm run build
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete
```

---

### Teardown / Cleanup

**Delete all resources:**
```bash
cd backend

# Delete stacks in reverse dependency order
cdk destroy ECom67InfraStack
cdk destroy ECom67ApiStack
cdk destroy ECom67ComputeStack
cdk destroy ECom67DataStack

# Or destroy all at once
cdk destroy --all
```

**Note:** S3 buckets with auto-delete enabled will remove all objects automatically.

---

## Local Development Setup

### Backend Local Testing

#### Lambda Functions (Standalone)

**Option 1: Python Script Testing**

Create test event:
```python
# test_cart.py
import json
from lambda.cart.index import handler

event = {
    'httpMethod': 'GET',
    'requestContext': {
        'authorizer': {
            'claims': {
                'sub': 'test-user-123'
            }
        }
    },
    'pathParameters': None,
    'queryStringParameters': None
}

context = {}
response = handler(event, context)
print(json.dumps(response, indent=2))
```

Run:
```bash
cd backend
source .venv/bin/activate
export CART_TABLE=e-com67-cart
export PRODUCTS_TABLE=e-com67-products
python test_cart.py
```

**Option 2: SAM Local (recommended for API Gateway testing)**

Install SAM CLI:
```bash
brew install aws-sam-cli
```

Create `template.yaml` from CDK synth output or manually.

Start local API:
```bash
sam local start-api --template template.yaml
```

**Option 3: Docker + LocalStack**

Use LocalStack for full AWS service emulation:
```bash
docker run -d \
  -p 4566:4566 \
  -e SERVICES=dynamodb,lambda,apigateway,cognito \
  localstack/localstack
```

---

### Frontend Local Development

#### Step 1: Setup Environment

```bash
cd frontend
npm install

# Create .env.local with deployed backend resources
cp .env.example .env.local
# Edit .env.local with actual values
```

#### Step 2: Start Dev Server

```bash
npm run dev
```

Access at: `http://localhost:5173`

**Features:**
- Hot Module Replacement (instant updates)
- React Fast Refresh
- Tailwind CSS JIT compilation
- Source maps for debugging

#### Step 3: Development Workflow

**Code Changes:**
- Edit files in `src/`
- Browser auto-refreshes on save
- Console shows errors and warnings

**Adding Dependencies:**
```bash
npm install package-name
```

**Linting:**
```bash
npm run lint
```

**Build Test:**
```bash
npm run build
npm run preview  # Test production build locally
```

---

### IDE Setup (VS Code Recommended)

**Extensions:**
```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "amazonwebservices.aws-toolkit-vscode"
  ]
}
```

**Settings (`.vscode/settings.json`):**
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

---

### Testing

#### Backend Unit Tests (Planned)

```bash
cd backend
pytest tests/

# With coverage
pytest --cov=lambda tests/
```

**Example Test:**
```python
# tests/test_cart.py
import pytest
from lambda.cart.index import handler

def test_get_cart_unauthorized():
    event = {'httpMethod': 'GET', 'requestContext': {}}
    response = handler(event, {})
    assert response['statusCode'] == 401
```

#### Frontend Tests (Planned)

```bash
cd frontend

# Unit tests with Vitest
npm run test

# E2E tests with Playwright
npm run test:e2e
```

---

## Monitoring & Logging

### CloudWatch Logs

**Log Groups:**
- `/aws/lambda/ECom67-ProductCrudFunction`
- `/aws/lambda/ECom67-CartFunction`
- `/aws/lambda/ECom67-PaymentFunction`
- `/aws/lambda/ECom67-OrderProcessorFunction`
- `/aws/apigateway/ECom67Api`

**Viewing Logs:**
```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/ECom67-CartFunction \
  --order-by LastEventTime \
  --descending

# Tail logs
aws logs tail /aws/lambda/ECom67-CartFunction --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/ECom67-CartFunction \
  --filter-pattern "ERROR"
```

**Log Retention:**
- Development: 7 days
- Production: 30+ days (configurable)

---

### AWS Lambda Powertools

**Structured Logging:**

All Lambda functions use Powertools Logger for consistent log formatting.

**Log Format (JSON):**
```json
{
  "level": "INFO",
  "location": "handler:42",
  "message": "Cart retrieved successfully",
  "timestamp": "2025-12-16 10:30:45,123",
  "service": "cart",
  "userId": "user-123",
  "cartItemCount": 3,
  "xray_trace_id": "1-67890abc-def12345"
}
```

**Benefits:**
- Searchable in CloudWatch Logs Insights
- Automatic correlation with X-Ray traces
- Structured context (service, function, cold start, etc.)

**Example Query (CloudWatch Logs Insights):**
```sql
fields @timestamp, message, userId, cartItemCount
| filter service = "cart" and level = "ERROR"
| sort @timestamp desc
| limit 50
```

---

### X-Ray Tracing

**Enabled Services:**
- All Lambda functions
- API Gateway
- Step Functions
- DynamoDB calls (automatic)

**Viewing Traces:**
1. Go to AWS X-Ray Console
2. Select "Service Map" to see service dependencies
3. Select "Traces" to view individual requests
4. Filter by URL, status code, duration, etc.

**Example Service Map:**
```
Client → API Gateway → Lambda (Cart) → DynamoDB (cart table)
                                     → DynamoDB (products table)
```

**Trace Details:**
- Total request duration
- Lambda init duration (cold start)
- DynamoDB query latency
- Downstream service calls
- Errors and exceptions

**CLI Query:**
```bash
# Get trace summaries
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --region ap-southeast-1
```

---

### CloudWatch Metrics

**Lambda Metrics (Automatic):**
- Invocations
- Errors
- Duration
- Throttles
- Concurrent Executions
- Iterator Age (for SQS triggers)

**API Gateway Metrics:**
- Count (request count)
- Latency (request duration)
- 4XXError
- 5XXError
- IntegrationLatency

**DynamoDB Metrics:**
- ConsumedReadCapacityUnits
- ConsumedWriteCapacityUnits
- UserErrors
- SystemErrors
- ThrottledRequests

**SQS Metrics:**
- ApproximateNumberOfMessagesVisible
- ApproximateNumberOfMessagesDelayed
- NumberOfMessagesSent
- NumberOfMessagesReceived
- ApproximateAgeOfOldestMessage

**Custom Metrics (via Powertools):**

```python
from aws_lambda_powertools import Metrics

metrics = Metrics(namespace="ECom67", service="cart")

@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    metrics.add_metric(name="CartItemAdded", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="Category", value="Electronics")
    # ... handler logic
```

---

### CloudWatch Alarms

**Configured Alarms:**

| Alarm Name | Metric | Threshold | Action |
|------------|--------|-----------|--------|
| PaymentErrorAlarm | Lambda Errors (PaymentFunction) | 5 errors in 1 period | SNS notification |
| QueueDepthAlarm | SQS ApproximateNumberOfMessagesVisible | 100 messages | SNS notification |

**Creating Additional Alarms:**

```bash
# High Lambda error rate
aws cloudwatch put-metric-alarm \
  --alarm-name cart-function-errors \
  --alarm-description "Alert on cart function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=ECom67-CartFunction

# API Gateway high latency
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-latency \
  --metric-name Latency \
  --namespace AWS/ApiGateway \
  --statistic Average \
  --period 300 \
  --threshold 2000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

### Dashboard (Planned)

Create custom CloudWatch Dashboard for at-a-glance monitoring:

**Widgets:**
- API request count and error rate
- Lambda invocations and duration
- DynamoDB read/write throughput
- SQS queue depth
- Order processing rate
- Error logs (Logs Insights widget)

---

## Troubleshooting

### Common Issues

#### 1. CDK Deployment Fails

**Error:** "Resource handler returned message: Invalid request"

**Solution:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Ensure CDK is bootstrapped
cdk bootstrap

# Check for existing stack errors
aws cloudformation describe-stack-events \
  --stack-name ECom67DataStack \
  --max-items 10
```

---

#### 2. Lambda Function Timeout

**Error:** "Task timed out after X.00 seconds"

**Causes:**
- Slow DynamoDB query (missing indexes)
- Cold start with large deployment package
- External API call timeout

**Solution:**
```bash
# Increase timeout in CDK
lambda_.Function(
    timeout=Duration.seconds(60)  # Increase from 30s
)

# Optimize DynamoDB queries with indexes
# Reduce Lambda package size (use layers)
```

---

#### 3. Cognito Authentication Fails

**Error:** "User is not authenticated"

**Debug Steps:**
```javascript
// Check current user
import { getCurrentUser } from 'aws-amplify/auth';

try {
  const user = await getCurrentUser();
  console.log('User:', user);
} catch (err) {
  console.error('Not authenticated:', err);
}

// Check token
import { fetchAuthSession } from 'aws-amplify/auth';

const session = await fetchAuthSession();
console.log('ID Token:', session.tokens.idToken.toString());
```

**Common Fixes:**
- Verify User Pool ID and Client ID in `.env.local`
- Check Amplify configuration is called before any auth operations
- Verify user confirmed email (check Cognito console)

---

#### 4. CORS Errors in Browser

**Error:** "Access to fetch at '...' from origin '...' has been blocked by CORS policy"

**Solution:**

Ensure Lambda returns CORS headers:
```python
return {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,PUT,POST,DELETE',
        'Access-Control-Allow-Headers': 'Authorization,Content-Type'
    },
    'body': json.dumps(data)
}
```

Verify API Gateway CORS configuration in CDK:
```python
api.root.add_resource("products").add_cors_preflight(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
```

---

#### 5. DynamoDB Query Returns No Results

**Issue:** Query with GSI returns empty items array

**Debug:**
```python
# Check if GSI exists
aws dynamodb describe-table --table-name e-com67-products

# Check item has GSI attribute
aws dynamodb scan --table-name e-com67-products --limit 5

# Test query directly
aws dynamodb query \
  --table-name e-com67-products \
  --index-name category-index \
  --key-condition-expression "category = :cat" \
  --expression-attribute-values '{":cat": {"S": "Electronics"}}'
```

**Solution:**
- Ensure items have the `category` attribute
- Wait for GSI to finish backfilling (check table status)
- Use correct data types (String vs Number)

---

#### 6. Frontend Build Fails

**Error:** "Module not found" or "Cannot resolve module"

**Solution:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite

# Verify imports use correct paths
# ✅ import { api } from '@/services/api'
# ❌ import { api } from 'services/api'
```

---

#### 7. Step Functions Execution Fails

**Error:** "States.TaskFailed" in Step Functions console

**Debug:**
```bash
# Get execution ARN
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:... \
  --max-results 1

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:...

# View execution history
aws stepfunctions get-execution-history \
  --execution-arn arn:aws:states:... \
  --reverse-order
```

**Common Causes:**
- Lambda function error (check CloudWatch Logs)
- Invalid input format
- Timeout exceeded

---

#### 8. SQS Messages Not Processing

**Issue:** Messages stuck in queue, Lambda not triggered

**Check:**
```bash
# Check queue metrics
aws sqs get-queue-attributes \
  --queue-url https://sqs.ap-southeast-1.amazonaws.com/.../e-com67-order-queue \
  --attribute-names All

# Check event source mapping
aws lambda list-event-source-mappings \
  --function-name ECom67-OrderProcessorFunction

# Check DLQ
aws sqs get-queue-attributes \
  --queue-url https://sqs.ap-southeast-1.amazonaws.com/.../e-com67-order-dlq \
  --attribute-names ApproximateNumberOfMessages
```

**Solution:**
- Ensure Lambda has execution role with SQS permissions
- Check Lambda concurrency limits
- Review Lambda function errors (CloudWatch Logs)
- Process messages in DLQ manually if needed

---

### Debugging Lambda Locally

**Enable Debug Logging:**
```python
import os
os.environ['LOG_LEVEL'] = 'DEBUG'

from aws_lambda_powertools import Logger
logger = Logger(level='DEBUG')
```

**Test with Sample Events:**
```python
# Create test_events/cart_get.json
{
  "httpMethod": "GET",
  "requestContext": {
    "authorizer": {
      "claims": {
        "sub": "test-user-123"
      }
    }
  },
  "headers": {
    "Authorization": "Bearer mock-token"
  }
}

# Run locally
python -c "
import json
from lambda.cart.index import handler
with open('test_events/cart_get.json') as f:
    event = json.load(f)
print(handler(event, {}))
"
```

---

### Performance Optimization

#### Lambda Cold Start Reduction

**Current Cold Start:** ~800ms (Python 3.11, Powertools layer)

**Optimization Strategies:**
1. Use Lambda Provisioned Concurrency (costs more)
2. Reduce deployment package size
3. Minimize imports (import inside functions if rarely used)
4. Use Lambda SnapStart (Java only, not applicable)

**Example:**
```python
# ❌ Import at top level (loaded on cold start)
import pandas as pd  # Heavy library

# ✅ Import inside function (only when needed)
def rare_operation():
    import pandas as pd
    # Use pandas only for this specific operation
```

#### DynamoDB Query Optimization

**Use Indexes:**
- Category filtering: Use `category-index` GSI
- User order history: Use `userId-timestamp-index` GSI

**Limit Results:**
```python
response = table.query(
    Limit=50,  # Return max 50 items
    ScanIndexForward=False  # Reverse order (newest first)
)
```

**Avoid Scans:**
```python
# ❌ Slow - full table scan
response = table.scan()

# ✅ Fast - query with partition key
response = table.query(
    KeyConditionExpression=Key('userId').eq(user_id)
)
```

---

## Planned Features

### 1. Stripe Payment Integration

**Status:** Payment stub exists, needs Stripe SDK integration

**Implementation Plan:**
1. Add Stripe secret key to AWS Secrets Manager
2. Install Stripe SDK in Lambda layer
3. Update `PaymentFunction` to create PaymentIntent
4. Add webhook endpoint for payment confirmation
5. Update frontend Checkout page with Stripe Elements

**Files to Modify:**
- `backend/lambda/payment/index.py`
- `backend/e_com67/stacks/compute_stack.py` (add Stripe layer)
- `frontend/src/pages/Checkout.jsx`

**Estimated Effort:** 2-3 days

---

### 2. OpenSearch Product Search

**Status:** Domain provisioned, integration pending

**Implementation Plan:**
1. Create Lambda function to sync DynamoDB → OpenSearch
2. Add DynamoDB Streams trigger on products table
3. Create search Lambda function to query OpenSearch
4. Add `/search` API endpoint
5. Update frontend SearchBar to use new endpoint

**Files to Create/Modify:**
- `backend/lambda/opensearch_sync/index.py` (new)
- `backend/lambda/search/index.py` (new)
- `backend/e_com67/stacks/compute_stack.py`
- `backend/e_com67/stacks/api_stack.py`
- `frontend/src/components/SearchBar.jsx`

**Estimated Effort:** 3-4 days

---

### 3. AI Chat with Amazon Bedrock

**Status:** ChatWidget UI exists, backend not implemented

**Implementation Plan:**
1. Create WebSocket API in API Gateway
2. Create Lambda functions for WebSocket routes ($connect, $disconnect, sendMessage)
3. Integrate Bedrock Claude model for chat responses
4. Implement RAG with S3 knowledge base
5. Store chat history in DynamoDB
6. Update ChatWidget with WebSocket connection

**Files to Create/Modify:**
- `backend/lambda/chat_connect/index.py` (new)
- `backend/lambda/chat_disconnect/index.py` (new)
- `backend/lambda/chat_message/index.py` (new)
- `backend/e_com67/stacks/infra_stack.py` (add WebSocket API)
- `frontend/src/components/ChatWidget.jsx`
- `frontend/src/services/websocket.js`

**Estimated Effort:** 5-6 days

---

### 4. Email Notifications via SES

**Status:** SNS topic exists, SES integration pending

**Implementation Plan:**
1. Verify email domain in SES (or single email for sandbox)
2. Create Lambda function to send HTML emails
3. Subscribe Lambda to SNS topic
4. Create email templates for order confirmation
5. Test email delivery

**Files to Create/Modify:**
- `backend/lambda/send_email/index.py` (new)
- `backend/e_com67/stacks/infra_stack.py` (add SES permissions)
- `backend/templates/order_confirmation.html` (new)

**Estimated Effort:** 1-2 days

---

### 5. Admin Dashboard

**Status:** Not started

**Features:**
- View all orders
- Manage products (CRUD via admin UI)
- View analytics (sales, revenue, popular products)
- User management
- Inventory alerts

**Implementation Plan:**
1. Create admin Cognito group
2. Add admin authorization to API endpoints
3. Create admin React pages
4. Add CloudWatch Logs Insights queries for analytics
5. Create admin-specific API endpoints

**Estimated Effort:** 1-2 weeks

---

### 6. CI/CD Pipeline

**Status:** Not started

**Implementation Plan:**
1. Create GitHub Actions workflow for frontend
   - Install dependencies
   - Run tests
   - Build production bundle
   - Deploy to S3
2. Create GitHub Actions workflow for backend
   - Run unit tests
   - Synthesize CDK
   - Deploy to AWS (on merge to main)
3. Add branch protection rules
4. Add manual approval step for production

**Files to Create:**
- `.github/workflows/frontend.yml`
- `.github/workflows/backend.yml`

**Estimated Effort:** 2-3 days

---

### 7. Advanced Features (Future)

**Product Reviews & Ratings:**
- New DynamoDB table: `reviews`
- API endpoints for submitting/viewing reviews
- Star rating component

**Wishlists:**
- New DynamoDB table: `wishlists`
- Save products for later
- Share wishlists

**Recommendations Engine:**
- ML-based product recommendations
- Amazon Personalize integration
- "Customers who bought this also bought..."

**Real-time Inventory Updates:**
- WebSocket notifications for stock changes
- Low stock alerts
- Out-of-stock handling

**Multi-Currency Support:**
- Currency conversion API integration
- User preference storage
- Dynamic pricing display

**Shipping Integration:**
- Third-party shipping API (ShipStation, EasyPost)
- Track order status
- Shipping cost calculation

---

## Appendix

### Environment Variables Reference

**Backend (Lambda):**
```bash
# DynamoDB Tables
PRODUCTS_TABLE=e-com67-products
CART_TABLE=e-com67-cart
ORDERS_TABLE=e-com67-orders
CHAT_HISTORY_TABLE=e-com67-chat-history

# SNS
SNS_TOPIC_ARN=arn:aws:sns:ap-southeast-1:724542698940:e-com67-order-notifications

# OpenSearch
OPENSEARCH_ENDPOINT=search-e-com67-search-xxxxx.ap-southeast-1.es.amazonaws.com

# Powertools
POWERTOOLS_SERVICE_NAME=<function-specific>
POWERTOOLS_METRICS_NAMESPACE=ECom67
LOG_LEVEL=INFO
```

**Frontend (.env.local):**
```bash
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_xxxxxxxxx
VITE_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_AWS_REGION=ap-southeast-1
VITE_API_GATEWAY_ENDPOINT=https://xxxxxxxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
```

---

### Useful AWS CLI Commands

**DynamoDB:**
```bash
# List tables
aws dynamodb list-tables

# Get table description
aws dynamodb describe-table --table-name e-com67-products

# Scan table (get all items)
aws dynamodb scan --table-name e-com67-products --limit 10

# Get single item
aws dynamodb get-item \
  --table-name e-com67-products \
  --key '{"productId": {"S": "uuid-here"}}'

# Put item
aws dynamodb put-item \
  --table-name e-com67-products \
  --item file://product.json
```

**Lambda:**
```bash
# List functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ECom67`)].FunctionName'

# Invoke function
aws lambda invoke \
  --function-name ECom67-CartFunction \
  --payload file://event.json \
  response.json

# Update environment variable
aws lambda update-function-configuration \
  --function-name ECom67-CartFunction \
  --environment "Variables={LOG_LEVEL=DEBUG}"
```

**CloudWatch Logs:**
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/ECom67-CartFunction --follow

# Query logs
aws logs start-query \
  --log-group-name /aws/lambda/ECom67-CartFunction \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter level = "ERROR"'
```

**Cognito:**
```bash
# List users
aws cognito-idp list-users --user-pool-id ap-southeast-1_xxxxxxxxx

# Admin create user
aws cognito-idp admin-create-user \
  --user-pool-id ap-southeast-1_xxxxxxxxx \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com \
  --temporary-password TempPass123

# Delete user
aws cognito-idp admin-delete-user \
  --user-pool-id ap-southeast-1_xxxxxxxxx \
  --username user@example.com
```

**Step Functions:**
```bash
# List executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-southeast-1:724542698940:stateMachine:e-com67-checkout

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:... \
  --input file://input.json

# Stop execution
aws stepfunctions stop-execution \
  --execution-arn arn:aws:states:...
```

---

### Cost Estimation (Monthly)

**Assumptions:**
- 10,000 API requests/month
- 100 orders/month
- Single-node OpenSearch (development)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda | 10,000 invocations, 128-512MB, avg 500ms | $0.20 |
| API Gateway | 10,000 requests | $0.04 |
| DynamoDB | On-demand, 10K reads, 1K writes | $0.50 |
| Cognito | 100 MAU (free tier) | $0.00 |
| S3 | 5GB storage, 10K requests | $0.15 |
| CloudWatch | 5GB logs, 10 alarms | $2.00 |
| OpenSearch | t3.small.search, 730 hrs, 10GB storage | $35.00 |
| Step Functions | 100 executions | $0.03 |
| SQS | 1,000 requests | $0.00 (free tier) |
| SNS | 100 notifications | $0.00 (free tier) |
| X-Ray | 10,000 traces | $0.50 |
| **Total** | | **~$38.42/month** |

**Production Estimates (1M requests/month):**
- Lambda: $20
- API Gateway: $3.50
- DynamoDB: $25
- OpenSearch (3-node cluster): $300
- CloudWatch: $10
- **Total: ~$358/month**

---

### Security Best Practices

**1. Secrets Management:**
- Store API keys in AWS Secrets Manager (not environment variables)
- Rotate secrets regularly
- Grant least-privilege IAM access to secrets

**2. IAM Policies:**
- Use resource-specific permissions (not `*`)
- Enable MFA for production deployments
- Regular IAM access reviews

**3. API Security:**
- Enable AWS WAF for production API Gateway
- Add rate limiting (throttling)
- Implement request validation
- Log all API access

**4. Data Protection:**
- Enable DynamoDB encryption at rest (enabled by default)
- Use HTTPS only (enforce in API Gateway)
- Implement input validation in Lambda functions
- Sanitize user inputs to prevent injection attacks

**5. Monitoring:**
- Enable CloudTrail for API audit logs
- Set up alarms for suspicious activity
- Regular security audits with AWS Trusted Advisor

---

### Support & Contact

**Documentation:**
- AWS CDK: https://docs.aws.amazon.com/cdk/
- AWS Amplify: https://docs.amplify.aws/
- React: https://react.dev/

**Issues & Bug Reports:**
- Create GitHub issue in project repository
- Include error logs and reproduction steps

**Questions:**
- Check existing documentation first
- AWS re:Post for AWS-specific questions
- Stack Overflow for general development questions

---

**Document Version:** 1.0
**Last Updated:** December 16, 2025
**Maintained By:** Development Team
