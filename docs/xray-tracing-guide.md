# AWS X-Ray Tracing Guide for E-Com67

## Overview

X-Ray tracing has been enabled across the entire E-Com67 serverless stack to provide end-to-end visibility into request flows, performance bottlenecks, and errors.

---

## ✅ What's Been Enabled

### 1. **All Lambda Functions** - Active Tracing
- ✅ Product CRUD Function
- ✅ Cart Function
- ✅ Payment Function
- ✅ Order Processor Function

**Configuration**: `tracing=lambda_.Tracing.ACTIVE`

### 2. **API Gateway** - Stage Tracing
- ✅ REST API endpoint tracing enabled
- All API requests will be traced end-to-end

**Configuration**: `deploy_options=apigw.StageOptions(tracing_enabled=True)`

### 3. **DynamoDB Tables** - Contributor Insights
- ✅ Users Table
- ✅ Products Table
- ✅ Orders Table
- ✅ Cart Table
- ✅ Chat History Table

**Configuration**: `contributor_insights_enabled=True`

### 4. **SQS Queue** - Message Tracing
- ✅ Order Queue
- Messages are traced as they flow through the queue

### 5. **Step Functions** - Workflow Tracing
- ✅ Checkout State Machine
- Complete workflow execution tracing

**Configuration**: `tracing_enabled=True`

### 6. **IAM Permissions**
- ✅ Automatically granted by CDK when `tracing=ACTIVE` is set
- Includes:
  - `xray:PutTraceSegments`
  - `xray:PutTelemetryRecords`

---

## 📦 X-Ray SDK Installation

The X-Ray SDK has been added to your project:

### Backend (CDK)
```bash
# Already in requirements.txt
aws-xray-sdk==2.12.1
```

### Lambda Layer (Optional)
```bash
# Created at: backend/lambda/layers/xray_layer/python/requirements.txt
cd backend/lambda/layers/xray_layer/python
pip install -r requirements.txt -t .
```

---

## 🚀 Using X-Ray in Lambda Functions

### Basic Setup

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3

# Automatically instrument AWS SDK calls
patch_all()

# Initialize AWS clients (will be auto-traced)
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    # Your code here - AWS SDK calls are automatically traced
    table = dynamodb.Table('e-com67-products')
    response = table.get_item(Key={'productId': '123'})
    return response
```

### Custom Subsegments

```python
# Trace specific business logic
with xray_recorder.capture('validate_cart') as subsegment:
    # Add annotations (for filtering in X-Ray console)
    subsegment.put_annotation('user_id', user_id)
    subsegment.put_annotation('cart_size', len(items))
    
    # Add metadata (for debugging)
    subsegment.put_metadata('cart_items', items)
    
    # Your validation logic
    is_valid = validate_cart_items(items)
    subsegment.put_metadata('validation_result', is_valid)
```

### Example Use Cases

#### 1. **Tracing DynamoDB Operations**
```python
# Automatic - no code changes needed
table.query(KeyConditionExpression=Key('userId').eq(user_id))
# ✅ This appears automatically in X-Ray traces
```

#### 2. **Tracing External API Calls**
```python
with xray_recorder.capture('stripe_payment') as subsegment:
    subsegment.put_annotation('payment_amount', amount)
    subsegment.put_annotation('currency', 'USD')
    
    response = stripe.Charge.create(
        amount=amount,
        currency='usd',
        source=token
    )
    
    subsegment.put_metadata('charge_id', response.id)
```

#### 3. **Tracing Business Logic**
```python
with xray_recorder.capture('calculate_shipping') as subsegment:
    subsegment.put_annotation('shipping_country', country)
    
    shipping_cost = calculate_shipping_cost(items, country)
    
    subsegment.put_metadata('shipping_cost', shipping_cost)
    subsegment.put_metadata('item_count', len(items))
```

---

## 📊 Viewing X-Ray Traces

### 1. **AWS Console**
Navigate to: **AWS X-Ray Console** → **Service Map / Traces**

### 2. **Service Map**
- Visual representation of your entire architecture
- Shows service dependencies and request flow
- Highlights errors and latency issues

### 3. **Traces**
- Individual request traces
- End-to-end view: API Gateway → Lambda → DynamoDB
- Filter by:
  - Response time
  - HTTP status codes
  - Annotations (custom filters)

### 4. **Analytics**
- Query traces using filter expressions
- Example: Find all failed payment attempts
  ```
  annotation.user_id = "user123" AND http.status = 500
  ```

---

## 🔍 Key X-Ray Concepts

### **Segments**
- Top-level trace units
- Automatically created for each Lambda invocation
- Contains timing, status, and metadata

### **Subsegments**
- Nested units within a segment
- Track specific operations (DB calls, API calls, business logic)
- Created using `xray_recorder.capture('name')`

### **Annotations** ⭐ Important!
- **Key-value pairs for FILTERING** traces
- Indexed and searchable in X-Ray console
- Limited to: strings, numbers, booleans
- **Use for**: user_id, product_id, order_status, payment_method

```python
subsegment.put_annotation('user_type', 'premium')  # ✅ Searchable
subsegment.put_annotation('order_total', 99.99)     # ✅ Searchable
```

### **Metadata**
- Additional debugging information (NOT indexed)
- Can be complex objects (lists, dicts)
- **Use for**: full request/response payloads, stack traces

```python
subsegment.put_metadata('full_cart', cart_items)  # ✅ For debugging
```

---

## 🎯 Best Practices

### 1. **Use Annotations Strategically**
```python
# ✅ Good - Filterable business metrics
subsegment.put_annotation('user_id', user_id)
subsegment.put_annotation('product_category', category)
subsegment.put_annotation('payment_status', 'success')

