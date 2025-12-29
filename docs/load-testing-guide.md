# Load Testing Guide for E-Com67 Platform

This guide walks you through setting up and running load tests for the E-Com67 platform using AWS Distributed Load Testing (DLT) solution.

## Prerequisites

Before starting, ensure you have:
- AWS Distributed Load Testing solution deployed in your AWS account
- Access to the DLT web console
- Your API Gateway endpoint URL (from CloudFormation outputs)
- Valid Cognito authentication tokens (if testing authenticated endpoints)

## Overview

The AWS Distributed Load Testing solution uses:
- **Amazon ECS Fargate** to run load testing containers
- **Taurus** as the testing framework (wraps JMeter, K6, Locust)
- **CloudWatch** for real-time monitoring
- **S3** for storing test results and artifacts

## Step 1: Access the DLT Console

1. Navigate to the DLT console URL (provided during solution deployment)
2. Sign in with your Cognito credentials
3. You'll see the main dashboard with existing test scenarios (if any)

## Step 2: Choose an API Endpoint to Test

For your first load test, we recommend starting with a **public endpoint** that doesn't require authentication:

### Recommended Starting Point: GET /products

**Why this endpoint?**
- No authentication required (simpler setup)
- Read-only operation (safe to test)
- Represents a common user action
- Good baseline for performance expectations

**Endpoint Details:**
- URL: `https://{your-api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products`
- Method: GET
- Query Parameters (optional): `category`, `limit`, `offset`

### Alternative Endpoints for Testing

**Public Endpoints (No Auth):**
- `GET /products/{id}` - Single product lookup
- `GET /search?q={query}` - Product search

**Authenticated Endpoints (Requires Cognito Token):**
- `GET /cart` - User's shopping cart
- `GET /orders` - User's order history
- `POST /cart` - Add items to cart

## Step 3: Create Your First Test Scenario

### 3.1 General Settings

1. Click **Create Test** in the DLT console
2. Configure general settings:

```
Test Name: E-Com67 Products List - Baseline
Test Description: Load test for GET /products endpoint to establish baseline performance metrics
Tags (optional):
  - Environment: Production
  - API: Products
  - Type: Baseline
```

3. **Scheduling Options:**
   - Select **Run Now** for immediate execution
   - (Later, you can use **Run on a Schedule** for regular performance monitoring)

4. **Live Data:**
   - ✅ Check **Include live data** to monitor real-time metrics during the test

### 3.2 Scenario Configuration

1. **Test Type:** Select **Single HTTP Endpoint**

2. **HTTP Endpoint Configuration:**

```
HTTP Endpoint: https://{your-api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
HTTP Method: GET
```

3. **Request Headers** (Optional - click "Add Header" if needed):
   - For public endpoints, no headers required
   - For authenticated endpoints, add:
     ```
     Authorization: Bearer {your-cognito-jwt-token}
     ```

4. **Body Payload:** Leave empty for GET requests

### 3.3 Traffic Shape Configuration

This is where you define the load pattern. Start conservatively and increase gradually.

#### Recommended Starting Configuration

**Region Selection:**
- Select **ap-southeast-1** (Singapore) - matches your deployment region

**For Each Region:**

```
Task Count: 2
  - Each task is a Fargate container
  - Start with 2 tasks for initial testing
  
Concurrency: 50
  - Virtual users per task
  - Total users = Task Count × Concurrency = 2 × 50 = 100 users
  
Ramp Up: 60 seconds
  - Gradually increase from 0 to 100 users over 1 minute
  - Prevents sudden traffic spikes
  
Hold For: 300 seconds (5 minutes)
  - Maintain 100 concurrent users for 5 minutes
  - Provides stable performance data
```

**Total Test Duration:** 6 minutes (1 min ramp-up + 5 min hold)

#### Understanding the Numbers

**Task Count × Concurrency = Total Virtual Users**
- 2 tasks × 50 users = 100 concurrent users
- Each user continuously makes requests during the test

