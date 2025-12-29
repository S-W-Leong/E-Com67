# Load Testing Quick Start

## 5-Minute Setup

### 1. Access DLT Console
- Navigate to your DLT console URL
- Sign in with Cognito credentials

### 2. Create Test - Quick Config

```
Test Name: Products API Baseline
Endpoint: https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
Method: GET
```

### 3. Traffic Shape - Starter Config

```
Region: ap-southeast-1
Tasks: 2
Concurrency: 50
Ramp Up: 60 seconds
Hold For: 300 seconds
```

**Total Load:** 100 concurrent users for 5 minutes

### 4. Run and Monitor

- Enable "Live Data" checkbox
- Click "Create" to start test
- Watch real-time metrics

### 5. Review Results

**Good Performance Indicators:**
- ✅ Avg Response Time < 200ms
- ✅ p95 < 300ms
- ✅ Error Rate < 1%
- ✅ Success Rate > 99%

## Recommended Test Progression

```
Test 1: 100 users   → Establish baseline
Test 2: 500 users   → Validate scaling
Test 3: 1,000 users → Stress test
Test 4: 2,000 users → Peak load
```

## Key Metrics to Watch

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| Avg Response Time | < 200ms | Optimize Lambda/DB |
| p95 Response Time | < 300ms | Check for bottlenecks |
| Error Rate | < 1% | Review CloudWatch logs |
| CPU Usage | < 75% | Reduce concurrency |
| Memory Usage | < 85% | Reduce concurrency |

## Common Issues & Quick Fixes

**High Response Times?**
- Check Lambda cold starts
- Review DynamoDB capacity
- Increase Lambda memory

**Errors (500/502)?**
- Check CloudWatch Logs
- Verify Lambda timeout
- Check database connections

**Rate Limiting (429)?**
- Increase API Gateway limits
- Enable DynamoDB auto-scaling
- Add exponential backoff

## Test Report Template (1-Page)

```markdown
# Load Test: {Name} - {Date}

## Config
- Endpoint: {url}
- Load: {users} users, {duration} minutes
- Region: {region}

## Results
- Avg Response: {value}ms
- p95: {value}ms
- RPS: {value}
- Success Rate: {value}%
- Errors: {count}

## Status: ✅ PASS / ❌ FAIL

## Actions:
- [ ] {action 1}
- [ ] {action 2}
```

## Useful Commands

**Get API Endpoint:**
```bash
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

**Get Auth Token:**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id {client-id} \
  --auth-parameters USERNAME={user},PASSWORD={pass} \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

## Next Steps

1. Run baseline test with 100 users
2. Set as baseline in DLT console
3. Document results
4. Scale up gradually
5. Automate with scheduled tests

For detailed instructions, see [Load Testing Guide](./load-testing-guide.md)
