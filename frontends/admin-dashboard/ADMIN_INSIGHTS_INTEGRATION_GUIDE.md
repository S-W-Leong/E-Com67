# Admin Insights Widget - Quick Integration Guide

## Prerequisites

Before using the Admin Insights Widget, ensure:

1. ✅ AdminInsightsStack is deployed to AWS
2. ✅ WebSocket API is created and accessible
3. ✅ Agent Lambda is configured with memory ID
4. ✅ Analytics tool Lambdas are deployed
5. ✅ Cognito User Pool is configured

## Step 1: Get WebSocket URL

After deploying the AdminInsightsStack, get the WebSocket URL:

```bash
# Option 1: From CloudFormation
aws cloudformation describe-stacks \
  --stack-name E-Com67-AdminInsightsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURL`].OutputValue' \
  --output text

# Option 2: From CDK deploy output
# Look for: E-Com67-AdminInsightsStack.WebSocketURL = wss://...
```

## Step 2: Update Environment Configuration

Edit `frontends/admin-dashboard/.env`:

```bash
# Add or update this line with your actual WebSocket URL
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
```

**Example:**
```bash
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://abc123xyz.execute-api.ap-southeast-1.amazonaws.com/prod
```

## Step 3: Install Dependencies (if needed)

```bash
cd frontends/admin-dashboard
npm install
```

## Step 4: Test Locally

```bash
npm run dev
```

1. Open browser to `http://localhost:5173` (or shown port)
2. Log in with admin credentials
3. Look for floating chat button in bottom-right corner
4. Click to open chat widget
5. Verify connection status shows "Connected"
6. Try a test query: "Show me order trends"

## Step 5: Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Step 6: Deploy

Deploy the built files to your hosting platform:

### Option A: AWS S3 + CloudFront

```bash
# Sync to S3 bucket
aws s3 sync dist/ s3://your-admin-dashboard-bucket/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Option B: Using CDK Pipeline

The admin dashboard pipeline should automatically deploy when you push changes.

## Verification Checklist

After deployment, verify:

- [ ] Widget button appears in bottom-right corner
- [ ] Clicking button opens chat window
- [ ] Connection status shows "Connected" (green dot)
- [ ] Can send messages
- [ ] Receives responses from agent
- [ ] Analytics data formats correctly
- [ ] Product links work
- [ ] Session persists across page navigation
- [ ] Widget works on all admin pages (Dashboard, Products, Orders)

## Troubleshooting

### Widget Not Appearing

**Problem**: Chat button doesn't show up

**Solutions**:
1. Check browser console for errors
2. Verify Layout.jsx imports AdminInsightsWidget
3. Clear browser cache and reload
4. Check that build includes new files

### Connection Fails

**Problem**: Status shows "Disconnected" or "Connecting..."

**Solutions**:
1. Verify `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL` is set correctly in `.env`
2. Check WebSocket URL format: `wss://api-id.execute-api.region.amazonaws.com/stage`
3. Verify AdminInsightsStack is deployed successfully
4. Check CloudWatch logs for WebSocket connect Lambda
5. Verify Cognito authentication is working
6. Check browser console for WebSocket errors

### Messages Not Sending

**Problem**: Can't send messages or no response

**Solutions**:
1. Verify connection status is "Connected"
2. Check browser console for errors
3. Verify agent Lambda is running (check CloudWatch logs)
4. Check that memory ID is configured in agent Lambda
5. Verify analytics tool Lambdas are accessible

### Analytics Not Formatting

**Problem**: Data shows as plain text instead of formatted

**Solutions**:
1. Check that agent is returning data in expected JSON format
2. Verify AnalyticsMessageFormatter is imported correctly
3. Check browser console for JSON parsing errors
4. Test agent responses directly via WebSocket

## Testing Queries

Try these queries to test functionality:

### Order Trends
- "Show me order trends for the last 7 days"
- "What's my order volume this month?"
- "How many orders are pending?"

### Sales Insights
- "What are my top-selling products?"
- "Show me sales by category"
- "Which products are underperforming?"

### Product Search
- "Search for products in electronics"
- "Find products with low stock"
- "Show me all products"

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL` | WebSocket endpoint for Admin Insights Agent | `wss://abc123.execute-api.ap-southeast-1.amazonaws.com/prod` |
| `VITE_AWS_REGION` | AWS region | `ap-southeast-1` |
| `VITE_USER_POOL_ID` | Cognito User Pool ID | `ap-southeast-1_xxxxxxxxx` |
| `VITE_USER_POOL_CLIENT_ID` | Cognito Client ID | `xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `VITE_API_ENDPOINT` | REST API endpoint | `https://api-id.execute-api.ap-southeast-1.amazonaws.com/prod` |

## Support Resources

- **Implementation Details**: See `ADMIN_INSIGHTS_WIDGET_IMPLEMENTATION.md`
- **Design Document**: `.kiro/specs/admin-insights-agent/design.md`
- **Requirements**: `.kiro/specs/admin-insights-agent/requirements.md`
- **CloudWatch Logs**: Check Lambda logs for debugging
- **WebSocket API Logs**: Check API Gateway logs for connection issues

## Quick Commands

```bash
# Get WebSocket URL
aws cloudformation describe-stacks --stack-name E-Com67-AdminInsightsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURL`].OutputValue' --output text

# Check agent Lambda logs
aws logs tail /aws/lambda/e-com67-admin-insights-agent --follow

# Check WebSocket connect Lambda logs
aws logs tail /aws/lambda/e-com67-admin-insights-websocket-connect --follow

# Test WebSocket connection (requires wscat)
wscat -c "wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod?token=YOUR_JWT_TOKEN"
```

## Next Steps

After successful integration:

1. Monitor CloudWatch metrics for usage
2. Review agent responses for accuracy
3. Gather user feedback
4. Consider implementing optional subtasks (15.6, 15.7) for testing
5. Plan for future enhancements (see implementation doc)

---

**Need Help?**
- Check CloudWatch logs for errors
- Review browser console for client-side issues
- Verify all environment variables are set correctly
- Ensure all AWS resources are deployed and accessible
