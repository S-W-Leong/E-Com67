# Load Test Report: Products API - Initial Baseline Test

**Date:** 2025-12-29  
**Test ID:** 2025-12-29T14-09-29_uwkXr34Vj4  
**Test Scenario ID:** 3T2FNWVOwg  
**Tester:** Shi Wei
**Environment:** Production

---

## Executive Summary

This initial baseline load test of the GET /products endpoint revealed **critical rate limiting issues**. The test generated 1,857,303 total requests over 6 minutes with 100 concurrent users, but **90.6% of requests failed with HTTP 429 (Too Many Requests) errors**. While the successful requests showed excellent response times (5ms median, 75ms p95), the high failure rate indicates that API Gateway throttle limits are significantly exceeded under this load.

**Overall Result:** ❌ **FAIL - Critical Rate Limiting**

**Immediate Action Required:** Increase API Gateway throttle limits or reduce test load to establish a valid baseline.

---

## Test Configuration

### Endpoint Under Test

```
URL: https://qy60l1ggnj.execute-api.ap-southeast-1.amazonaws.com/prod/products
Method: GET
Authentication: Not Required (Public Endpoint)
```

### Load Pattern

| Parameter | Value |
|-----------|-------|
| Region(s) | ap-southeast-1 |
| Task Count | 2 |
| Concurrency per Task | 50 |
| **Total Virtual Users** | **100** |
| Ramp Up Duration | 60 seconds |
| Hold Duration | 300 seconds (5 minutes) |
| **Total Test Duration** | **6 minutes (360 seconds)** |
| **Actual ECS Duration** | **504 seconds (8.4 minutes)** |

### Request Configuration

**Headers:**
```
None (Public endpoint)
```

**Body Payload:** None (GET request)

---

## Performance Results

### Summary Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Average Response Time** | 14.8ms | < 200ms | ✅ (for successful requests) |
| **Average Latency** | 14.8ms | < 50ms | ✅ |
| **Average Connection Time** | 0.01ms | < 20ms | ✅ |
| **Requests per Second** | 5,159 RPS | > 200 RPS | ⚠️ (but 90.6% failed) |
| **Total Requests** | 1,857,303 | - | - |
| **Successful Requests (200)** | 174,012 | > 99% | ❌ **9.4%** |
| **Failed Requests (429)** | 1,683,291 | < 1% | ❌ **90.6%** |
| **Success Rate** | 9.4% | > 99% | ❌ **CRITICAL** |
| **Error Rate** | 90.6% | < 1% | ❌ **CRITICAL** |

### Response Time Distribution (Percentiles)

**Note:** These percentiles are for the 9.4% of requests that succeeded (174,012 requests).

| Percentile | Response Time | Target | Status |
|------------|---------------|--------|--------|
| **p0 (Min)** | 2ms | - | ✅ |
| **p50 (Median)** | 5ms | < 100ms | ✅ Excellent |
| **p90** | 51ms | < 250ms | ✅ Excellent |
| **p95** | 75ms | < 300ms | ✅ Excellent |
| **p99** | 110ms | < 500ms | ✅ Excellent |
| **p99.9** | 187ms | < 1000ms | ✅ Excellent |
| **p100 (Max)** | 2,230ms | - | ⚠️ Outlier |

**Interpretation:**
- For the requests that succeeded, performance was **excellent**
- 50% of successful requests completed in under 5ms
- 95% of successful requests completed in under 75ms
- Only 0.1% of successful requests exceeded 187ms
- The maximum response time of 2.23 seconds is an outlier

### Throughput Analysis

```
Total Requests: 1,857,303 requests
Test Duration: 360 seconds
Average RPS: 5,159 requests/second
Successful RPS: 483 requests/second (9.4% of total)
Failed RPS: 4,676 requests/second (90.6% of total)

Total Data Transferred: 1,657,358,214 bytes (1.54 GB)
Average Bandwidth: 4.6 MB/second
Data per Request: ~892 bytes average
```

**Analysis:**
- The test generated extremely high request volume (5,159 RPS)
- This far exceeds typical API Gateway default limits (10,000 RPS burst, 5,000 RPS steady)
- However, with 100 concurrent users, each user was attempting ~52 requests/second
- This is unrealistically high for a typical user browsing products

