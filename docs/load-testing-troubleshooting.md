# Load Testing Troubleshooting Guide

Quick reference for diagnosing and fixing common load testing issues.

---

## Issue: High Response Times

### Symptoms
- Average response time > 500ms
- p95 > 1000ms
- Response times increase during hold period

### Diagnostic Steps

1. **Check Lambda Performance**
   ```bash
   # View Lambda metrics in CloudWatch
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value={function-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Average,Maximum
   ```

2. **Check for Cold Starts**
   ```bash
   # Count cold start invocations
   aws logs filter-log-events \
     --log-group-name /aws/lambda/{function-name} \
     --filter-pattern "REPORT" \
     --start-time {timestamp}
   ```

3. **Review DynamoDB Throttling**
   ```bash
   # Check for throttled requests
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name UserErrors \
     --dimensions Name=TableName,Value={table-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Sum
   ```

### Common Causes & Solutions

| Cause | Solution |
|-------|----------|
| **Lambda Cold Starts** | Enable provisioned concurrency (5-10 instances) |
| **Insufficient Lambda Memory** | Increase from 128MB to 512MB or 1024MB |
| **DynamoDB Throttling** | Enable auto-scaling or increase provisioned capacity |
| **Database Connection Pool Exhaustion** | Increase max connections or use RDS Proxy |
| **Inefficient Queries** | Add DynamoDB GSIs, optimize query patterns |
| **Large Response Payloads** | Implement pagination, reduce payload size |
| **External API Calls** | Add caching, implement circuit breakers |

### Quick Fixes

**Enable Lambda Provisioned Concurrency:**
```python
# In your CDK stack
lambda_function.add_alias(
    "prod",
    provisioned_concurrent_executions=10
)
```

**Increase Lambda Memory:**
```python
lambda_function = _lambda.Function(
    self, "MyFunction",
    memory_size=1024,  # Increased from 128
    # ... other config
)
```

**Enable DynamoDB Auto-Scaling:**
```python
table.auto_scale_read_capacity(
    min_capacity=5,
    max_capacity=100
).scale_on_utilization(target_utilization_percent=70)
```

---

## Issue: High Error Rates

### Symptoms
- Error rate > 5%
- Many 500, 502, or 503 status codes
- Inconsistent success rates

### Diagnostic Steps

1. **Check CloudWatch Logs**
   ```bash
   # View recent errors
   aws logs tail /aws/lambda/{function-name} \
     --follow \
     --filter-pattern "ERROR"
   ```

2. **Review API Gateway Errors**
   ```bash
   # Check API Gateway 5XX errors
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ApiGateway \
     --metric-name 5XXError \
     --dimensions Name=ApiName,Value={api-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Sum
   ```

3. **Check Lambda Errors**
   ```bash
   # View Lambda error metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Errors \
     --dimensions Name=FunctionName,Value={function-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Sum
   ```

### Common Causes & Solutions

| Error Type | Cause | Solution |
|------------|-------|----------|
| **500 Internal Server Error** | Unhandled exceptions | Add try-catch blocks, improve error handling |
| **502 Bad Gateway** | Lambda timeout | Increase Lambda timeout (default 3s → 30s) |
| **503 Service Unavailable** | Lambda throttling | Increase concurrent execution limit |
| **504 Gateway Timeout** | API Gateway timeout | Increase API Gateway timeout (max 29s) |
| **Connection Errors** | Network issues | Check VPC configuration, security groups |
| **Validation Errors** | Invalid request data | Improve input validation, add request schemas |

### Quick Fixes

**Increase Lambda Timeout:**
```python
lambda_function = _lambda.Function(
    self, "MyFunction",
    timeout=Duration.seconds(30),  # Increased from 3
    # ... other config
)
```

**Add Error Handling:**
```python
def lambda_handler(event, context):
    try:
        # Your code here
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except ValidationError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

**Increase Concurrent Execution Limit:**
```bash
# Request limit increase via AWS Support
# Or set reserved concurrency
aws lambda put-function-concurrency \
  --function-name {function-name} \
  --reserved-concurrent-executions 100
```

---

## Issue: Rate Limiting (429 Errors)

### Symptoms
- 429 Too Many Requests errors
- Throttling messages in logs
- Success rate drops under high load

### Diagnostic Steps

1. **Check API Gateway Throttling**
   ```bash
   # View throttle count
   aws apigateway get-usage-plans
   ```

2. **Check Lambda Throttles**
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Throttles \
     --dimensions Name=FunctionName,Value={function-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Sum
   ```

