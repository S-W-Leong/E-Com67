# E-Com67 Admin Dashboard

A React-based admin dashboard for managing the E-Com67 e-commerce platform.

## Features

### Product Management
- View all products with filtering and search
- Add new products with comprehensive form validation
- Edit existing products
- Delete products with confirmation
- Category-based organization
- Stock level monitoring
- Product analytics overview

### Order Management
- View all customer orders
- Filter orders by status
- Search orders by ID or customer
- Update order status
- View detailed order information
- Order analytics and metrics

### Dashboard Analytics
- Key performance metrics
- Recent orders overview
- Product inventory status
- Revenue tracking

## Technology Stack

- **React 18** - Modern React with hooks
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **AWS Amplify** - Authentication and API integration
- **Axios** - HTTP client for API calls
- **Lucide React** - Beautiful icons

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

The application will be available at `http://localhost:3000`.

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── components/          # Reusable UI components
│   └── Layout.jsx      # Main layout with navigation
├── pages/              # Page components
│   ├── Dashboard.jsx   # Main dashboard
│   ├── Products.jsx    # Product management
│   ├── ProductForm.jsx # Add/edit product form
│   └── Orders.jsx      # Order management
├── services/           # API and utility services
│   └── api.js         # API client and endpoints
├── App.jsx            # Main app component
├── main.jsx           # App entry point
└── index.css          # Global styles
```

## Authentication

The application uses AWS Cognito for authentication. Users must be in the `admin` group to access admin-specific features.

### Setting up Admin Users

1. Create a user in your Cognito User Pool
2. Add the user to the `admin` group
3. The user can then log in to the admin dashboard

## API Integration

The dashboard communicates with the E-Com67 backend through REST APIs:

- **Products API**: CRUD operations for product management
- **Orders API**: Order retrieval and status updates
- **Search API**: Product search functionality

All API calls are authenticated using JWT tokens from Cognito.

## Features in Detail

### Product Management
- **List View**: Paginated table with search and filtering
- **Add Product**: Comprehensive form with validation
- **Edit Product**: Pre-populated form for updates
- **Delete Product**: Soft delete with confirmation
- **Categories**: Predefined categories for organization
- **Stock Tracking**: Visual indicators for stock levels

### Order Management
- **Order List**: Sortable table with status filters
- **Status Updates**: Admin can change order status
- **Order Details**: Modal with complete order information
- **Search**: Find orders by ID or customer
- **Analytics**: Order statistics and metrics

### Dashboard
- **Metrics Cards**: Key performance indicators
- **Recent Orders**: Latest order activity
- **Quick Actions**: Navigation to main features
- **Analytics Overview**: Business insights

## Styling

The application uses Tailwind CSS for styling with a custom design system:

- **Colors**: Primary blue theme with semantic colors
- **Components**: Reusable component classes
- **Responsive**: Mobile-first responsive design
- **Dark Mode**: Ready for dark mode implementation

## Development

### Code Style
- Use functional components with hooks
- Follow React best practices
- Use TypeScript-style prop validation
- Implement proper error handling

### Testing
- Unit tests for components (to be implemented)
- Integration tests for API calls (to be implemented)
- E2E tests for critical workflows (to be implemented)

## Deployment

The frontend can be deployed to:
- **AWS S3 + CloudFront**: Static hosting with CDN
- **Vercel**: Automatic deployments from Git
- **Netlify**: JAMstack deployment platform

## Contributing

1. Follow the existing code style
2. Add proper error handling
3. Include loading states for async operations
4. Test thoroughly before submitting
5. Update documentation as needed

## License

This project is part of the E-Com67 platform and follows the same licensing terms.