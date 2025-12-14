# 🛍️ AWS Serverless E-commerce - Implementation Guide

## 📋 Table of Contents
1. [Architecture Summary](#architecture-summary)
2. [CDK Stack Structure](#cdk-stack-structure)
3. [Lambda Functions](#lambda-functions)
4. [API Endpoints](#api-endpoints)
5. [Frontend Architecture](#frontend-architecture)
6. [Frontend Setup & Components](#frontend-setup--components)
7. [Deployment Steps](#deployment-steps)
8. [Testing Checklist](#testing-checklist)

---

## Backend Architecture Summary

### Core User Flows

#### 1. **Authentication Flow**
```
User → React (Amplify Auth) → Cognito → JWT Token → API Gateway Authorizer
↓
Post-Auth Trigger → Lambda → DynamoDB (save user profile)
```

#### 2. **Product Discovery Flow**
```
User searches → API Gateway → Lambda → OpenSearch → Results
OR
User browses by category → Lambda → DynamoDB Query (GSI: category-index)
```

#### 3. **Checkout Flow**
```
User clicks "Place Order" → API Gateway → Step Function
  ├─ Step 1: Validate Cart (Lambda)
  ├─ Step 2: Process Payment (Lambda → Stripe API) [with retry]
  ├─ Step 3: Success → Send to SQS
  └─ Failure → Return error

SQS → Lambda Consumer
  ├─ Create Order in DynamoDB
  ├─ Clear Cart
  ├─ Update Product Stock
  └─ Trigger SNS → SES (send email)
```

#### 4. **AI Chat Flow**
```
User opens chat → WebSocket Connection → API Gateway (WebSocket)
User sends message → Lambda
  ├─ Retrieve context from Knowledge Base (S3)
  ├─ Call Bedrock (Claude) with RAG
  ├─ Save to ChatHistory (DynamoDB)
  └─ Stream response via WebSocket
```

---

## CDK Stack Structure

### Project Setup
```bash
# Initialize CDK project
mkdir ecommerce-aws-cdk && cd ecommerce-aws-cdk
cdk init app --language python
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### requirements.txt
```txt
aws-cdk-lib==2.120.0
constructs>=10.0.0
aws-cdk.aws-lambda-python-alpha==2.120.0a0
```

### Main Stack Organization


**cdk_app.py** (Entry point)
```python
#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.main_stack import ECom67Stack

app = cdk.App()
ECom67Stack(app, "e-com67Stack", 
    env=cdk.Environment(
        account='YOUR_ACCOUNT_ID',
        region='us-east-1'
    )
)
app.synth()
```

### Stack Breakdown (infrastructure/main_stack.py)

```python
from aws_cdk import Stack, RemovalPolicy, Duration
from constructs import Construct
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_opensearchservice as opensearch,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs
)

class ECom67Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # 1. Create DynamoDB Tables
        self.create_dynamodb_tables()
        
        # 2. Create Cognito User Pool
        self.create_cognito()
        
        # 3. Create Lambda Layers
        self.create_lambda_layers()
        
        # 4. Create Lambda Functions
        self.create_lambda_functions()
        
        # 5. Create API Gateway
        self.create_api_gateway()
        
        # 6. Create OpenSearch
        self.create_opensearch()
        
        # 7. Create SQS/SNS
        self.create_messaging()
        
        # 8. Create Step Functions
        self.create_step_functions()
        
        # 9. Create S3 Buckets
        self.create_s3_buckets()
        
        # 10. Create Bedrock Integration
        self.create_bedrock()
        
        # 11. Create Monitoring
        self.create_monitoring()
        
        # 12. Create EventBridge Rules
        self.create_scheduled_jobs()
```

---

## DynamoDB Tables

### 1. Users Table
```python
def create_dynamodb_tables(self):
    # Users Table
    self.users_table = dynamodb.Table(
        self, "UsersTable",
        partition_key=dynamodb.Attribute(
            name="userId",
            type=dynamodb.AttributeType.STRING
        ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy=RemovalPolicy.DESTROY,  # For dev only
        stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
    )
```

### 2. Products Table (with GSI)
```python
    self.products_table = dynamodb.Table(
        self, "ProductsTable",
        partition_key=dynamodb.Attribute(
            name="productId",
            type=dynamodb.AttributeType.STRING
        ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy=RemovalPolicy.DESTROY,
        stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
    )
    
    # Add GSI for category-based queries
    self.products_table.add_global_secondary_index(
        index_name="category-index",
        partition_key=dynamodb.Attribute(
            name="category",
            type=dynamodb.AttributeType.STRING
        ),
        projection_type=dynamodb.ProjectionType.ALL
    )
```

### 3. Orders Table (with Composite Key + GSI)
```python
    self.orders_table = dynamodb.Table(
        self, "OrdersTable",
        partition_key=dynamodb.Attribute(
            name="orderId",
            type=dynamodb.AttributeType.STRING
        ),
        sort_key=dynamodb.Attribute(
            name="userId",
            type=dynamodb.AttributeType.STRING
        ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy=RemovalPolicy.DESTROY
    )
    
    # GSI for querying user's orders sorted by timestamp
    self.orders_table.add_global_secondary_index(
        index_name="userId-timestamp-index",
        partition_key=dynamodb.Attribute(
            name="userId",
            type=dynamodb.AttributeType.STRING
        ),
        sort_key=dynamodb.Attribute(
            name="timestamp",
            type=dynamodb.AttributeType.NUMBER
        ),
        projection_type=dynamodb.ProjectionType.ALL
    )
```

### 4. Cart Table
```python
    self.cart_table = dynamodb.Table(
        self, "CartTable",
        partition_key=dynamodb.Attribute(
            name="userId",
            type=dynamodb.AttributeType.STRING
        ),
        sort_key=dynamodb.Attribute(
            name="productId",
            type=dynamodb.AttributeType.STRING
        ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy=RemovalPolicy.DESTROY
    )
```

### 5. ChatHistory Table
```python
    self.chat_table = dynamodb.Table(
        self, "ChatHistoryTable",
        partition_key=dynamodb.Attribute(
            name="userId",
            type=dynamodb.AttributeType.STRING
        ),
        sort_key=dynamodb.Attribute(
            name="timestamp",
            type=dynamodb.AttributeType.NUMBER
        ),
        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy=RemovalPolicy.DESTROY
    )
```

---

## Lambda Functions

### Lambda Layers
```python
def create_lambda_layers(self):
    # Common utilities layer
    self.common_layer = lambda_.LayerVersion(
        self, "CommonUtilsLayer",
        code=lambda_.Code.from_asset("lambda/layers/common_utils"),
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
        description="Common utilities, logging, error handling"
    )
    
    # Stripe SDK layer
    self.stripe_layer = lambda_.LayerVersion(
        self, "StripeSdkLayer",
        code=lambda_.Code.from_asset("lambda/layers/stripe_sdk"),
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
        description="Stripe Python SDK"
    )
```

### Sample Lambda Functions

#### 1. Product CRUD
```python
def create_lambda_functions(self):
    # Product CRUD
    self.product_crud_fn = lambda_.Function(
        self, "ProductCrudFunction",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_asset("lambda/products"),
        layers=[self.common_layer],
        environment={
            "PRODUCTS_TABLE": self.products_table.table_name,
            "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint
        },
        timeout=Duration.seconds(30),
        memory_size=512
    )
    
    # Grant permissions
    self.products_table.grant_read_write_data(self.product_crud_fn)
```

#### 2. Cart Handler
```python
    self.cart_fn = lambda_.Function(
        self, "CartFunction",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_asset("lambda/cart"),
        layers=[self.common_layer],
        environment={
            "CART_TABLE": self.cart_table.table_name,
            "PRODUCTS_TABLE": self.products_table.table_name
        },
        timeout=Duration.seconds(10)
    )
    
    self.cart_table.grant_read_write_data(self.cart_fn)
    self.products_table.grant_read_data(self.cart_fn)
```

#### 3. Payment Handler (Stripe Integration)
```python
    self.payment_fn = lambda_.Function(
        self, "PaymentFunction",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_asset("lambda/payment"),
        layers=[self.common_layer, self.stripe_layer],
        environment={
            "STRIPE_API_KEY": "{{resolve:secretsmanager:stripe-api-key}}",
            "ORDERS_TABLE": self.orders_table.table_name
        },
        timeout=Duration.seconds(30)
    )
```

#### 4. Order Processor (SQS Consumer)
```python
    self.order_processor_fn = lambda_.Function(
        self, "OrderProcessorFunction",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_asset("lambda/order_processor"),
        layers=[self.common_layer],
        environment={
            "ORDERS_TABLE": self.orders_table.table_name,
            "CART_TABLE": self.cart_table.table_name,
            "PRODUCTS_TABLE": self.products_table.table_name,
            "SNS_TOPIC_ARN": self.order_notification_topic.topic_arn
        },
        timeout=Duration.seconds(60)
    )
    
    # Grant permissions
    self.orders_table.grant_read_write_data(self.order_processor_fn)
    self.cart_table.grant_read_write_data(self.order_processor_fn)
    self.products_table.grant_read_write_data(self.order_processor_fn)
    self.order_notification_topic.grant_publish(self.order_processor_fn)
```

---

## API Gateway

### REST API with Cognito Authorizer
```python
def create_api_gateway(self):
    # Create Cognito Authorizer
    authorizer = apigw.CognitoUserPoolsAuthorizer(
        self, "ECom67Authorizer",
        cognito_user_pools=[self.user_pool]
    )
    
    # Create REST API
    api = apigw.RestApi(
        self, "ECom67Api",
        rest_api_name="e-com67 API",
        description="Serverless e-com67 API",
        default_cors_preflight_options=apigw.CorsOptions(
            allow_origins=apigw.Cors.ALL_ORIGINS,
            allow_methods=apigw.Cors.ALL_METHODS
        )
    )
    
    # Products endpoints
    products = api.root.add_resource("products")
    products.add_method(
        "GET",
        apigw.LambdaIntegration(self.product_crud_fn)
    )
    products.add_method(
        "POST",
        apigw.LambdaIntegration(self.product_crud_fn),
        authorizer=authorizer,
        authorization_type=apigw.AuthorizationType.COGNITO
    )
    
    product = products.add_resource("{productId}")
    product.add_method("GET", apigw.LambdaIntegration(self.product_crud_fn))
    product.add_method(
        "PUT",
        apigw.LambdaIntegration(self.product_crud_fn),
        authorizer=authorizer
    )
    
    # Search endpoint
    search = api.root.add_resource("search")
    search.add_method("GET", apigw.LambdaIntegration(self.search_fn))
    
    # Cart endpoints
    cart = api.root.add_resource("cart")
    cart.add_method(
        "GET",
        apigw.LambdaIntegration(self.cart_fn),
        authorizer=authorizer
    )
    cart.add_method(
        "POST",
        apigw.LambdaIntegration(self.cart_fn),
        authorizer=authorizer
    )
    
    # Orders endpoints
    orders = api.root.add_resource("orders")
    orders.add_method(
        "POST",
        apigw.LambdaIntegration(self.checkout_fn),
        authorizer=authorizer
    )
    orders.add_method(
        "GET",
        apigw.LambdaIntegration(self.orders_fn),
        authorizer=authorizer
    )
```

### WebSocket API for Chat
```python
    # WebSocket API for real-time chat
    websocket_api = apigw.CfnApi(
        self, "ChatWebSocketApi",
        name="e-com67 Chat WebSocket",
        protocol_type="WEBSOCKET",
        route_selection_expression="$request.body.action"
    )
    
    # WebSocket routes
    connect_route = apigw.CfnRoute(
        self, "ConnectRoute",
        api_id=websocket_api.ref,
        route_key="$connect",
        authorization_type="NONE",
        target=f"integrations/{connect_integration.ref}"
    )
```

---

## Step Functions (Payment Workflow)

```python
def create_step_functions(self):
    # Define tasks
    validate_cart = tasks.LambdaInvoke(
        self, "ValidateCart",
        lambda_function=self.validate_cart_fn,
        output_path="$.Payload"
    )
    
    process_payment = tasks.LambdaInvoke(
        self, "ProcessPayment",
        lambda_function=self.payment_fn,
        output_path="$.Payload",
        retry_on_service_exceptions=True
    )
    
    send_to_queue = tasks.SqsSendMessage(
        self, "SendToQueue",
        queue=self.order_queue,
        message_body=sfn.TaskInput.from_json_path_at("$")
    )
    
    # Define state machine
    definition = validate_cart \
        .next(process_payment) \
        .next(send_to_queue)
    
    self.checkout_state_machine = sfn.StateMachine(
        self, "CheckoutStateMachine",
        definition=definition,
        timeout=Duration.minutes(5)
    )
```

---

## SQS & SNS

```python
def create_messaging(self):
    # Dead Letter Queue
    dlq = sqs.Queue(
        self, "OrderDLQ",
        retention_period=Duration.days(14)
    )
    
    # Order Processing Queue
    self.order_queue = sqs.Queue(
        self, "OrderQueue",
        visibility_timeout=Duration.seconds(90),
        dead_letter_queue=sqs.DeadLetterQueue(
            max_receive_count=3,
            queue=dlq
        )
    )
    
    # Connect Lambda to SQS
    self.order_processor_fn.add_event_source(
        lambda_event_sources.SqsEventSource(self.order_queue, batch_size=10)
    )
    
    # SNS Topic for Order Notifications
    self.order_notification_topic = sns.Topic(
        self, "OrderNotificationTopic",
        display_name="Order Notifications"
    )
    
    # Subscribe SES email
    self.order_notification_topic.add_subscription(
        sns_subs.LambdaSubscription(self.email_fn)
    )
```

---

## CloudWatch Alarms

```python
def create_monitoring(self):
    # Lambda Error Alarm
    self.payment_fn.metric_errors().create_alarm(
        self, "PaymentErrorAlarm",
        threshold=5,
        evaluation_periods=1,
        alarm_description="Payment function errors"
    )
    
    # API Gateway 5xx Alarm
    api_5xx = cloudwatch.Metric(
        namespace="AWS/ApiGateway",
        metric_name="5XXError",
        dimensions_map={"ApiName": "ECom67Api"}
    )
    
    api_5xx.create_alarm(
        self, "Api5xxAlarm",
        threshold=10,
        evaluation_periods=2
    )
    
    # SQS Queue Depth Alarm
    self.order_queue.metric_approximate_number_of_messages_visible().create_alarm(
        self, "QueueDepthAlarm",
        threshold=100,
        evaluation_periods=1
    )
```

---

## Lambda Function Examples

### lambda/products/index.py
```python
import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Product CRUD handler
    """
    try:
        http_method = event['httpMethod']
        path_params = event.get('pathParameters', {})
        
        if http_method == 'GET':
            if path_params and 'productId' in path_params:
                return get_product(path_params['productId'])
            else:
                return list_products(event.get('queryStringParameters', {}))
        
        elif http_method == 'POST':
            body = json.loads(event['body'])
            return create_product(body)
        
        elif http_method == 'PUT':
            body = json.loads(event['body'])
            return update_product(path_params['productId'], body)
        
        elif http_method == 'DELETE':
            return delete_product(path_params['productId'])
        
        return error_response(400, "Unsupported method")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")

def list_products(query_params: Dict) -> Dict:
    """List products with optional category filter"""
    category = query_params.get('category')
    
    if category:
        response = products_table.query(
            IndexName='category-index',
            KeyConditionExpression='category = :cat',
            ExpressionAttributeValues={':cat': category}
        )
    else:
        response = products_table.scan(Limit=50)
    
    return success_response(response.get('Items', []))

def get_product(product_id: str) -> Dict:
    """Get single product"""
    response = products_table.get_item(Key={'productId': product_id})
    
    if 'Item' not in response:
        return error_response(404, "Product not found")
    
    return success_response(response['Item'])

def create_product(data: Dict) -> Dict:
    """Create new product"""
    import uuid
    
    product_id = str(uuid.uuid4())
    item = {
        'productId': product_id,
        'name': data['name'],
        'description': data.get('description', ''),
        'price': Decimal(str(data['price'])),
        'category': data['category'],
        'stock': data.get('stock', 0),
        'imageUrl': data.get('imageUrl', '')
    }
    
    products_table.put_item(Item=item)
    return success_response(item, 201)

def success_response(data: Any, status_code: int = 200) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data, default=str)
    }

def error_response(status_code: int, message: str) -> Dict:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
```

### lambda/order_processor/index.py
```python
import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])
cart_table = dynamodb.Table(os.environ['CART_TABLE'])
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])
sns_topic_arn = os.environ['SNS_TOPIC_ARN']

def handler(event, context):
    """
    Process orders from SQS queue
    """
    for record in event['Records']:
        try:
            order_data = json.loads(record['body'])
            process_order(order_data)
        except Exception as e:
            print(f"Failed to process order: {str(e)}")
            raise  # Will send to DLQ after retries

def process_order(order_data):
    """
    1. Create order in DynamoDB
    2. Clear user's cart
    3. Update product stock
    4. Send notification
    """
    user_id = order_data['userId']
    order_id = order_data['orderId']
    items = order_data['items']
    
    # 1. Create order
    orders_table.put_item(Item={
        'orderId': order_id,
        'userId': user_id,
        'items': items,
        'totalAmount': Decimal(str(order_data['totalAmount'])),
        'status': 'PROCESSING',
        'paymentId': order_data['paymentId'],
        'timestamp': order_data['timestamp']
    })
    
    # 2. Clear cart
    for item in items:
        cart_table.delete_item(
            Key={'userId': user_id, 'productId': item['productId']}
        )
    
    # 3. Update stock
    for item in items:
        products_table.update_item(
            Key={'productId': item['productId']},
            UpdateExpression='SET stock = stock - :qty',
            ExpressionAttributeValues={':qty': item['quantity']}
        )
    
    # 4. Send notification
    sns.publish(
        TopicArn=sns_topic_arn,
        Subject='Order Confirmation',
        Message=json.dumps({
            'orderId': order_id,
            'userId': user_id,
            'email': order_data.get('email'),
            'totalAmount': order_data['totalAmount']
        })
    )
    
    print(f"Order {order_id} processed successfully")
```

---

## Frontend Architecture

### Frontend Tech Stack
- **React 18** - UI framework
- **AWS Amplify** - Authentication and API integration
- **Tailwind CSS** - Styling and responsive design
- **React Router** - Client-side navigation
- **Axios** - HTTP client for API calls

### Frontend Project Structure

```
frontend/
├── src/
│   ├── pages/                    # Page components
│   │   ├── Login.jsx             # Cognito authentication (signup/login)
│   │   ├── Products.jsx          # Product listing with filters
│   │   ├── ProductDetail.jsx     # Single product view
│   │   ├── Cart.jsx              # Shopping cart management
│   │   ├── Checkout.jsx          # Payment processing
│   │   └── Orders.jsx            # Order history
│   ├── components/               # Reusable components
│   │   ├── Navbar.jsx            # Top navigation bar
│   │   ├── ProductCard.jsx       # Product display card
│   │   ├── ChatWidget.jsx        # AI chat interface
│   │   └── SearchBar.jsx         # Product search
│   ├── services/                 # API and utility services
│   │   ├── api.js                # API Gateway calls
│   │   ├── auth.js               # Amplify Auth wrapper
│   │   └── websocket.js          # WebSocket connections
│   ├── aws-exports.js            # Amplify configuration
│   ├── App.js                    # Main app component
│   ├── App.css                   # Global styles
│   └── index.js                  # React entry point
├── public/
│   ├── index.html                # HTML template
│   └── favicon.ico
├── package.json                  # Node dependencies
├── .env.local                    # Environment variables (not in git)
├── tailwind.config.js            # Tailwind CSS config
└── postcss.config.js             # PostCSS config
```

### Frontend Key Features

1. **Authentication (Cognito + Amplify)**
   - User signup with email verification
   - Login/logout functionality
   - JWT token management
   - Protected routes

2. **Product Management**
   - Browse all products
   - Filter by category
   - Search functionality
   - Product detail view

3. **Shopping Cart**
   - Add/remove items
   - Update quantities
   - Persistent cart state
   - Real-time total calculation

4. **Checkout & Payment**
   - Order review
   - Stripe integration
   - Order confirmation
   - Order history

5. **AI Chat**
   - Real-time WebSocket connection
   - Chat history
   - Product recommendations
   - Bedrock Claude integration

---

## Frontend Setup & Components

### Amplify Configuration - `aws-exports.js`

```javascript
const awsconfig = {
  Auth: {
    region: 'us-east-1',
    userPoolId: 'YOUR_USER_POOL_ID',        // From CDK output
    userPoolWebClientId: 'YOUR_CLIENT_ID',  // From CDK output
  },
  API: {
    endpoints: [
      {
        name: 'ECom67Api',
        endpoint: 'YOUR_API_ENDPOINT',       // From CDK output
        region: 'us-east-1',
      },
    ],
  },
};

export default awsconfig;
```

### App.js - Main Application

```javascript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Auth } from 'aws-amplify';
import Login from './pages/Login';
import Products from './pages/Products';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import Navbar from './components/Navbar';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const currentUser = await Auth.currentAuthenticatedUser();
      setUser(currentUser);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }

  return (
    <Router>
      {user && <Navbar user={user} onLogout={() => setUser(null)} />}
      <Routes>
        {!user ? (
          <>
            <Route path="/login" element={<Login onSuccess={checkUser} />} />
            <Route path="*" element={<Navigate to="/login" />} />
          </>
        ) : (
          <>
            <Route path="/products" element={<Products />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/" element={<Navigate to="/products" />} />
          </>
        )}
      </Routes>
    </Router>
  );
}

export default App;
```

### Login Page - `pages/Login.jsx`

```javascript
import React, { useState } from 'react';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';

function Login({ onSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await Auth.signIn(email, password);
      onSuccess();
      navigate('/products');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await Auth.signUp({
        username: email,
        password: password,
        attributes: {
          email: email,
        },
      });
      alert('Sign up successful! Please check your email for verification.');
      setIsSignUp(false);
      setEmail('');
      setPassword('');
    } catch (err) {
      setError(err.message || 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600">
      <div className="bg-white p-8 rounded-lg shadow-2xl w-96">
        <h2 className="text-3xl font-bold mb-6 text-center">
          {isSignUp ? 'Create Account' : 'Login to E-Com67'}
        </h2>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={isSignUp ? handleSignUp : handleLogin}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 mb-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />

          <input
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 mb-6 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 disabled:opacity-50 font-bold transition"
          >
            {loading ? 'Loading...' : isSignUp ? 'Sign Up' : 'Login'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError('');
            }}
            className="text-blue-500 hover:underline font-bold"
          >
            {isSignUp ? 'Login' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default Login;
```

### Products Page - `pages/Products.jsx`

```javascript
import React, { useState, useEffect } from 'react';
import { API } from 'aws-amplify';
import ProductCard from '../components/ProductCard';
import SearchBar from '../components/SearchBar';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('');

  useEffect(() => {
    loadProducts();
  }, [category]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const params = category ? { queryStringParameters: { category } } : {};
      const response = await API.get('ECom67Api', '/products', params);
      setProducts(response || []);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query) => {
    if (!query) {
      loadProducts();
      return;
    }
    
    try {
      setLoading(true);
      const results = await API.get('ECom67Api', '/search', {
        queryStringParameters: { q: query }
      });
      setProducts(results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-8">Loading products...</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-4xl font-bold mb-6">Products</h1>
      
      <SearchBar onSearch={handleSearch} />

      <div className="my-4 flex gap-2">
        <button
          onClick={() => setCategory('')}
          className={`px-4 py-2 rounded ${!category ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          All
        </button>
        {['Electronics', 'Clothing', 'Books', 'Home'].map(cat => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-4 py-2 rounded ${category === cat ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((product) => (
          <ProductCard key={product.productId} product={product} />
        ))}
      </div>
    </div>
  );
}

export default Products;
```

### Cart Page - `pages/Cart.jsx`

```javascript
import React, { useState, useEffect } from 'react';
import { API } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';

function Cart() {
  const [cartItems, setCartItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadCart();
  }, []);

  const loadCart = async () => {
    try {
      const response = await API.get('ECom67Api', '/cart');
      setCartItems(response || []);
    } catch (err) {
      console.error('Failed to load cart:', err);
    } finally {
      setLoading(false);
    }
  };

  const removeFromCart = async (productId) => {
    try {
      await API.del('ECom67Api', '/cart', {
        queryStringParameters: { productId },
      });
      loadCart();
    } catch (err) {
      console.error('Failed to remove from cart:', err);
    }
  };

  const updateQuantity = async (productId, quantity) => {
    try {
      await API.post('ECom67Api', '/cart', {
        body: { productId, quantity },
      });
      loadCart();
    } catch (err) {
      console.error('Failed to update quantity:', err);
    }
  };

  if (loading) return <div>Loading cart...</div>;

  const total = cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-4xl font-bold mb-6">Shopping Cart</h1>

      {cartItems.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-xl text-gray-600 mb-4">Your cart is empty</p>
          <button
            onClick={() => navigate('/products')}
            className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
          >
            Continue Shopping
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-4 mb-8">
            {cartItems.map((item) => (
              <div key={item.productId} className="border rounded-lg p-4 flex justify-between items-center bg-gray-50">
                <div>
                  <h3 className="font-bold text-lg">{item.name}</h3>
                  <p className="text-gray-600">Price: ${item.price.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-4">
                  <input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => updateQuantity(item.productId, parseInt(e.target.value))}
                    className="w-12 px-2 py-1 border rounded"
                  />
                  <p className="font-bold">${(item.price * item.quantity).toFixed(2)}</p>
                  <button
                    onClick={() => removeFromCart(item.productId)}
                    className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t-2 pt-4 bg-gray-100 p-4 rounded">
            <p className="text-3xl font-bold mb-6 text-right">Total: ${total.toFixed(2)}</p>
            <button
              onClick={() => navigate('/checkout')}
              className="w-full bg-green-500 text-white py-3 rounded-lg hover:bg-green-600 text-lg font-bold"
            >
              Proceed to Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default Cart;
```

### Navbar Component - `components/Navbar.jsx`

```javascript
import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Auth } from 'aws-amplify';

function Navbar({ user, onLogout }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await Auth.signOut();
      onLogout();
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <nav className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <Link to="/products" className="text-2xl font-bold hover:opacity-80">
          🛍️ E-Com67
        </Link>
        
        <div className="flex gap-6 items-center">
          <Link to="/products" className="hover:underline transition">
            Products
          </Link>
          <Link to="/cart" className="hover:underline transition">
            Cart
          </Link>
          <Link to="/orders" className="hover:underline transition">
            Orders
          </Link>
          
          <div className="border-l border-white pl-4 flex items-center gap-4">
            <span className="text-sm">{user?.attributes?.email}</span>
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-600 px-4 py-2 rounded transition"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
```

### Frontend Installation & Running

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local with CDK outputs
cat > .env.local << EOF
REACT_APP_API_ENDPOINT=your-api-endpoint-from-cdk
REACT_APP_USER_POOL_ID=your-user-pool-id
REACT_APP_USER_POOL_CLIENT_ID=your-client-id
EOF

# Start development server
npm start
```

---

---

## Testing Checklist

### Unit Tests
- [ ] Test Lambda CRUD operations with mocked DynamoDB
- [ ] Test payment handler with mocked Stripe API
- [ ] Test cart operations (add, remove, calculate total)
- [ ] Test order validation logic
- [ ] Test Bedrock integration with mocked responses

### Integration Tests (Postman)
- [ ] POST /products (create product)
- [ ] GET /products (list products)
- [ ] GET /products/{id} (get product)
- [ ] GET /search?q=laptop (search products)
- [ ] POST /cart (add to cart)
- [ ] GET /cart (get cart items)
- [ ] POST /orders (place order)
- [ ] GET /orders (order history)

### E2E Tests
- [ ] User signup/login flow
- [ ] Browse and search products
- [ ] Add items to cart
- [ ] Complete checkout with Stripe test card
- [ ] Receive order confirmation email
- [ ] Chat with AI bot via WebSocket

---

## Deployment Steps

### Backend Deployment (CDK)

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set environment variables
export AWS_ACCOUNT_ID=your-account-id
export AWS_REGION=us-east-1

# 5. Bootstrap CDK (first time only)
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# 6. Synthesize CloudFormation template
cdk synth

# 7. Review and deploy stack
cdk deploy

# 8. Get CDK outputs (save these for frontend)
aws cloudformation describe-stacks \
    --stack-name e-com67Stack \
    --query "Stacks[0].Outputs"
```

### Frontend Deployment (React)

```bash
# 1. Navigate to frontend
cd ../frontend

# 2. Install Node dependencies
npm install

# 3. Create .env.local with CDK outputs
cat > .env.local << EOF
REACT_APP_API_ENDPOINT=https://xxx.execute-api.us-east-1.amazonaws.com/prod
REACT_APP_USER_POOL_ID=us-east-1_xxxxx
REACT_APP_USER_POOL_CLIENT_ID=xxxxx
EOF

# 4. Test development server
npm start

# 5. Build for production
npm run build

# 6. Deploy to S3 (get bucket name from CDK outputs)
aws s3 sync build/ s3://e-com67-frontend-YOUR-ACCOUNT-ID --delete
```

### Complete Deployment Workflow

```bash
#!/bin/bash

# Backend deployment
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
cdk deploy --require-approval never

# Save outputs
aws cloudformation describe-stacks \
    --stack-name e-com67Stack \
    --query "Stacks[0].Outputs" > outputs.json

# Extract values
ENDPOINT=$(jq -r '.[] | select(.OutputKey=="ApiEndpoint") | .OutputValue' outputs.json)
USER_POOL=$(jq -r '.[] | select(.OutputKey=="UserPoolId") | .OutputValue' outputs.json)
CLIENT_ID=$(jq -r '.[] | select(.OutputKey=="UserPoolClientId") | .OutputValue' outputs.json)

# Frontend deployment
cd ../frontend
cat > .env.local << EOF
REACT_APP_API_ENDPOINT=$ENDPOINT
REACT_APP_USER_POOL_ID=$USER_POOL
REACT_APP_USER_POOL_CLIENT_ID=$CLIENT_ID
EOF

npm install
npm run build

# Deploy to S3
BUCKET=$(jq -r '.[] | select(.OutputKey=="FrontendBucketName") | .OutputValue' ../backend/outputs.json)
aws s3 sync build/ s3://$BUCKET --delete

echo "Deployment complete!"
echo "Frontend: https://$BUCKET.s3.us-east-1.amazonaws.com"
```

---

## Cost Optimization Tips

1. **DynamoDB**: Use on-demand billing for unpredictable traffic
2. **OpenSearch**: Use t3.small instance for dev (can pause when not in use)
3. **Lambda**: Set appropriate memory/timeout to avoid over-provisioning
4. **S3**: Enable lifecycle policies to archive old reports
5. **CloudWatch**: Set log retention to 7 days for dev environment
6. **API Gateway**: Monitor usage; throttle if needed
7. **Cognito**: Use free tier; upgrade only if needed

---

## Next Steps

1. **Phase 1 - Foundation**
   - Deploy DynamoDB tables
   - Create Cognito User Pool
   - Setup API Gateway and basic Lambda functions

2. **Phase 2 - Core Features**
   - Implement Product CRUD operations
   - Build Cart functionality
   - Create Order processing workflow

3. **Phase 3 - Advanced Features**
   - Add payment processing (Stripe)
   - Implement OpenSearch for product search
   - Add email notifications (SES)

4. **Phase 4 - AI & Polish**
   - Add Bedrock chat integration
   - Implement WebSocket for real-time chat
   - Setup monitoring and alarms

5. **Phase 5 - Production Readiness**
   - Set up CI/CD pipeline (CodePipeline + CodeBuild)
   - Add comprehensive testing
   - Configure auto-scaling policies
   - Setup CDN for frontend (CloudFront)

---

## Monorepo Structure

This project uses a monorepo structure for easier management:

```
e-com67/
├── backend/              # AWS CDK infrastructure
├── frontend/             # React application
├── shared/               # Shared code and constants
├── docs/                 # Documentation
├── README.md             # Project overview
└── .gitignore           # Git ignore rules
```

Each directory can be developed and tested independently while sharing common utilities through the `/shared` folder.
5. Implement CI/CD last (CodePipeline + CodeBuild)

Good luck with your AWS training project! 🚀