3. **Check DynamoDB Throttling**
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name ThrottledRequests \
     --dimensions Name=TableName,Value={table-name} \
     --start-time {start} --end-time {end} \
     --period 60 --statistics Sum
   ```

### Common Causes & Solutions

| Service | Default Limit | Solution |
|---------|---------------|----------|
| **API Gateway** | 10,000 RPS (burst: 5,000) | Increase throttle limits in usage plan |
| **Lambda** | 1,000 concurrent executions | Request limit increase via AWS Support |
| **DynamoDB** | Provisioned capacity | Enable auto-scaling or on-demand mode |

### Quick Fixes

**Increase API Gateway Limits:**
```python
# In CDK
usage_plan = api.add_usage_plan(
    "UsagePlan",
    throttle=apigw.ThrottleSettings(
        rate_limit=10000,  # Requests per second
        burst_limit=5000   # Burst capacity
    )
)
```

**Enable DynamoDB On-Demand:**
```python
table = dynamodb.Table(
    self, "MyTable",
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    # ... other config
)
```

**Request Lambda Concurrency Increase:**
1. Go to AWS Support Center
2. Create case: "Service Limit Increase"
3. Select: Lambda → Concurrent executions
4. Request new limit (e.g., 5,000)

---

## Issue: Container Resource Limits

### Symptoms
- CPU usage > 75%
- Memory usage > 85%
- Inconsistent test results
- Lower than expected RPS

### Diagnostic Steps

1. **Check Container Metrics**
   - Open CloudWatch Console
   - Navigate to Container Insights → Performance Monitoring
   - Select ECS Clusters → Your DLT cluster
   - Review CPU and Memory graphs

2. **Review Task Configuration**
   ```bash
   # Get task definition
   aws ecs describe-task-definition \
     --task-definition {task-definition-name}
   ```

### Solutions

**Option 1: Reduce Load per Container**
```
Current: 10 tasks × 200 users = 2,000 users
Adjusted: 20 tasks × 100 users = 2,000 users

Result: Same total load, lower per-container resource usage
```

**Option 2: Increase Container Resources**

Request quota increase:
1. Go to Service Quotas console
2. Select: Amazon ECS → Fargate vCPUs
3. Request increase from 2 vCPU to 4 vCPU per task

**Option 3: Optimize Test Script**
- Reduce unnecessary logging
- Minimize data processing in test script
- Use more efficient assertions

---

## Issue: Test Won't Start

### Symptoms
- Test stuck in "Pending" status
- No containers launching
- Error messages in DLT console

### Diagnostic Steps

1. **Check ECS Cluster**
   ```bash
   # List running tasks
   aws ecs list-tasks \
     --cluster {dlt-cluster-name} \
     --region ap-southeast-1
   ```

2. **Check CloudWatch Logs**
   ```bash
   # View DLT API logs
   aws logs tail /aws/lambda/dlt-api-services \
     --follow
   ```

3. **Check IAM Permissions**
   ```bash
   # Verify ECS task execution role
   aws iam get-role --role-name {ecs-task-role}
   ```

### Common Causes & Solutions

| Cause | Solution |
|-------|----------|
| **Insufficient Fargate Capacity** | Reduce task count or request quota increase |
| **IAM Permission Issues** | Verify ECS task role has required permissions |
| **VPC/Subnet Issues** | Ensure subnets have available IP addresses |
| **Security Group Issues** | Verify outbound rules allow HTTPS (443) |
| **Invalid Test Configuration** | Review test scenario for errors |

---

## Issue: Inaccurate Results

### Symptoms
- Results don't match expectations
- Inconsistent metrics between runs
- Unexpected RPS values

### Diagnostic Steps

1. **Verify Test Configuration**
   - Check task count and concurrency
   - Verify ramp-up and hold duration
   - Confirm endpoint URL is correct

2. **Check for Concurrent Tests**
   ```bash
   # List all running tasks
   aws ecs list-tasks \
     --cluster {dlt-cluster-name} \
     --desired-status RUNNING
   ```

3. **Review Test Artifacts**
   - Download results.xml from S3
   - Check for anomalies in raw data
   - Verify request/response patterns

### Common Causes & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **Lower than expected RPS** | Endpoint response time too slow | Optimize backend performance |
| **Inconsistent results** | Multiple tests running simultaneously | Run one test at a time |
| **Unexpected errors** | Wrong endpoint URL | Verify URL in test configuration |
| **Missing data** | Results parsing failed | Check S3 for raw results files |

---

## Issue: Authentication Failures

### Symptoms
- 401 Unauthorized errors
- 403 Forbidden errors
- High error rate for authenticated endpoints

### Diagnostic Steps

1. **Verify Token**
   ```bash
   # Test token manually
   curl -H "Authorization: Bearer {token}" \
     https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/cart
   ```

2. **Check Token Expiration**
   ```bash
   # Decode JWT token (use jwt.io or jwt-cli)
   echo {token} | jwt decode -
   ```

3. **Verify Cognito Configuration**
   ```bash
   # Get user pool details
   aws cognito-idp describe-user-pool \
     --user-pool-id {pool-id}
   ```

### Solutions

**Token Expired:**
- Cognito tokens expire after 1 hour by default
- For tests > 1 hour, use refresh tokens
- Or create custom test script with token refresh logic

**Wrong Token Type:**
- Use IdToken (not AccessToken) for API Gateway authorization
- Verify token includes required claims

**Insufficient Permissions:**
- Verify user is in correct Cognito group
- Check API Gateway authorizer configuration

---

## Issue: Cost Concerns

### Symptoms
- Unexpectedly high AWS bill
- Costs increasing with each test
- Need to optimize testing costs

### Cost Optimization Strategies

1. **Reduce Test Duration**
   ```
   Instead of: 10 minutes hold time
   Use: 5 minutes hold time
   Savings: 50% reduction in Fargate costs
   ```

2. **Test During Off-Peak Hours**
   - Lower risk of impacting production
   - Easier to isolate issues
   - Same results, lower business impact

3. **Use Smaller Initial Tests**
   ```
   Start: 100 users for 5 minutes
   Then: 500 users for 5 minutes
   Finally: 2,000 users for 5 minutes
   
   Instead of: 2,000 users for 30 minutes
   ```

4. **Clean Up Test Data**
   - Delete old test results from S3
   - Remove unused test scenarios
   - Archive historical data to Glacier

5. **Monitor Costs**
   ```bash
   # Check current month costs
   aws ce get-cost-and-usage \
     --time-period Start=2024-01-01,End=2024-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost \
     --filter file://filter.json
   ```

### Estimated Costs

**Per Test:**
```
10 tasks × 2 vCPU × 10 minutes = 3.33 vCPU-hours
Cost: 3.33 × $0.04 = ~$0.13 per test
```

**Monthly (Daily Testing):**
```
1 test/day × 30 days = 30 tests
Cost: 30 × $0.13 = ~$3.90/month
```

---

## Quick Reference: Diagnostic Commands

### Get API Endpoint
```bash
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