**Expected Request Volume:**
- If each user makes 1 request per second: ~100 RPS
- Over 5 minutes: ~30,000 total requests

#### Scaling Up (After Baseline)

Once you've established baseline performance, you can increase load:

```
Light Load:    2 tasks × 50 users = 100 users
Medium Load:   5 tasks × 100 users = 500 users
Heavy Load:    10 tasks × 200 users = 2,000 users
Stress Test:   20 tasks × 250 users = 5,000 users
```

**Important:** Monitor CPU and memory in CloudWatch Container Insights to ensure you're not exceeding container capacity.

### 3.4 Review and Create

1. Review all configurations:
   - General settings
   - Endpoint configuration
   - Traffic shape
   
2. Click **Create** to save the test scenario

3. The test will start immediately (if "Run Now" was selected)

## Step 4: Monitor the Test Run

### Real-Time Monitoring (Live Data)

If you enabled "Include live data", you'll see real-time charts showing:

1. **Average Response Time** - How quickly your API responds
2. **Virtual Users** - Current number of simulated users
3. **Success Count** - Number of successful requests
4. **Error Count** - Number of failed requests

**What to Watch For:**
- Response times should remain stable during the hold period
- Error count should be zero or very low
- Success rate should be close to 100%

### CloudWatch Container Insights

Monitor resource utilization:

1. Open CloudWatch Console
2. Navigate to **Container Insights** → **Performance Monitoring**
3. Select **ECS Clusters** → Your DLT cluster
4. Watch CPU and Memory metrics:
   - CPU should stay below 75%
   - Memory should stay below 85%
   - If exceeded, reduce concurrency or increase task resources

## Step 5: Analyze Test Results

### Wait for Results Processing

After the test completes:
1. The solution automatically processes results (takes 1-2 minutes)
2. You'll see "Parsing" status change to "Complete"
3. Click on the test run to view detailed results

### Key Metrics to Review

#### Summary Metrics

```
Average Response Time: Target < 200ms for good performance
Average Latency: Should be minimal
Total Count: Total requests made
Success Count: Should match total count (or close)
Error Count: Should be 0 or very low (< 1%)
Requests per Second: Actual throughput achieved
```

#### Percentiles (Response Time Distribution)

```
p50 (Median): 50% of requests faster than this
p90: 90% of requests faster than this
p95: 95% of requests faster than this
p99: 99% of requests faster than this
```

**Example Good Results:**
```
p50: 50ms
p90: 100ms
p95: 150ms
p99: 300ms
```

**What This Means:**
- Most users (50%) experience 50ms response time
- 90% of users get responses under 100ms
- Only 1% of users experience > 300ms

### View Results by Dimension

Toggle between views:
- **Overall** - Aggregated across all endpoints and regions
- **By Endpoint** - Breakdown per endpoint (useful for multi-endpoint tests)
- **By Region** - Breakdown per AWS region (useful for multi-region tests)

### Check for Errors

1. Click the **Errors** tab
2. Review any error types and counts
3. Common errors to investigate:
   - 500 errors: Backend issues
   - 429 errors: Rate limiting triggered
   - Timeout errors: Performance issues

### Download Artifacts

1. Click the **Artifacts** tab
2. Available files:
   - `results.xml` - Detailed test results
   - `kpi.jtl` - Performance metrics
   - `error.jtl` - Error details
   - Container logs
3. Download for offline analysis or sharing with team

## Step 6: Set a Baseline

After your first successful test:

1. In the test runs table, find your test run
2. Click **Set as Baseline**
3. Future test runs will show percentage differences compared to this baseline

**Why Set a Baseline?**
- Track performance improvements or regressions over time
- Quickly identify when changes impact performance
- Establish SLA targets

## Step 7: Document Your Results

Create a test report documenting your findings. Here's a template:



---

## Load Test Report Template

