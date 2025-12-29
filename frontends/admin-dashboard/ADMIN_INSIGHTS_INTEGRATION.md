# Admin Insights Chat Widget Integration Plan

## Overview

This document outlines the implementation plan for integrating the Admin Insights Agent chat widget into the admin dashboard frontend. The implementation follows the same pattern as the customer-app chat widget but is tailored for admin-specific analytics queries.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Admin Dashboard (React App)                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         AdminInsightsWidget Component          │    │
│  │  - Floating chat button                        │    │
│  │  - Chat window (minimize/maximize)             │    │
│  │  - Message display with analytics formatting   │    │
│  │  - Input field with send button                │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
│  ┌────────────▼───────────────────────────────────┐    │
│  │      adminInsightsService.js                   │    │
│  │  - WebSocket connection management             │    │
│  │  - Authentication with Cognito JWT             │    │
│  │  - Session management                          │    │
│  │  - Message sending/receiving                   │    │
│  │  - Reconnection logic                          │    │
│  └────────────┬───────────────────────────────────┘    │
│               │                                          │
└───────────────┼──────────────────────────────────────────┘
                │ WebSocket (WSS)
                │
┌───────────────▼──────────────────────────────────────────┐
│         API Gateway (WebSocket API)                      │
│  - $connect (with Cognito authorizer)                   │
│  - $disconnect                                           │
│  - sendMessage                                           │
└───────────────┬──────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│      Admin Insights Agent Lambda Handler                │
│  - Bedrock AgentCore Runtime                            │
│  - Analytics Tools Invocation                           │
│  - Session Memory Management                            │
│  - Streaming Response                                    │
└──────────────────────────────────────────────────────────┘
```

## Implementation Components

### 1. Admin Insights Service (`src/services/adminInsights.js`)

**Purpose**: Manage WebSocket connection to the Admin Insights Agent backend.

**Key Features**:
- WebSocket connection with authentication
- Session management (localStorage-based)
- Message sending and receiving
- Reconnection with exponential backoff
- Connection status tracking

**API**:
```javascript
class AdminInsightsService {
  // Connection management
  async connect(handlers)
  disconnect()
  isConnected()
  
  // Messaging
  async sendMessage(content, metadata)
  
  // Session management
  getSessionId()
  clearSession()
  
  // History (localStorage-based)
  async loadHistory()
  saveToHistory(message)
}
```

**Environment Variables**:
- `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL`: WebSocket API endpoint

**Authentication**:
- Uses AWS Amplify `fetchAuthSession()` to get Cognito JWT token
- Token passed as query parameter: `?token=<jwt>&sessionId=<session_id>`

### 2. Admin Insights Widget Component (`src/components/AdminInsightsWidget.jsx`)

**Purpose**: UI component for the chat interface.

**States**:
- `isOpen`: Chat window open/closed
- `isMinimized`: Chat window minimized
- `messages`: Array of message objects
- `inputMessage`: Current input text
- `isConnected`: WebSocket connection status
- `isTyping`: Agent typing indicator
- `isSending`: Message sending in progress

**Message Format**:
```javascript
{
  id: string,           // Unique message ID
  role: string,         // 'user' | 'assistant' | 'system'
  content: string,      // Message text
  timestamp: number,    // Unix timestamp
  metadata: {           // Optional analytics data
    type: string,       // 'order_trends' | 'sales_insights' | 'product_search'
    data: object        // Tool-specific data
  }
}
```

**UI Features**:
- Floating button (bottom-right, blue theme)
- Chat window (400px wide, 600px tall)
- Header with connection status
- Minimize/maximize buttons
- Message list with auto-scroll
- Typing indicator (animated dots)
- Input field with send button
- Analytics data formatting (charts, tables, links)

**Styling**:
- Tailwind CSS classes
- Blue theme matching admin dashboard (`bg-blue-600`, `text-blue-600`)
- Responsive design
- Smooth animations

### 3. Analytics Message Formatting

**Order Trends Data**:
```javascript
// Display as table or chart
{
  type: 'order_trends',
  data: {
    time_series: [...],
    summary: { total_orders, total_revenue, growth_rate },
    status_breakdown: { pending: 10, shipped: 50, ... }
  }
}
```

**Sales Insights Data**:
```javascript
// Display with product links
{
  type: 'sales_insights',
  data: {
    top_products: [{ productId, name, revenue, units }],
    category_performance: {...},
    insights: [...]
  }
}
```

**Product Search Results**:
```javascript
// Display with admin product links
{
  type: 'product_search',
  data: {
    products: [{ productId, name, category, price }],
    total_results: 10
  }
}
```

### 4. Integration into Admin Dashboard

**App.jsx Changes**:
```javascript
import AdminInsightsWidget from './components/AdminInsightsWidget'

