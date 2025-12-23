# E-Com67 Customer Application

A React-based customer-facing shopping application for the E-Com67 e-commerce platform. This is part of the dual-frontend architecture, specifically designed for customers to browse products, manage their cart, and complete purchases.

## Architecture

This customer application is part of the E-Com67 dual-frontend architecture:

- **Admin Dashboard** (`frontends/admin-dashboard/`): Administrative interface for staff
- **Customer Application** (`frontends/customer-app/`): This application - customer shopping experience  
- **Shared Components** (`frontends/shared/`): Reusable components and utilities

Both applications connect to the same backend infrastructure but provide role-specific user experiences.

## Features

### Product Browsing
- Browse all products with grid and list views
- Filter by category and price range
- Sort by name, price, and rating
- Search functionality with real-time results
- Detailed product pages with images and descriptions

### Shopping Experience
- Add products to shopping cart
- Manage cart items (update quantities, remove items)
- Secure checkout process with payment integration
- Order confirmation and tracking

### User Account
- User registration and authentication via AWS Cognito
- Customer profile management
- Order history and tracking
- Account settings and preferences

### AI Chat Support
- Real-time chat widget with WebSocket connection
- AI-powered product recommendations in chat
- Typing indicators and message history
- Chat session persistence across page refreshes
- Minimizable and closable chat window
- Order assistance and FAQ support

## Technology Stack