---

## Resource Utilization

### Container Metrics (from Test Results)

| Resource | Configuration | Notes |
|----------|---------------|-------|
| **vCPU per Task** | 2 vCPU | Standard configuration |
| **Memory per Task** | 4096 MB (4 GB) | Standard configuration |
| **Task Count** | 2 tasks | As configured |
| **ECS Duration** | 504 seconds | Longer than test duration (360s) due to startup/shutdown |

**Note:** Container resource utilization metrics (CPU%, Memory%) are not available in the XML results. These should be reviewed in CloudWatch Container Insights.

### Backend Service Metrics

**API Gateway:**
- Total Requests: 1,857,303
- 200 OK Responses: 174,012 (9.4%)
- 429 Throttle Errors: 1,683,291 (90.6%)
- **Critical Finding:** API Gateway throttle limits were severely exceeded

**Estimated Lambda Invocations:**
- Only successful requests (174,012) would have invoked Lambda
- Failed requests (1,683,291) were rejected at API Gateway level
- This prevented overwhelming the backend Lambda functions

---

## Error Analysis

### Error Summary

| Error Type | Count | Percentage | HTTP Status |
|------------|-------|------------|-------------|
| **Rate Limiting (Throttle)** | 1,683,291 | 90.6% | 429 |
| **Successful Requests** | 174,012 | 9.4% | 200 |
| **Total Requests** | **1,857,303** | **100%** | - |

### Error Details

**429 Too Many Requests (1,683,291 occurrences - 90.6%):**

**Root Cause:** API Gateway throttle limits exceeded

**Analysis:**
- API Gateway has default throttle limits:
  - **Burst Limit:** 5,000 requests (short bursts)
  - **Steady-State Limit:** 10,000 requests per second (account-level)
- This test generated 5,159 RPS average, which is within the steady-state limit
- However, the burst pattern likely exceeded the burst capacity
- With 100 concurrent users making continuous requests, the burst limit was quickly exhausted

**Impact:**
- 90.6% of users experienced throttling
- This represents a complete failure for most users
- In production, this would result in a poor user experience

**Recommended Actions:**
1. **Immediate:** Reduce test load to establish valid baseline (start with 10-20 users)
2. **Short-term:** Increase API Gateway throttle limits via Usage Plan
3. **Long-term:** Implement caching (CloudFront, API Gateway cache) to reduce backend load

---

## Performance Trends

### Response Time Over Time

**Note:** Detailed time-series data would require analyzing the kpi.jtl file (368 MB). Based on summary metrics:

```
Successful Requests (9.4%):
  - Median: 5ms (excellent)
  - p95: 75ms (excellent)
  - Consistent low latency for requests that succeeded

Failed Requests (90.6%):
  - Immediate 429 responses from API Gateway
  - No backend processing occurred
  - Fast failure (good for preventing cascade failures)
```

### Throughput Over Time

```
Total RPS: 5,159 requests/second (average)
Successful RPS: 483 requests/second (9.4%)
Failed RPS: 4,676 requests/second (90.6%)

Pattern:
- High request rate maintained throughout test
- Consistent throttling throughout test duration
- No degradation in backend performance (for successful requests)
```

---

## Observations

### Positive Findings

1. **Excellent Backend Performance**
   - For requests that succeeded, response times were exceptional
   - Median of 5ms and p95 of 75ms indicate highly optimized backend
   - No performance degradation observed in successful requests

2. **Effective Throttling**
   - API Gateway throttling prevented backend overload
   - Failed requests returned quickly (no timeout delays)
   - Protected Lambda functions and DynamoDB from excessive load

3. **Consistent Performance**
   - Response time distribution shows consistent performance
   - No significant outliers (except max of 2.23s)
   - Backend remained stable despite high request volume

4. **Low Latency**
   - Average connection time of 0.01ms indicates excellent network performance
   - Average latency of 14.8ms is very low
   - Infrastructure is well-optimized

### Critical Issues

1. **Severe Rate Limiting (90.6% Failure Rate)**
   - **Severity:** CRITICAL
   - **Impact:** Test is invalid for baseline establishment
   - **Root Cause:** API Gateway throttle limits exceeded
   - **Recommendation:** Reduce load or increase throttle limits