# ❌ Avoid - Not useful for filtering
subsegment.put_annotation('random_uuid', uuid.uuid4())
```

### 2. **Meaningful Subsegment Names**
```python
# ✅ Good
with xray_recorder.capture('stripe_payment_authorization'):
    ...

# ❌ Avoid
with xray_recorder.capture('step1'):
    ...
```

### 3. **Don't Over-Segment**
- Create subsegments for **expensive or critical operations**
- Avoid creating hundreds of subsegments per request
- Each subsegment adds overhead

### 4. **Capture Errors Properly**
```python
try:
    process_payment()
except Exception as e:
    # Error is automatically captured by X-Ray
    xray_recorder.current_subsegment().put_annotation('error_type', type(e).__name__)
    raise  # Re-raise to propagate
```

---

## 🔧 Deployment

After enabling X-Ray, deploy your stack:

```bash
cd backend

# Synthesize to see changes
cdk synth

# Deploy with X-Ray tracing enabled
cdk deploy
```

---

## 📈 Monitoring & Alerting

### CloudWatch Integration
- X-Ray metrics are available in CloudWatch
- Create alarms based on:
  - Error rates
  - Response times (p50, p90, p99)
  - Trace counts

### Example Alarm
```python
# In your CDK stack (already exists for payment function)
self.payment_fn.metric_errors().create_alarm(
    self, "PaymentErrorAlarm",
    threshold=5,
    evaluation_periods=1,
    alarm_description="Payment function errors"
)
```

---

## 🧪 Testing X-Ray Locally

### SAM CLI (Optional)
```bash
# Run Lambda locally with X-Ray
sam local invoke ProductCrudFunction \
  --event events/get-product.json \
  --docker-network sam-local

# View traces at http://localhost:2000
```

---

## 📚 Common Trace Patterns

### 1. **E-Commerce Checkout Flow**
```
API Gateway
  └─ Checkout Lambda
      ├─ Validate Cart (subsegment)
      │   └─ DynamoDB: Get Cart Items
      ├─ Process Payment (subsegment)
      │   └─ Stripe API Call
      └─ Send to SQS (subsegment)
          └─ Order Queue Message
```

### 2. **Product Search Flow**
```
API Gateway
  └─ Search Lambda
      ├─ OpenSearch Query (subsegment)
      └─ DynamoDB: Get Product Details
          └─ Batch Get Items
```

---

## 🐛 Troubleshooting

### Issue: Traces Not Appearing
**Solution:**
1. Verify Lambda has X-Ray permissions (auto-granted by CDK)
2. Check that `tracing=ACTIVE` is set
3. Ensure SDK is imported: `from aws_xray_sdk.core import xray_recorder`
4. Wait a few minutes for traces to propagate

### Issue: Missing AWS SDK Calls in Traces
**Solution:**
```python
# Add at the top of your Lambda handler
from aws_xray_sdk.core import patch_all
patch_all()  # Must be called before importing boto3
import boto3
```

### Issue: Subsegments Not Showing
**Solution:**
```python
# Ensure context manager is used correctly
with xray_recorder.capture('operation_name'):
    # Your code here
    pass
```

---

## 📖 Additional Resources

- **AWS X-Ray Documentation**: https://docs.aws.amazon.com/xray/
- **X-Ray SDK for Python**: https://docs.aws.amazon.com/xray-sdk-for-python/
- **X-Ray Sample App**: https://github.com/aws-samples/aws-xray-sdk-python-sample
- **Example Lambda**: `backend/lambda/XRAY_EXAMPLE.py`

---

## 🎉 Summary

✅ **X-Ray Active tracing** enabled on all Lambda functions  
✅ **API Gateway tracing** enabled on REST API  
✅ **DynamoDB Contributor Insights** enabled on all tables  
✅ **SQS tracing** enabled on Order Queue  
✅ **Step Functions tracing** enabled on Checkout workflow  
✅ **X-Ray SDK** added to requirements  
✅ **IAM permissions** automatically granted  
✅ **Example code** provided in `XRAY_EXAMPLE.py`  

**Next Steps:**
1. Deploy the stack: `cdk deploy`
2. Generate some traffic to your API
3. View traces in AWS X-Ray console
4. Add custom subsegments to your Lambda functions
5. Create X-Ray dashboards and alarms

---

Happy tracing! 🚀
