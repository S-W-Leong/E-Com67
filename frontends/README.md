# E-Com67 Frontend Applications

This directory contains the dual-frontend architecture for the E-Com67 e-commerce platform.

## Architecture Overview

The platform uses separate frontend applications for different user roles, providing optimized experiences for each use case:

```
frontends/
├── admin-dashboard/    # Administrative interface for staff
├── customer-app/       # Customer-facing shopping experience
└── shared/            # Shared components and utilities
```

## Applications

### Admin Dashboard (`admin-dashboard/`)

Administrative interface for managing the e-commerce platform.

**Features:**
- Product management (CRUD operations)
- Order management and status updates
- Analytics dashboard
- User management

**Target Users:** Administrators, staff, operations team

**Deployment:** admin.yourdomain.com

[View Admin Dashboard README](./admin-dashboard/README.md)

### Customer Application (`customer-app/`)

Customer-facing shopping experience.

**Features:**
- Product browsing and search
- Shopping cart management
- Checkout and payment processing
- Order history and tracking
- AI-powered chat support

**Target Users:** Customers, shoppers

**Deployment:** shop.yourdomain.com

[View Customer App README](./customer-app/README.md)

### Shared Components (`shared/`)

Reusable components and utilities library.

**Contents:**
- UI components (Button, Input, Modal)
- API client with authentication
- Formatting utilities
- Validation helpers

**Usage:** Imported by both applications

[View Shared Library README](./shared/README.md)

## Technology Stack

All applications use:
- **React 18** - Modern React with hooks
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **AWS Amplify** - Authentication integration
- **Axios** - HTTP client

## Development Workflow

### Initial Setup

1. Install dependencies for all applications:
```bash
cd admin-dashboard && npm install
cd ../customer-app && npm install
cd ../shared && npm install
```

2. Configure environment variables in each application's `.env` file

### Running Applications

**Admin Dashboard:**
```bash
cd admin-dashboard
npm run dev
# Runs on http://localhost:3000
```

**Customer Application:**
```bash
cd customer-app
npm run dev
# Runs on http://localhost:3001
```

**Shared Library (watch mode):**
```bash
cd shared
npm run dev
```

### Building for Production

Build all applications:
```bash
cd admin-dashboard && npm run build
cd ../customer-app && npm run build
cd ../shared && npm run build
```

## Backend Integration

Both applications connect to the same backend infrastructure:

- **API Gateway**: REST API for products, cart, orders
- **WebSocket API**: Real-time chat functionality
- **Cognito**: User authentication and authorization
- **S3 + CloudFront**: Static hosting and CDN

### Authentication

Both applications use the same Cognito User Pool but with different redirect URLs:
- Admin: `https://admin.yourdomain.com/callback`
- Customer: `https://shop.yourdomain.com/callback`

Users are differentiated by Cognito user groups:
- `admin` group: Access to admin dashboard
- Regular users: Access to customer application

## Deployment

Each application is deployed separately:

### Admin Dashboard
- S3 bucket: `e-com67-admin-dashboard`
- CloudFront distribution: admin.yourdomain.com
- Restricted access (admin users only)

### Customer Application
- S3 bucket: `e-com67-customer-app`
- CloudFront distribution: shop.yourdomain.com
- Public access

### Deployment Process

1. Build the application
2. Upload to S3 bucket
3. Invalidate CloudFront cache
4. Verify deployment

See individual application READMEs for detailed deployment instructions.

## Code Sharing Strategy

### What Goes in Shared Library
- UI components used by both applications
- API client and authentication utilities
- Common formatting and validation functions
- Shared types and constants

### What Stays Application-Specific
- Page components and routing
- Application-specific business logic
- Role-specific features
- Application-specific styling overrides

## Best Practices

1. **Component Development**: Build components in the shared library first if they'll be used by both applications
2. **Styling**: Use Tailwind CSS classes consistently across applications
3. **API Integration**: Use the shared ApiClient for all backend communication
4. **Authentication**: Handle auth state consistently using AWS Amplify
5. **Error Handling**: Implement consistent error handling patterns
6. **Loading States**: Show loading indicators for async operations

## Testing

Each application should have its own test suite:
- Unit tests for components
- Integration tests for API calls
- E2E tests for critical workflows

## Contributing

When working on frontend features:

1. Determine if the feature is admin-specific, customer-specific, or shared
2. Place code in the appropriate directory
3. Update the relevant README
4. Test in both applications if using shared components
5. Follow the existing code style and patterns

## Architecture Decisions

### Why Separate Applications?

1. **Optimized User Experience**: Each application is tailored to its specific use case
2. **Independent Deployment**: Deploy admin and customer apps separately
3. **Security**: Easier to implement role-based access control
4. **Performance**: Smaller bundle sizes for each application
5. **Scalability**: Scale each application independently based on traffic

### Why Shared Library?

1. **Code Reuse**: Avoid duplicating common components
2. **Consistency**: Maintain consistent UI/UX across applications
3. **Maintainability**: Update shared code in one place
4. **Development Speed**: Faster feature development with reusable components

## Future Enhancements

- TypeScript migration for better type safety
- Storybook for component documentation
- Automated testing pipeline
- Performance monitoring and analytics
- Progressive Web App (PWA) features
- Internationalization (i18n) support