- **React 18** - Modern React with hooks
- **Vite** - Fast build tool and dev server (runs on port 3001)
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **AWS Amplify** - Authentication and API integration
- **Axios** - HTTP client for API calls
- **Lucide React** - Beautiful icons
- **@e-com67/shared** - Shared components library

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- AWS account with deployed E-Com67 backend

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
Copy `.env.example` to `.env` and update the values:
```bash
VITE_AWS_REGION=ap-southeast-1
VITE_USER_POOL_ID=your-user-pool-id
VITE_USER_POOL_CLIENT_ID=your-user-pool-client-id
VITE_API_ENDPOINT=https://your-api-id.execute-api.ap-southeast-1.amazonaws.com/prod
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3001`.

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Layout.jsx      # Main layout with navigation and footer
│   ├── ChatWidget.jsx  # AI chat widget component
│   ├── ProductCard.jsx # Product display card
│   └── SearchBar.jsx   # Search with autocomplete
├── pages/              # Page components
│   ├── Home.jsx        # Landing page with featured products
│   ├── Products.jsx    # Product listing with filters
│   ├── ProductDetail.jsx # Individual product details
│   ├── Cart.jsx        # Shopping cart management
│   ├── Checkout.jsx    # Checkout process
│   ├── Orders.jsx      # Order history and detail view
│   └── Profile.jsx     # User profile management
├── services/           # API and utility services
│   ├── api.js         # REST API service layer
│   └── chat.js        # WebSocket chat service
├── context/            # React context providers (future)
├── App.jsx            # Main app component with routing
├── main.jsx           # App entry point with Amplify config
└── index.css          # Global styles and Tailwind imports
```

## Authentication

The application uses AWS Cognito for authentication with the following features:

- **Email-based registration** with verification codes
- **Secure login** with JWT tokens
- **Guest browsing** for public product pages
- **Protected routes** for cart, checkout, and account pages
- **Password requirements**: 8+ characters with uppercase, lowercase, and numbers

### User Flow

1. **Guest Users**: Can browse products and view details
2. **Registration**: Required for cart and checkout functionality
3. **Login**: Persistent sessions with automatic token refresh
4. **Protected Features**: Cart, checkout, orders, and profile require authentication

## API Integration

The application communicates with the E-Com67 backend through REST APIs:

- **Products API**: Browse and search products
- **Cart API**: Manage shopping cart items
- **Orders API**: Place orders and view history
- **Search API**: Real-time product search
- **WebSocket API**: Real-time chat support

All API calls are authenticated using JWT tokens from Cognito when required.

## Pages Overview

### Home Page (`/`)
- Hero section with call-to-action
- Featured products showcase
- Key features and benefits
- Newsletter signup
- **Status**: ✅ Implemented

### Products Page (`/products`)
- Product grid and list views
- Real-time search with autocomplete suggestions
- Category and price filtering
- Sorting options (name, price, rating)
- Pagination with "Load More" functionality
- Add to cart directly from listings
- Responsive design for mobile
- **Status**: ✅ Implemented (Phase 9.3)

### Product Detail Page (`/products/:id`)
- Detailed product information
- Full product images and details
- Add to cart functionality with quantity selector
- Stock availability indicators
- Buy now option
- Related products section
- **Status**: ✅ Implemented (Phase 9.3)

### Shopping Cart (`/cart`)
- Cart item management with real-time updates
- Quantity controls (increase/decrease)
- Remove items with confirmation
- Price calculations with tax
- Order summary with sticky sidebar
- Empty cart state with CTA
- **Status**: ✅ Implemented (Phase 9.4)

### Checkout (`/checkout`)
- Two-step checkout process (Shipping → Payment)
- Comprehensive shipping information form with validation
- Stripe Elements payment integration
- Order summary with cart items
- Free shipping calculation (orders over $50)
- Progress indicator
- **Status**: ✅ Implemented (Phase 9.4)

### Order History (`/orders`)
- List of customer orders with pagination
- Order status tracking with visual badges
- Detailed order view with items and shipping
- Order detail routing (`/orders/:id`)
- Success message display from checkout
- Empty state for no orders
- **Status**: ✅ Implemented (Phase 9.5)

### Profile (`/profile`)
- Three-tab interface (Profile, Security, Notifications)
- Account information management with Cognito integration
- Password change with validation
- Email and SMS notification preferences
- Success/error message handling
- **Status**: ✅ Implemented (Phase 9.5)

## Styling

The application uses Tailwind CSS with a custom design system:

- **Primary Color**: Blue (#2563eb)
- **Background**: Light gray (#f9fafb)
- **Cards**: White with subtle shadows
- **Typography**: System font stack
- **Responsive**: Mobile-first approach
- **Components**: Consistent spacing and interactions

### Custom CSS Classes

```css
.btn-primary     # Blue primary button
.btn-secondary   # Gray secondary button
.card           # White card with shadow
.input-field    # Styled form input
```

## Development Guidelines

### Component Development
- Use functional components with hooks
- Implement proper loading states for async operations
- Add error boundaries for better user experience
- Follow React best practices and patterns

### State Management
- Use React hooks for local state
- Consider Context API for global state (cart, user)
- Implement proper error handling
- Add loading indicators for better UX

### API Integration
- Use the shared ApiClient from `@e-com67/shared`
- Implement proper error handling and retry logic
- Add loading states for all async operations
- Handle authentication token management

## Deployment

The customer application will be deployed to:

- **S3 Bucket**: `e-com67-customer-app`
- **CloudFront Distribution**: shop.yourdomain.com
- **Environment**: Production and staging environments
- **CI/CD**: Automated deployment pipeline (Phase 10.3)

### Deployment Process

1. Build the application (`npm run build`)
2. Upload to S3 bucket
3. Invalidate CloudFront cache
4. Verify deployment and functionality

## Implementation Roadmap

### Phase 9.1: ✅ Completed
- [x] Set up project structure and basic configuration
- [x] Create shared components library
- [x] Implement basic layout and navigation
- [x] Set up routing and authentication

### Phase 9.2: ✅ Completed
- [x] Create customer application foundation
- [x] Implement home page with featured products
- [x] Set up product listing with filters and search
- [x] Configure AWS Amplify authentication

### Phase 9.3: ✅ Completed
- [x] Implement product browsing with grid/list layouts
- [x] Add real-time search with autocomplete
- [x] Create ProductCard component for reusability
- [x] Implement product detail pages with full details
- [x] Add add-to-cart functionality with quantity management
- [x] Set up pagination with "Load More"
- [x] Add category navigation and filtering
- [x] Implement related products feature

### Phase 9.4: ✅ Completed
- [x] Build shopping cart management with item updates
- [x] Implement two-step checkout process
- [x] Integrate Stripe Elements for payment processing
- [x] Add shipping information form with validation
- [x] Implement order summary and totals calculation
- [x] Add free shipping threshold logic

### Phase 9.5: ✅ Completed
- [x] Create customer account management
- [x] Implement order history and tracking
- [x] Add profile management features with Cognito integration
- [x] Set up notification preferences
- [x] Implement order detail view component
- [x] Add password change functionality

### Phase 9.6: ✅ Completed
- [x] Integrate AI chat widget with floating button
- [x] Add real-time WebSocket messaging
- [x] Implement typing indicators and message display
- [x] Set up chat history management with localStorage
- [x] Add chat session persistence and restoration
- [x] Implement product recommendation display in chat
- [x] Add minimize/maximize chat functionality
- [x] Configure reconnection with exponential backoff

## Testing

Future testing implementation will include:

- **Unit Tests**: Component testing with Jest and React Testing Library
- **Integration Tests**: API integration and user flow testing
- **E2E Tests**: Critical user journeys with Cypress
- **Performance Tests**: Load testing and optimization

## Contributing

When working on customer application features:

1. Follow the existing code structure and patterns
2. Use shared components from `@e-com67/shared` when possible
3. Implement proper error handling and loading states
4. Test on both desktop and mobile devices
5. Update this README when adding new features

## Security Considerations

- **Authentication**: All sensitive operations require user authentication
- **API Security**: JWT tokens for authenticated requests
- **Input Validation**: Client-side validation with server-side verification
- **XSS Protection**: Proper input sanitization and output encoding
- **HTTPS**: All communication over secure connections

## Performance Optimization

- **Code Splitting**: Lazy loading for route components
- **Image Optimization**: Responsive images with proper sizing
- **Caching**: Proper cache headers and CDN utilization
- **Bundle Size**: Regular analysis and optimization
- **Loading States**: Skeleton screens and progress indicators

## Browser Support

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **Mobile**: iOS Safari, Chrome Mobile
- **Responsive**: Mobile-first design approach
- **Progressive Enhancement**: Graceful degradation for older browsers

## License

This project is part of the E-Com67 platform and follows the same licensing terms.