```markdown
# Load Test Report: {Test Name}

## Test Information

**Date:** {Date}
**Test ID:** {Test Run ID}
**Endpoint:** {API Endpoint}
**Duration:** {Ramp Up + Hold Time}

## Test Configuration

**Load Pattern:**
- Tasks: {number}
- Concurrency per Task: {number}
- Total Virtual Users: {total}
- Ramp Up: {seconds}
- Hold Duration: {seconds}
- Region(s): {regions}

## Results Summary

### Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Avg Response Time | {value}ms | < 200ms | ✅/❌ |
| p50 Response Time | {value}ms | < 100ms | ✅/❌ |
| p95 Response Time | {value}ms | < 300ms | ✅/❌ |
| p99 Response Time | {value}ms | < 500ms | ✅/❌ |
| Requests per Second | {value} | {target} | ✅/❌ |
| Success Rate | {value}% | > 99% | ✅/❌ |
| Error Rate | {value}% | < 1% | ✅/❌ |

### Request Statistics

- **Total Requests:** {number}
- **Successful Requests:** {number}
- **Failed Requests:** {number}
- **Average Bandwidth:** {value} KB/s

### Resource Utilization

- **Peak CPU Usage:** {value}%
- **Peak Memory Usage:** {value}%
- **Container Count:** {number}

## Observations

### Performance

- {Observation about response times}
- {Observation about throughput}
- {Observation about stability}

### Errors

- {Any errors encountered}
- {Error patterns or trends}
- {Root cause analysis}

### Bottlenecks

- {Identified bottlenecks}
- {Resource constraints}
- {Scaling limitations}

## Recommendations

1. {Recommendation 1}
2. {Recommendation 2}
3. {Recommendation 3}

## Next Steps

- [ ] {Action item 1}
- [ ] {Action item 2}
- [ ] {Action item 3}

## Attachments

- Test Results CSV: {link or filename}
- CloudWatch Dashboard: {link}
- Artifacts Archive: {link or filename}
```

## Advanced Testing Scenarios

### Testing Authenticated Endpoints

For endpoints requiring authentication:

1. **Obtain a Cognito JWT Token:**
   ```bash
   # Using AWS CLI
   aws cognito-idp initiate-auth \
     --auth-flow USER_PASSWORD_AUTH \
     --client-id {your-client-id} \
     --auth-parameters USERNAME={username},PASSWORD={password} \
     --region ap-southeast-1
   ```

2. **Add Authorization Header:**
   ```
   Authorization: Bearer {jwt-token}
   ```

3. **Token Expiration:**
   - Cognito tokens typically expire after 1 hour
   - For longer tests, you may need to refresh tokens
   - Consider using custom test scripts (JMeter/K6) for token management

### Testing POST/PUT Endpoints

Example: Testing `POST /cart` (Add to Cart)

**Configuration:**
```
HTTP Endpoint: https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/cart
HTTP Method: POST

Headers:
  Content-Type: application/json
  Authorization: Bearer {jwt-token}

Body Payload:
{
  "productId": "prod-123",
  "quantity": 2
}
```

**Considerations:**
- POST/PUT operations modify data
- Test against a test/staging environment first
- Consider data cleanup after tests
- Monitor database write capacity

### Multi-Endpoint Testing with JMeter

For complex scenarios testing multiple endpoints:

1. **Create a JMeter Test Script (.jmx):**
   - Define multiple HTTP samplers
   - Add logic controllers for realistic user flows
   - Include think times between requests
   - Add assertions for response validation

2. **Example User Flow:**
   ```
   1. GET /products (browse products)
   2. Wait 2 seconds (think time)
   3. GET /products/{id} (view product details)
   4. Wait 3 seconds
   5. POST /cart (add to cart)
   6. Wait 2 seconds
   7. GET /cart (view cart)
   ```