function App() {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <>
          <Layout user={user} signOut={signOut}>
            <Routes>
              {/* existing routes */}
            </Routes>
          </Layout>
          
          {/* Admin Insights Widget - always visible */}
          <AdminInsightsWidget />
        </>
      )}
    </Authenticator>
  )
}
```

**Layout.jsx Changes**:
- No changes needed - widget is rendered at App level
- Widget persists across all routes

### 5. Environment Configuration

**.env**:
```bash
# Existing variables
VITE_AWS_REGION=ap-southeast-1
VITE_USER_POOL_ID=ap-southeast-1_xxxxx
VITE_USER_POOL_CLIENT_ID=xxxxx
VITE_API_ENDPOINT=https://xxxxx.execute-api.ap-southeast-1.amazonaws.com/prod

# New variable for Admin Insights
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://xxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
```

**.env.example**:
```bash
VITE_AWS_REGION=ap-southeast-1
VITE_USER_POOL_ID=your-user-pool-id
VITE_USER_POOL_CLIENT_ID=your-user-pool-client-id
VITE_API_ENDPOINT=https://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://your-websocket-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
```

## Implementation Steps

### Step 1: Create Admin Insights Service (Task 15.1)

1. Create `frontends/admin-dashboard/src/services/adminInsights.js`
2. Implement `AdminInsightsService` class based on customer-app pattern
3. Add WebSocket connection with Cognito authentication
4. Implement session management with localStorage
5. Add reconnection logic with exponential backoff
6. Test connection and message flow

### Step 2: Create Admin Insights Widget Component (Task 15.2)

1. Create `frontends/admin-dashboard/src/components/AdminInsightsWidget.jsx`
2. Implement chat UI with floating button
3. Add message display with role-based styling
4. Implement minimize/maximize functionality
5. Add typing indicator
6. Style with Tailwind CSS (blue theme)
7. Test UI interactions

### Step 3: Integrate Widget into Dashboard (Task 15.3)

1. Import `AdminInsightsWidget` in `App.jsx`
2. Render widget at app level (outside Layout)
3. Test widget visibility on all pages
4. Verify widget persists across route changes
5. Test with authenticated admin users

### Step 4: Add Environment Configuration (Task 15.4)

1. Add `VITE_ADMIN_INSIGHTS_WEBSOCKET_URL` to `.env`
2. Update `.env.example` with new variable
3. Document configuration in README
4. Test with different environments

### Step 5: Implement Analytics Formatting (Task 15.5)

1. Create helper functions for formatting analytics data
2. Implement order trends visualization
3. Implement sales insights with product links
4. Implement product search results with admin links
5. Add visual indicators for data types
6. Test with sample analytics data

### Step 6: Testing (Tasks 15.6, 15.7)

1. Write unit tests for `adminInsightsService.js`
2. Write integration tests for `AdminInsightsWidget.jsx`
3. Test end-to-end message flow
4. Test error handling and reconnection
5. Test analytics data formatting

## Key Differences from Customer Chat

| Aspect | Customer Chat | Admin Insights Chat |
|--------|--------------|---------------------|
| **Purpose** | Product recommendations, order help | Business analytics, insights |
| **Backend** | Customer support agent | Admin insights agent |
| **Tools** | Product search, cart management, order query | Order trends, sales insights, product search |
| **Data Format** | Simple text, product recommendations | Complex analytics data (charts, tables) |
| **Authentication** | Customer Cognito pool | Admin Cognito pool |
| **Theme** | Blue (customer-facing) | Blue (admin-facing) |
| **Message Types** | Text, product links | Text, analytics data, visualizations |

## Testing Strategy

### Unit Tests
- WebSocket connection establishment
- Message sending and receiving
- Session management
- Reconnection logic
- Authentication token handling

### Integration Tests
- Widget rendering
- Message flow end-to-end
- Minimize/maximize functionality
- Connection error handling
- Analytics data formatting

### Manual Testing
1. Open admin dashboard
2. Click chat button
3. Send analytics queries:
   - "Show me order trends for the last week"
   - "What are the top selling products?"
   - "Search for products in Electronics category"
4. Verify analytics data displays correctly
5. Test minimize/maximize
6. Test reconnection after network interruption
7. Test across different admin pages

## Deployment Checklist

- [ ] Create `adminInsights.js` service
- [ ] Create `AdminInsightsWidget.jsx` component
- [ ] Integrate widget into `App.jsx`
- [ ] Add environment variables
- [ ] Implement analytics formatting
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update README with configuration
- [ ] Test in development environment
- [ ] Deploy to staging
- [ ] Test in staging environment
- [ ] Deploy to production

## Future Enhancements

1. **Rich Analytics Visualizations**
   - Chart.js integration for trends
   - Interactive tables for data exploration
   - Export data to CSV/Excel

2. **Advanced Features**
   - Voice input for queries
   - Scheduled reports
   - Alert notifications
   - Multi-session support

3. **Performance Optimizations**
   - Message pagination
   - Lazy loading of analytics data
   - Caching of frequent queries

4. **Accessibility**
   - Keyboard navigation
   - Screen reader support
   - High contrast mode

## References

- Customer chat implementation: `frontends/customer-app/src/components/ChatWidget.jsx`
- Customer chat service: `frontends/customer-app/src/services/chat.js`
- Admin Insights Agent design: `.kiro/specs/admin-insights-agent/design.md`
- Admin Insights Agent tasks: `.kiro/specs/admin-insights-agent/tasks.md`
