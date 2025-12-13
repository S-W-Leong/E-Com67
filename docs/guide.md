# 🛍️ AWS Serverless E-commerce - Implementation Guide

## 📋 Table of Contents
1. [Architecture Summary](#architecture-summary)
2. [CDK Stack Structure](#cdk-stack-structure)
3. [Lambda Functions](#lambda-functions)
4. [API Endpoints](#api-endpoints)
5. [Frontend Pages](#frontend-pages)
6. [Deployment Steps](#deployment-steps)
7. [Testing Checklist](#testing-checklist)

---

## Architecture Summary

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

## Frontend Structure

### React Pages

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.jsx           # Cognito authentication
│   │   ├── Products.jsx        # Product listing with search
│   │   ├── ProductDetail.jsx   # Single product view
│   │   ├── Cart.jsx            # Shopping cart
│   │   ├── Checkout.jsx        # Payment with Stripe
│   │   └── Orders.jsx          # Order history
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── ProductCard.jsx
│   │   ├── ChatWidget.jsx      # WebSocket chat
│   │   └── SearchBar.jsx
│   ├── services/
│   │   ├── api.js              # API calls
│   │   ├── auth.js             # Cognito integration
│   │   └── websocket.js        # WebSocket connection
│   └── App.js
```

### Sample React Component (Products.jsx)
```javascript
import React, { useState, useEffect } from 'react';
import { searchProducts, listProducts } from '../services/api';
import ProductCard from '../components/ProductCard';
import SearchBar from '../components/SearchBar';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async (category = null) => {
    setLoading(true);
    try {
      const data = await listProducts(category);
      setProducts(data);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
    setLoading(false);
  };

  const handleSearch = async (query) => {
    if (!query) {
      loadProducts();
      return;
    }
    
    setLoading(true);
    try {
      const results = await searchProducts(query);
      setProducts(results);
    } catch (error) {
      console.error('Search failed:', error);
    }
    setLoading(false);
  };

  return (
    <div className="container mx-auto p-4">
      <SearchBar onSearch={handleSearch} />
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {products.map(product => (
          <ProductCard key={product.productId} product={product} />
        ))}
      </div>
    </div>
  );
}

export default Products;
```

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

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export AWS_ACCOUNT_ID=your-account-id
export AWS_REGION=us-east-1
export STRIPE_API_KEY=your-stripe-test-key

# 3. Bootstrap CDK (first time only)
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# 4. Synthesize CloudFormation template
cdk synth

# 5. Deploy stack
cdk deploy --all

# 6. Get outputs
aws cloudformation describe-stacks \
    --stack-name e-com67Stack \
    --query "Stacks[0].Outputs"

# 7. Deploy frontend
cd frontend
npm install
npm run build
aws s3 sync build/ s3://your-frontend-bucket
```

---

## Cost Optimization Tips

1. **DynamoDB**: Use on-demand billing for unpredictable traffic
2. **OpenSearch**: Use t3.small instance for dev (can pause when not in use)
3. **Lambda**: Set appropriate memory/timeout to avoid over-provisioning
4. **S3**: Enable lifecycle policies to archive old reports
5. **CloudWatch**: Set log retention to 7 days for dev environment

---

## Next Steps

1. Start with Phase 1 (Foundation) - DynamoDB, Cognito, basic Lambda
2. Test each service individually before integration
3. Document API endpoints as you build
4. Create architecture diagram using draw.io or Lucidchart
5. Implement CI/CD last (CodePipeline + CodeBuild)

Good luck with your AWS training project! 🚀