2. **Unrealistic Load Pattern**
   - **Issue:** 100 users generating 5,159 RPS = ~52 requests/second per user
   - **Analysis:** Real users browsing products would make 1-2 requests/second maximum
   - **Recommendation:** Adjust test to simulate realistic user behavior

3. **No Think Time**
   - **Issue:** Test appears to have no delay between requests
   - **Impact:** Creates unrealistic continuous load
   - **Recommendation:** Add 1-2 second think time between requests

---

## Bottleneck Analysis

### Identified Bottlenecks

1. **API Gateway Throttle Limits** ⚠️ **CRITICAL BOTTLENECK**
   - **Impact:** 90.6% of requests rejected
   - **Severity:** HIGH - Prevents valid testing
   - **Current Limits:** 
     - Burst: 5,000 requests
     - Steady-state: 10,000 RPS (account-level)
   - **Recommendation:** 
     - Increase burst limit to 10,000 requests
     - Increase steady-state limit to 20,000 RPS
     - Or reduce test load to fit within current limits

2. **Test Configuration** ⚠️ **DESIGN ISSUE**
   - **Impact:** Unrealistic load pattern
   - **Severity:** MEDIUM - Affects test validity
   - **Issue:** No think time between requests
   - **Recommendation:** 
     - Add 1-2 second think time
     - Reduce concurrency to 20-50 users
     - Use more realistic request patterns

### Capacity Headroom

**Cannot be determined** due to throttling. Backend capacity remains unknown because:
- Only 9.4% of requests reached the backend
- Lambda and DynamoDB capacity not tested
- Need to resolve throttling before assessing backend capacity

**Next Steps:**
1. Resolve API Gateway throttling
2. Re-run test with realistic load
3. Then assess backend capacity headroom

---

## Comparison to Baseline

**N/A** - This was intended to be the baseline test, but the high failure rate makes it invalid for baseline purposes.

**Recommendation:** Re-run test with corrected configuration before establishing baseline.

---

## Recommendations

### Immediate Actions (CRITICAL - Before Next Test)

1. **Reduce Test Load** ⚠️ **HIGHEST PRIORITY**
   - Start with 10-20 concurrent users (not 100)
   - Add 1-2 second think time between requests
   - Target: 100-200 RPS (not 5,000+ RPS)
   - **Rationale:** Establish valid baseline within current limits

2. **Review API Gateway Configuration**
   - Check current throttle limits in Usage Plan
   - Verify account-level limits
   - Document current configuration
   - **Rationale:** Understand current constraints

3. **Analyze Realistic User Behavior**
   - Determine typical user request patterns
   - Calculate expected RPS for target user count
   - Design test to match production patterns
   - **Rationale:** Ensure test validity

### Short-Term Improvements (Within 1 Week)

4. **Increase API Gateway Throttle Limits**
   - Increase burst limit from 5,000 to 10,000 requests
   - Increase steady-state limit from 10,000 to 20,000 RPS
   - Create Usage Plan with appropriate limits
   - **Rationale:** Support higher load for future growth

5. **Implement Caching Strategy**
   - Enable API Gateway caching (5-minute TTL)
   - Consider CloudFront in front of API Gateway
   - Cache GET /products responses
   - **Rationale:** Reduce backend load by 70-90%

6. **Re-run Test with Corrected Configuration**
   - Configuration: 20 users, 2-second think time
   - Expected RPS: ~10-20 requests/second
   - Duration: 5 minutes hold
   - **Rationale:** Establish valid baseline

### Long-Term Optimizations (Within 1 Month)

7. **Implement CloudFront CDN**
   - Cache product listings at edge locations
   - Reduce API Gateway load
   - Improve global latency
   - **Rationale:** Scalability and performance

8. **Enable DynamoDB Auto-Scaling**
   - Configure auto-scaling for read capacity
   - Set target utilization at 70%
   - **Rationale:** Handle traffic spikes

9. **Implement Rate Limiting at Application Level**
   - Add per-user rate limiting
   - Implement exponential backoff
   - Return user-friendly error messages
   - **Rationale:** Graceful degradation

