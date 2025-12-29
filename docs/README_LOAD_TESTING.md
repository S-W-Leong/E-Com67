# Load Testing Documentation

Complete guide for load testing the E-Com67 platform using AWS Distributed Load Testing (DLT) solution.

## 📚 Documentation Index

### 1. [Load Testing Summary](./LOAD_TESTING_SUMMARY.md) - **START HERE**
Overview of all load testing documentation with quick navigation guide.

**Read this first** to understand the documentation structure and find what you need.

---

### 2. [Load Testing Guide](./load-testing-guide.md) - **Complete Reference**
Comprehensive guide covering everything from setup to advanced scenarios.

**Contents:**
- Prerequisites and DLT console access
- Step-by-step test creation (General Settings → Scenario → Traffic Shape → Review)
- Traffic configuration and scaling strategies
- Real-time monitoring and results analysis
- Advanced scenarios (authenticated endpoints, multi-region, JMeter/K6/Locust)
- Performance targets and SLAs
- Best practices and troubleshooting
- Cost optimization
- CI/CD integration

**When to use:** First-time setup, learning load testing concepts, detailed reference

---

### 3. [Quick Start Guide](./load-testing-quick-start.md) - **5-Minute Setup**
Get your first load test running quickly with minimal configuration.

**Contents:**
- Quick configuration template
- Recommended test progression (100 → 500 → 1,000 → 2,000 users)
- Key metrics reference table
- Common issues and quick fixes
- One-page test report template
- Essential commands

**When to use:** Experienced users, rapid testing, quick reference

---

### 4. [Test Results Template](./load-test-results-template.md) - **Documentation Template**
Professional template for documenting and sharing test results.

**Contents:**
- Executive summary format
- Detailed metrics tables
- Performance analysis framework
- Error analysis structure
- Baseline comparison format
- Recommendations template
- Sign-off section

**When to use:** After completing tests, formal documentation, stakeholder reports

---

### 5. [Troubleshooting Guide](./load-testing-troubleshooting.md) - **Problem Solving**
Diagnose and fix common load testing issues.

**Contents:**
- High response times → causes and solutions
- High error rates → diagnostic steps
- Rate limiting (429 errors) → quick fixes
- Container resource limits → optimization strategies
- Authentication failures → token management
- Cost concerns → optimization tips
- Diagnostic commands reference

**When to use:** Test failures, performance issues, error investigation

---

## 🚀 Quick Start

### Your First Load Test (5 Minutes)

1. **Access DLT Console**
   - Navigate to your DLT console URL
   - Sign in with Cognito credentials

2. **Create Test**
   ```
   Test Name: Products API Baseline
   Endpoint: https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
   Method: GET
   ```

3. **Configure Traffic**
   ```
   Region: ap-southeast-1
   Tasks: 2
   Concurrency: 50
   Ramp Up: 60 seconds
   Hold: 300 seconds
   ```

4. **Run and Monitor**
   - Enable "Live Data" checkbox
   - Click "Create" to start
   - Watch real-time metrics

5. **Review Results**
   - Wait for parsing to complete
   - Review metrics (response time, errors, throughput)
   - Download artifacts
   - Document using template

**Expected Results:**
- ✅ Avg Response Time < 200ms
- ✅ p95 < 300ms
- ✅ Success Rate > 99%
- ✅ Error Rate < 1%

---

## 📊 Available APIs for Testing

### Recommended Starting Point: GET /products ⭐

**Why?**
- No authentication required (simpler setup)
- Read-only operation (safe to test)
- High-traffic endpoint
- Good baseline for performance

**Configuration:**
```
URL: https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
Method: GET
Headers: None required
Body: None
```

### Other Public Endpoints

- `GET /products/{id}` - Single product lookup
- `GET /search?q={query}` - Product search

### Authenticated Endpoints (Test After Baseline)

- `GET /cart` - User's shopping cart
- `GET /orders` - User's order history
- `POST /cart` - Add items to cart

**Requires:** Authorization header with Cognito JWT token

---

## 📈 Recommended Test Progression

```
Test 1: 100 users   → Establish baseline performance
Test 2: 500 users   → Validate scaling capabilities
Test 3: 1,000 users → Stress test under load
Test 4: 2,000 users → Peak load testing
```

**Between each test:**
1. Review and document results
2. Identify and address issues
3. Compare against baseline
4. Increase load gradually

---

## 🎯 Performance Targets

### Response Time Targets

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| **Average** | < 100ms | < 200ms | < 500ms | > 500ms |
| **p95** | < 150ms | < 300ms | < 750ms | > 750ms |
| **p99** | < 250ms | < 500ms | < 1000ms | > 1000ms |

### Reliability Targets

| Metric | Target | Minimum |
|--------|--------|---------|
| **Success Rate** | > 99.9% | > 99% |
| **Error Rate** | < 0.1% | < 1% |
| **Availability** | 99.9% | 99% |

### Throughput Targets

| Traffic Level | RPS Target |
|---------------|------------|
| **Low** | 100-500 |
| **Medium** | 500-2,000 |
| **High** | 2,000-10,000 |
| **Peak** | > 10,000 |