3. **Upload to DLT:**
   - Select "JMeter" as test type
   - Upload your .jmx file
   - Configure traffic shape (DLT overrides JMeter's thread settings)

### Multi-Region Testing

Test from multiple AWS regions to simulate global traffic:

**Configuration:**
```
Region 1: ap-southeast-1 (Singapore)
  - Tasks: 3
  - Concurrency: 100
  - Total: 300 users

Region 2: us-east-1 (N. Virginia)
  - Tasks: 2
  - Concurrency: 100
  - Total: 200 users

Total Load: 500 concurrent users from 2 regions
```

**Benefits:**
- Test geographic distribution
- Identify latency differences by region
- Validate CloudFront or global accelerator performance

## Performance Targets and SLAs

### Recommended Targets for E-Commerce APIs

**Response Time Targets:**
```
Excellent:  < 100ms (p95)
Good:       < 200ms (p95)
Acceptable: < 500ms (p95)
Poor:       > 500ms (p95)
```

**Throughput Targets:**
```
Low Traffic:     100-500 RPS
Medium Traffic:  500-2,000 RPS
High Traffic:    2,000-10,000 RPS
Peak Traffic:    > 10,000 RPS
```

**Availability Targets:**
```
Success Rate: > 99.9% (3 nines)
Error Rate:   < 0.1%
```

### API-Specific Targets

**Product Listing (GET /products):**
- Target: < 200ms (p95)
- Rationale: High-traffic, user-facing, read-only

**Product Search (GET /search):**
- Target: < 300ms (p95)
- Rationale: Complex query, acceptable slight delay

**Cart Operations (POST /cart):**
- Target: < 300ms (p95)
- Rationale: Write operation, user expects quick feedback

**Order Placement (POST /orders):**
- Target: < 1000ms (p95)
- Rationale: Complex workflow, users tolerate longer wait

## Troubleshooting Common Issues

### High Response Times

**Symptoms:**
- p95 > 500ms
- Response times increase during hold period

**Possible Causes:**
1. Lambda cold starts
2. Database connection pool exhaustion
3. DynamoDB throttling
4. Insufficient Lambda memory/CPU

**Solutions:**
- Enable Lambda provisioned concurrency
- Increase DynamoDB read/write capacity
- Optimize database queries
- Increase Lambda memory allocation

### High Error Rates

**Symptoms:**
- Error rate > 1%
- 500 or 502 status codes

**Possible Causes:**
1. Lambda timeouts
2. Unhandled exceptions
3. Database connection failures
4. API Gateway throttling

**Solutions:**
- Check CloudWatch Logs for Lambda errors
- Increase Lambda timeout
- Review error logs in DLT artifacts
- Increase API Gateway throttle limits

### Container Resource Limits

**Symptoms:**
- CPU > 75% or Memory > 85%
- Inconsistent test results
- Lower than expected RPS

**Solutions:**
1. Reduce concurrency per task
2. Increase task count (distribute load)
3. Increase vCPUs per task (requires quota increase)
4. Optimize test script efficiency

### Rate Limiting (429 Errors)

**Symptoms:**
- 429 status codes
- Throttling errors in results

**Possible Causes:**
1. API Gateway throttle limits exceeded
2. DynamoDB throttling
3. Lambda concurrent execution limit

**Solutions:**
- Increase API Gateway rate limits
- Enable DynamoDB auto-scaling
- Request Lambda concurrency limit increase
- Implement exponential backoff in application

## Best Practices

### 1. Start Small, Scale Gradually

```
Test 1: 100 users   (establish baseline)
Test 2: 500 users   (5x increase)
Test 3: 1,000 users (2x increase)
Test 4: 2,000 users (2x increase)
```

### 2. Test During Off-Peak Hours

- Avoid impacting real users
- Easier to isolate performance issues
- More predictable results

### 3. Monitor Multiple Metrics

Don't just watch response times:
- Error rates
- Resource utilization (CPU, memory, database)
- Cost implications
- Downstream service impact

### 4. Document Everything

- Test configurations
- Results and observations
- Changes made between tests
- Performance trends over time

### 5. Automate Regular Testing

Use scheduled tests to:
- Monitor performance trends
- Detect regressions early
- Validate deployments
- Establish performance baselines

### 6. Test Realistic Scenarios

- Mix of read and write operations
- Realistic data payloads
- Appropriate think times
- User behavior patterns

### 7. Clean Up Test Data

After testing write operations:
- Remove test records from database
- Clear test user carts
- Cancel test orders
- Reset test user accounts

## Cost Considerations

### DLT Solution Costs

**Primary Cost Drivers:**
1. **ECS Fargate Tasks**
   - Charged per vCPU-hour and GB-hour
   - Example: 10 tasks × 2 vCPU × 0.1 hours = 2 vCPU-hours
   - Cost: ~$0.08 per vCPU-hour

2. **Data Transfer**
   - Outbound data from AWS
   - Minimal for most tests

3. **S3 Storage**
   - Test results and artifacts
   - Negligible cost

**Example Test Cost:**
```
Configuration: 10 tasks, 2 vCPU each, 10-minute test
vCPU-hours: 10 × 2 × (10/60) = 3.33 vCPU-hours
Cost: 3.33 × $0.04 = ~$0.13 per test
```

### API Under Test Costs

Consider costs for services being tested:
- Lambda invocations and duration
- DynamoDB read/write units
- API Gateway requests
- Data transfer

**Tip:** Use AWS Cost Explorer to track load testing costs separately by tagging resources.

## Integration with CI/CD

### Automated Performance Testing

Integrate load testing into your deployment pipeline:

1. **Post-Deployment Validation:**
   ```bash
   # After CDK deploy
   # Trigger DLT test via API
   # Wait for results
   # Validate against thresholds
   ```

2. **Performance Regression Detection:**
   - Run baseline test after each deployment
   - Compare against previous baseline
   - Fail pipeline if performance degrades > 10%

3. **Scheduled Performance Monitoring:**
   - Daily/weekly scheduled tests
   - Alert on performance degradation
   - Track trends over time

## Additional Resources

### AWS Documentation

- [Distributed Load Testing on AWS](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
- [API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [Lambda Performance Optimization](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Performance](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

### Testing Frameworks

- [Taurus Documentation](https://gettaurus.org/docs/)
- [JMeter User Manual](https://jmeter.apache.org/usermanual/index.html)
- [K6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)

### Monitoring and Analysis

- [CloudWatch Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
- [X-Ray Tracing](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)

## Quick Reference Commands

### Get API Gateway Endpoint

```bash
# From CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text \
  --region ap-southeast-1
```

### Get Cognito Token

```bash
# Authenticate and get JWT token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id {your-client-id} \
  --auth-parameters USERNAME={username},PASSWORD={password} \
  --region ap-southeast-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

### Check API Gateway Throttle Limits

```bash
# Get API Gateway usage plan
aws apigateway get-usage-plans \
  --region ap-southeast-1
```

### Monitor Lambda Concurrency

```bash
# Get Lambda concurrent executions
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value={function-name} \
  --start-time {start-time} \
  --end-time {end-time} \
  --period 60 \
  --statistics Maximum \
  --region ap-southeast-1
```

---

## Summary

This guide provides a comprehensive approach to load testing your E-Com67 platform:

1. **Start with simple tests** - Single endpoint, low load
2. **Establish baselines** - Document expected performance
3. **Scale gradually** - Increase load systematically
4. **Monitor everything** - Response times, errors, resources
5. **Document results** - Track trends and improvements
6. **Automate testing** - Integrate into CI/CD pipeline

By following this guide, you'll gain confidence in your platform's performance and identify optimization opportunities before they impact users.

For questions or issues, refer to the AWS DLT documentation or consult with your DevOps team.