10. **Establish Performance Monitoring**
    - Set up CloudWatch dashboards
    - Configure alarms for throttling
    - Track RPS and error rates
    - **Rationale:** Proactive issue detection

---

## Next Steps

### Before Next Test

- [ ] Reduce concurrent users from 100 to 20
- [ ] Add 1-2 second think time between requests
- [ ] Calculate expected RPS (target: 10-20 RPS)
- [ ] Review API Gateway throttle limits
- [ ] Document current configuration

### After Throttling Resolution

- [ ] Re-run test with corrected configuration
- [ ] Establish valid baseline
- [ ] Document baseline metrics
- [ ] Set baseline in DLT console
- [ ] Share results with team

### Long-Term

- [ ] Implement caching strategy
- [ ] Increase API Gateway limits
- [ ] Test with gradually increasing load (20 → 50 → 100 users)
- [ ] Establish performance SLAs
- [ ] Schedule regular load tests

---

## Test Artifacts

### Files Available

- **Test Results XML:** `9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.xml`
- **Performance Metrics (KPI):** `kpi-9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.jtl` (368 MB)
- **Taurus Log:** `bzt-9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.log`
- **JMeter Log:** `jmeter-9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.log`
- **JMeter Output:** `jmeter-9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.out`
- **Error Log:** `jmeter-9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.err` (empty - no JMeter errors)

### S3 Location

```
s3://distributed-load-testing-dlttestrunnerstoragedltsc-qbdvucaky6dl/results/3T2FNWVOwg/2025-12-29T14-09-29_uwkXr34Vj4/
```

### Download Commands

```bash
# Download all artifacts
aws s3 cp s3://distributed-load-testing-dlttestrunnerstoragedltsc-qbdvucaky6dl/results/3T2FNWVOwg/2025-12-29T14-09-29_uwkXr34Vj4/ ./test-results/ --recursive --region ap-southeast-1

# Download just the summary
aws s3 cp s3://distributed-load-testing-dlttestrunnerstoragedltsc-qbdvucaky6dl/results/3T2FNWVOwg/2025-12-29T14-09-29_uwkXr34Vj4/9ab53c4f-20eb-48b2-bc7c-6a0545615d9b-ap-southeast-1.xml ./test-summary.xml --region ap-southeast-1
```

---

## Appendix

### Test Environment Details

**AWS Account:** [Your Account ID]  
**Region:** ap-southeast-1 (Singapore)  
**API Gateway:** qy60l1ggnj.execute-api.ap-southeast-1.amazonaws.com  
**Endpoint:** /prod/products  

### Software Versions

- DLT Solution Version: 4.0+
- Taurus Version: Latest
- JMeter Version: Latest
- Test Framework: Taurus + JMeter

### Calculated Metrics

**Request Rate per User:**
```
Total RPS: 5,159
Concurrent Users: 100
RPS per User: 5,159 / 100 = 51.59 requests/second per user
```

**This is unrealistic** - typical users make 1-2 requests/second maximum.

**Recommended Configuration:**
```
Users: 20
Think Time: 2 seconds
Expected RPS: 20 users × 0.5 requests/second = 10 RPS
This is realistic and within API Gateway limits
```

### API Gateway Throttle Limits

**Default Limits (Account-Level):**
- Burst Capacity: 5,000 requests
- Steady-State Rate: 10,000 requests per second

**Current Test:**
- Average RPS: 5,159 (within steady-state limit)
- Burst Pattern: Likely exceeded burst capacity
- Result: 90.6% throttled

**Recommendation:**
- Request limit increase via AWS Support
- Or implement caching to reduce load
- Or reduce test load to fit within limits


---

## Key Takeaways

1. ❌ **Test Failed** - 90.6% error rate due to API Gateway throttling
2. ✅ **Backend Performance Excellent** - 5ms median, 75ms p95 for successful requests
3. ⚠️ **Test Configuration Issue** - Load pattern unrealistic (52 RPS per user)
4. 🔧 **Action Required** - Reduce load to 20 users with 2-second think time
5. 📈 **Next Test Target** - 10-20 RPS total, establish valid baseline

---

*This report documents a failed load test due to rate limiting. The test must be re-run with corrected configuration before establishing a baseline. For questions, contact the Platform Team.*