---

## 🛠️ Essential Commands

### Get API Endpoint
```bash
aws cloudformation describe-stacks \
  --stack-name E-Com67-ApiStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

### Get Cognito Token (for authenticated endpoints)
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id {client-id} \
  --auth-parameters USERNAME={user},PASSWORD={pass} \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

### Test Endpoint Manually
```bash
curl https://{api-id}.execute-api.ap-southeast-1.amazonaws.com/prod/products
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/{function-name} --follow
```

---

## 🔍 Key Metrics to Monitor

### During Test (Live Data)

- **Average Response Time** - Should remain stable
- **Virtual Users** - Should match configuration
- **Success Count** - Should increase steadily
- **Error Count** - Should be zero or very low

### After Test (Results Analysis)

- **Response Time Distribution** (p50, p90, p95, p99)
- **Throughput** (Requests per Second)
- **Error Rate** (percentage of failed requests)
- **Resource Utilization** (CPU, Memory from CloudWatch)

---

## ⚠️ Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| **High Response Times** | Check Lambda cold starts, increase memory |
| **500 Errors** | Review CloudWatch Logs, check Lambda timeout |
| **429 Rate Limiting** | Increase API Gateway limits, enable DynamoDB auto-scaling |
| **Container CPU > 75%** | Reduce concurrency or increase task count |
| **Authentication Failures** | Verify token validity, check expiration |

See [Troubleshooting Guide](./load-testing-troubleshooting.md) for detailed solutions.

---

## 📋 Best Practices Checklist

### Before Testing
- [ ] Start with public endpoints (no auth)
- [ ] Test during off-peak hours
- [ ] Begin with low load (100 users)
- [ ] Enable "Live Data" monitoring
- [ ] Have CloudWatch console open

### During Testing
- [ ] Monitor real-time metrics
- [ ] Watch CloudWatch Container Insights
- [ ] Check for errors immediately
- [ ] Note any anomalies
- [ ] Run only one test at a time

### After Testing
- [ ] Wait for results parsing
- [ ] Review all metrics thoroughly
- [ ] Download test artifacts
- [ ] Document results using template
- [ ] Set baseline for comparisons
- [ ] Share results with team

### Scaling Up
- [ ] Increase load gradually (2x)
- [ ] Monitor resource utilization
- [ ] Stop if limits exceeded
- [ ] Investigate errors before continuing
- [ ] Compare to baseline

---

## 💰 Cost Considerations

### Per Test Cost Estimate

```
Configuration: 10 tasks × 2 vCPU × 10 minutes
vCPU-hours: 10 × 2 × (10/60) = 3.33 vCPU-hours
Cost: 3.33 × $0.04 = ~$0.13 per test
```

### Monthly Cost (Daily Testing)

```
1 test/day × 30 days = 30 tests
Cost: 30 × $0.13 = ~$3.90/month
```

**Cost Optimization Tips:**
- Start with shorter tests (5 minutes vs 30 minutes)
- Test during off-peak hours
- Clean up old test results from S3
- Use smaller initial configurations

---

## 🔗 Related Documentation

### E-Com67 Platform Docs
- [API Endpoints](./api-endpoints.md) - Complete API reference
- [Architecture Overview](../README.md) - Platform architecture
- [Deployment Guide](../README.md#setup-and-deployment) - Setup instructions

### AWS Documentation
- [Distributed Load Testing on AWS](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/)
- [DLT User Guide](https://docs.aws.amazon.com/solutions/latest/distributed-load-testing-on-aws/)
- [API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [Lambda Performance](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

---

## 📞 Support

### Questions or Issues?

1. **Check Documentation First**
   - Review [Troubleshooting Guide](./load-testing-troubleshooting.md)
   - Search [Load Testing Guide](./load-testing-guide.md)

2. **AWS Support**
   - [AWS Solutions Library](https://aws.amazon.com/solutions/)
   - [GitHub Issues](https://github.com/aws-solutions/distributed-load-testing-on-aws/issues)
   - AWS Support Center (if you have a support plan)

3. **Internal Resources**
   - DevOps Team: [contact]
   - Platform Team: [contact]
   - On-Call Engineer: [contact]

---

## 📝 Document Updates

**Version:** 1.0  
**Created:** December 29, 2024  
**Last Updated:** December 29, 2024  
**Owner:** Platform Team

**Review Schedule:** Quarterly or after major platform changes

---

## ✅ Next Steps

1. [ ] Read [Load Testing Summary](./LOAD_TESTING_SUMMARY.md) for overview
2. [ ] Follow [Quick Start Guide](./load-testing-quick-start.md) for first test
3. [ ] Document results using [Test Results Template](./load-test-results-template.md)
4. [ ] Set baseline and schedule regular tests
5. [ ] Share results with team

---

*Ready to start load testing? Begin with the [Quick Start Guide](./load-testing-quick-start.md) or dive into the [Complete Load Testing Guide](./load-testing-guide.md).*
