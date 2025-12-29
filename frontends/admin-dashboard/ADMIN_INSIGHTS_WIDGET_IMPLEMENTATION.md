# Admin Insights Chat Widget Implementation

## Overview

The Admin Insights Chat Widget has been successfully implemented as a floating chat interface that provides real-time conversational analytics powered by the Admin Insights Agent. The widget is integrated into the admin dashboard and accessible from all pages.

## Implementation Summary

### Files Created

1. **`src/services/adminInsights.js`**
   - WebSocket service for Admin Insights Agent communication
   - Handles authentication with Cognito JWT tokens
   - Implements session management with localStorage
   - Provides reconnection logic with exponential backoff
   - Manages message sending and receiving
   - Supports real-time streaming responses

2. **`src/components/AdminInsightsWidget.jsx`**
   - Main chat widget component
   - Floating button in bottom-right corner
   - Expandable chat window with header, messages area, and input
   - Minimize/maximize functionality
   - Typing indicators and connection status display
   - Styled with Tailwind CSS matching admin dashboard theme

3. **`src/components/AnalyticsMessageFormatter.jsx`**
   - Formats analytics data into visual components
   - Detects and renders order trends with metrics cards
   - Displays sales insights with product links
   - Shows product search results with admin links
   - Provides visual indicators for data types (metrics, trends, insights)

4. **`.env.example`**
   - Template for environment configuration
   - Documents required environment variables

### Files Modified

1. **`src/components/Layout.jsx`**
   - Imported and integrated AdminInsightsWidget
   - Widget persists across all routes

2. **`.env`**
   - Added `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL` configuration

3. **`README.md`**
   - Documented Admin Insights configuration
   - Added feature description
   - Included deployment instructions

## Features Implemented

### Core Functionality
✅ WebSocket connection to Admin Insights API  
✅ Authentication with Cognito JWT tokens  
✅ Session management with localStorage  
✅ Reconnection logic with exponential backoff  
✅ Message sending and receiving  
✅ Real-time streaming responses  

### UI Components
✅ Floating chat button (bottom-right corner)  
✅ Expandable chat window  
✅ Header with connection status  
✅ Messages area with auto-scroll  
✅ Input field with send button  
✅ Minimize/maximize functionality  
✅ Typing indicators  
✅ Connection status display  
✅ Error handling and display  

### Analytics Formatting
✅ Order trends visualization with metrics cards  
✅ Sales insights with product links  
✅ Product search results with admin links  
✅ Visual indicators for data types  
✅ Category performance breakdown  
✅ Status distribution charts  

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
```

### Getting the WebSocket URL

After deploying the AdminInsightsStack, retrieve the WebSocket URL:

```bash
aws cloudformation describe-stacks \
  --stack-name E-Com67-AdminInsightsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURL`].OutputValue' \
  --output text
```

Or from CDK output:
```bash
cdk deploy E-Com67-AdminInsightsStack
# Look for: E-Com67-AdminInsightsStack.WebSocketURL
```

## Usage

### For Administrators

1. **Access the Widget**: Click the floating chat button in the bottom-right corner of any admin page

2. **Ask Questions**: Type natural language queries about your business:
   - "Show me order trends for the last 7 days"
   - "What are my top-selling products?"
   - "Search for products in the electronics category"
   - "What's my revenue this month?"

3. **View Analytics**: The widget displays formatted analytics data with:
   - Metrics cards for key performance indicators
   - Product lists with links to edit pages
   - Category breakdowns
   - Status distributions
   - Trend indicators

4. **Session Management**: 
   - Conversations persist across page navigation
   - Click "Clear session" to start a new conversation
   - Sessions are stored in localStorage

### Connection Status

The widget displays connection status in the header:
- 🟢 **Connected**: Ready to receive queries
- 🔴 **Disconnected**: Attempting to reconnect
- ⏳ **Connecting**: Establishing connection

## Architecture

### WebSocket Communication Flow

```
Admin Dashboard → WebSocket API → Agent Lambda → Analytics Tools
                                      ↓
                                  Bedrock Nova
                                      ↓
                                  Guardrails
                                      ↓
                                Session Memory
```

### Message Flow

1. User types message in widget
2. Widget sends message via WebSocket with session ID
3. Agent Lambda receives message and processes with Bedrock
4. Agent invokes analytics tools as needed
5. Response streams back to widget in chunks
6. Widget displays formatted analytics data

### Session Management

- Session ID generated on first connection
- Stored in localStorage for persistence
- Sent with every message for context
- Cleared on "Clear session" action
- Terminated on disconnect

## Analytics Data Formats

The widget recognizes and formats the following data types:

### Order Trends
```json
{
  "type": "order_trends",
  "summary": {
    "total_orders": 150,
    "total_revenue": 45000,
    "average_order_value": 300,
    "growth_rate": 12.5
  },
  "status_breakdown": {
    "pending": 10,
    "processing": 25,
    "shipped": 80,
    "delivered": 30,
    "cancelled": 5
  }
}
```

