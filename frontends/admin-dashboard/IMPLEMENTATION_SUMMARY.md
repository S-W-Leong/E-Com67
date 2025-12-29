# Admin Insights Chat Widget - Implementation Summary

## What We're Building

A real-time chat widget for the admin dashboard that connects to the Admin Insights Agent backend via WebSocket. Admins can ask natural language questions about business metrics and receive analytics insights.

## Quick Overview

**Pattern**: Same as customer-app chat widget, but for admin analytics
**Location**: `frontends/admin-dashboard/`
**Backend**: Admin Insights Agent (WebSocket API)
**Authentication**: Cognito JWT tokens (admin pool)

## Files to Create

```
frontends/admin-dashboard/
├── src/
│   ├── services/
│   │   └── adminInsights.js          # WebSocket service (NEW)
│   └── components/
│       └── AdminInsightsWidget.jsx   # Chat UI component (NEW)
├── .env                               # Add VITE_ADMIN_INSIGHTS_WEBSOCKET_URL
└── ADMIN_INSIGHTS_INTEGRATION.md     # Detailed implementation guide (CREATED)
```

## Files to Modify

```
frontends/admin-dashboard/
├── src/
│   └── App.jsx                        # Add <AdminInsightsWidget />
└── .env.example                       # Document new env variable
```

## Implementation Flow

### 1. Service Layer (`adminInsights.js`)
- WebSocket connection management
- Cognito JWT authentication
- Session management (localStorage)
- Message sending/receiving
- Reconnection with exponential backoff

### 2. UI Component (`AdminInsightsWidget.jsx`)
- Floating chat button (bottom-right)
- Chat window (minimize/maximize)
- Message display with analytics formatting
- Typing indicators
- Connection status

### 3. Integration (`App.jsx`)
- Render widget at app level
- Persists across all routes
- Always visible when authenticated

### 4. Analytics Formatting
- Order trends → tables/charts
- Sales insights → product links
- Product search → admin links

## Key Differences from Customer Chat

| Customer Chat | Admin Insights Chat |
|--------------|---------------------|
| Product recommendations | Business analytics |
| Simple text responses | Complex data visualizations |
| Customer support queries | Analytics queries |
| Customer Cognito pool | Admin Cognito pool |

## Example Queries

```
User: "Show me order trends for the last week"
Agent: [Displays table with daily order volumes, revenue, growth rates]

User: "What are the top selling products?"
Agent: [Displays ranked list with product links, revenue, units sold]

User: "Search for products in Electronics"
Agent: [Displays product list with admin edit links]
```

## Environment Configuration

Add to `.env`:
```bash
VITE_ADMIN_INSIGHTS_WEBSOCKET_URL=wss://xxxxx.execute-api.ap-southeast-1.amazonaws.com/prod
```

## Testing Approach

1. **Unit Tests**: Service methods, connection logic
2. **Integration Tests**: Widget interactions, message flow
3. **Manual Tests**: End-to-end analytics queries

## Task Breakdown (from tasks.md)

- **Task 15.1**: Create adminInsights.js service
- **Task 15.2**: Create AdminInsightsWidget component
- **Task 15.3**: Integrate into App.jsx
- **Task 15.4**: Add environment configuration
- **Task 15.5**: Implement analytics formatting
- **Task 15.6**: Write unit tests (optional)
- **Task 15.7**: Write integration tests (optional)

## Next Steps

1. Review `ADMIN_INSIGHTS_INTEGRATION.md` for detailed implementation guide
2. Start with Task 15.1 (create service)
3. Follow the implementation steps in order
4. Test each component before moving to the next

## Reference Files

- **Customer chat widget**: `frontends/customer-app/src/components/ChatWidget.jsx`
- **Customer chat service**: `frontends/customer-app/src/services/chat.js`
- **Detailed plan**: `frontends/admin-dashboard/ADMIN_INSIGHTS_INTEGRATION.md`
- **Backend design**: `.kiro/specs/admin-insights-agent/design.md`
- **Task list**: `.kiro/specs/admin-insights-agent/tasks.md`

## Timeline Estimate

- Service layer: 2-3 hours
- UI component: 3-4 hours
- Integration: 1 hour
- Analytics formatting: 2-3 hours
- Testing: 2-3 hours
- **Total**: ~10-15 hours

## Success Criteria

✅ Admin can open chat widget from any page
✅ Admin can send analytics queries
✅ Agent responds with formatted analytics data
✅ Widget persists across route changes
✅ Connection handles errors gracefully
✅ Analytics data displays with proper formatting
✅ All tests pass