### Test Endpoint Manually
```bash
curl -X GET \
  -H "Content-Type: application/json" \
  https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/{function-name} --follow
```

### Check DynamoDB Capacity
```bash
aws dynamodb describe-table \
  --table-name {table-name} \
  --query 'Table.ProvisionedThroughput'
```

### List Running ECS Tasks
```bash
aws ecs list-tasks \
  --cluster {dlt-cluster-name} \
  --desired-status RUNNING
```

### Download Test Results from S3
```bash
aws s3 cp \
  s3://dlt-results-bucket/scenario-{id}/test-run-{id}/ \
  ./test-results/ \
  --recursive
```

---

## Getting Help

### AWS Support

**For DLT Solution Issues:**
1. Check [AWS Solutions Library](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
2. Review [GitHub Issues](https://github.com/aws-solutions/distributed-load-testing-on-aws/issues)
3. Contact AWS Support (if you have a support plan)

**For Service Limit Increases:**
1. Go to AWS Support Center
2. Create case: "Service Limit Increase"
3. Specify service and desired limit

### Internal Resources

- **DevOps Team:** [contact info]
- **Platform Team:** [contact info]
- **On-Call Engineer:** [contact info]

### Documentation

- [Load Testing Guide](./load-testing-guide.md)
- [Quick Start Guide](./load-testing-quick-start.md)
- [API Endpoints](./api-endpoints.md)
- [AWS DLT Documentation](https://docs.aws.amazon.com/solutions/latest/distributed-load-testing-on-aws/)

---

## Troubleshooting Checklist

Before asking for help, verify:

- [ ] Test configuration is correct (endpoint URL, method, headers)
- [ ] API endpoint is accessible (test manually with curl)
- [ ] Authentication token is valid (if required)
- [ ] No other tests are running concurrently
- [ ] CloudWatch Logs reviewed for errors
- [ ] Resource limits not exceeded (CPU, memory, throttles)
- [ ] Test artifacts downloaded and reviewed
- [ ] Issue is reproducible (run test again)

---

*Last Updated: [Date]*  
*For questions or updates, contact: [your-email@example.com]*