### Sales Insights
```json
{
  "type": "sales_insights",
  "top_products": [
    {
      "productId": "prod-123",
      "name": "Product Name",
      "category": "Electronics",
      "revenue": 5000,
      "units_sold": 50
    }
  ],
  "category_performance": {
    "Electronics": { "revenue": 15000 },
    "Clothing": { "revenue": 10000 }
  },
  "insights": [
    "Electronics category showing strong growth",
    "Product X is trending upward"
  ]
}
```

### Product Search
```json
{
  "type": "product_search",
  "products": [
    {
      "productId": "prod-123",
      "name": "Product Name",
      "description": "Product description",
      "category": "Electronics",
      "price": 99.99,
      "stock": 50
    }
  ],
  "total_results": 10
}
```

## Styling

The widget uses Tailwind CSS with the admin dashboard theme:

- **Primary Color**: Blue (`primary-600`)
- **Background**: White with gray accents
- **Borders**: Gray-200
- **Text**: Gray-900 for primary, Gray-500 for secondary
- **Shadows**: Consistent with dashboard components
- **Animations**: Smooth transitions and hover effects

## Error Handling

The widget handles various error scenarios:

1. **Connection Errors**: Displays error banner and attempts reconnection
2. **Authentication Errors**: Shows error message and prompts re-authentication
3. **Message Send Errors**: Queues messages and retries on reconnection
4. **Agent Errors**: Displays error messages in chat with error styling
5. **Network Errors**: Implements exponential backoff for reconnection

## Testing Checklist

- [ ] Widget appears on all admin pages
- [ ] Floating button is clickable and opens chat window
- [ ] Connection establishes successfully with valid credentials
- [ ] Messages can be sent and received
- [ ] Streaming responses display correctly
- [ ] Analytics data formats properly
- [ ] Product links navigate to correct pages
- [ ] Session persists across page navigation
- [ ] Clear session resets conversation
- [ ] Minimize/maximize works correctly
- [ ] Connection status updates accurately
- [ ] Error messages display appropriately
- [ ] Reconnection logic works after disconnect

## Deployment

### Prerequisites

1. AdminInsightsStack must be deployed
2. WebSocket API endpoint must be available
3. Agent Lambda must be configured with correct memory ID
4. Cognito authentication must be set up

### Steps

1. Update `.env` with WebSocket URL:
   ```bash
   VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
   ```

2. Build the admin dashboard:
   ```bash
   cd frontends/admin-dashboard
   npm install
   npm run build
   ```

3. Deploy to hosting (S3, CloudFront, etc.):
   ```bash
   # Example for S3
   aws s3 sync dist/ s3://your-admin-dashboard-bucket/
   ```

4. Test the widget:
   - Log in as admin user
   - Click chat button
   - Verify connection
   - Send test queries

## Troubleshooting

### Widget Not Appearing
- Check that Layout.jsx imports AdminInsightsWidget
- Verify widget is rendered in Layout component
- Check browser console for errors

### Connection Fails
- Verify VITE_ADMIN_INSIGHTS_WEBSOCKET_URL is set correctly
- Check that AdminInsightsStack is deployed
- Verify Cognito authentication is working
- Check browser console for WebSocket errors

### Messages Not Sending
- Verify connection status is "Connected"
- Check that session ID is being generated
- Look for errors in browser console
- Verify agent Lambda is running

### Analytics Not Formatting
- Check that agent is returning data in expected format
- Verify AnalyticsMessageFormatter is imported
- Look for JSON parsing errors in console
- Test with sample data

## Future Enhancements

Potential improvements for future iterations:

1. **Rich Media Support**: Images, charts, and graphs
2. **Export Functionality**: Download analytics data as CSV/PDF
3. **Saved Queries**: Quick access to common questions
4. **Notifications**: Alert when new insights are available
5. **Voice Input**: Speech-to-text for queries
6. **Multi-language**: Support for multiple languages
7. **Dark Mode**: Match dashboard theme preferences
8. **Mobile Optimization**: Better mobile experience

## Requirements Validation

This implementation satisfies the following requirements:

- ✅ **Requirement 1.1**: Agent processes requests and provides insights
- ✅ **Requirement 1.2**: Session context maintained across conversation
- ✅ **Requirement 1.4**: Responses formatted clearly and actionably
- ✅ **Requirement 2.1**: Order trends data displayed with metrics
- ✅ **Requirement 2.2**: Status distribution shown visually
- ✅ **Requirement 2.3**: Revenue trends formatted with currency
- ✅ **Requirement 3.1**: Top products ranked and linked
- ✅ **Requirement 3.2**: Product revenue displayed with formatting
- ✅ **Requirement 4.1**: Session initialized on connection
- ✅ **Requirement 4.2**: Messages persisted in session
- ✅ **Requirement 10.4**: WebSocket API integration complete

## Support

For issues or questions:
1. Check browser console for errors
2. Verify environment configuration
3. Review CloudWatch logs for agent Lambda
4. Check WebSocket API Gateway logs
5. Consult the design document for architecture details

---

**Implementation Date**: December 2024  
**Version**: 1.0.0  
**Status**: Complete ✅
