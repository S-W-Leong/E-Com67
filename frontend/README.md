# E-Com67 Frontend

Modern e-commerce frontend built with React, Vite, Tailwind CSS, and AWS Amplify.

## Features

- 🔐 **Authentication**: Cognito-based signup/login with email verification
- 🛍️ **Product Browsing**: Category filtering and search functionality
- 🛒 **Shopping Cart**: Add, remove, update quantities
- 💳 **Checkout**: Mock Stripe payment integration
- 📦 **Order History**: View past orders and details
- 💬 **AI Chat**: WebSocket-based AI shopping assistant (demo mode)
- 📱 **Responsive Design**: Mobile-first Tailwind CSS design
- ⚡ **Fast**: Built with Vite for lightning-fast development

## Tech Stack

- **React 18** - UI framework
- **Vite 5** - Build tool and dev server
- **Tailwind CSS 3** - Utility-first CSS framework
- **AWS Amplify v6** - AWS authentication and API integration
- **React Router v6** - Client-side routing
- **Axios** - HTTP client
- **React Hot Toast** - Toast notifications

## Prerequisites

- Node.js 18+ and npm
- AWS account with deployed backend (CDK stack)
- Environment variables configured in root `.env.local`

## Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Environment Variables

The frontend uses environment variables from the root `.env.local` file with `VITE_` prefix:

```env
VITE_AWS_REGION=ap-southeast-1
VITE_API_GATEWAY_ENDPOINT=https://your-api.execute-api.region.amazonaws.com/prod/
VITE_COGNITO_USER_POOL_ID=region_xxxxx
VITE_COGNITO_APP_CLIENT_ID=xxxxx
```

These are already configured in your root `.env.local` file.

## Development

```bash
# Start development server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable components
│   │   ├── Navbar.jsx
│   │   ├── ProductCard.jsx
│   │   ├── SearchBar.jsx
│   │   ├── ChatWidget.jsx
│   │   ├── ErrorBoundary.jsx
│   │   └── LoadingSpinner.jsx
│   ├── pages/           # Page components
│   │   ├── Login.jsx
│   │   ├── Products.jsx
│   │   ├── Cart.jsx
│   │   ├── Checkout.jsx
│   │   ├── Orders.jsx
│   │   └── NotFound.jsx
│   ├── services/        # API and services
│   │   ├── api.js
│   │   └── websocket.js
│   ├── config/          # Configuration
│   │   └── aws-config.js
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Key Features

### Authentication Flow
- Sign up with email and password
- Email verification via Cognito
- Automatic session management
- Protected routes

### Product Management
- Browse all products or filter by category
- Search products by name/description
- Add products to cart
- View product details

### Shopping Cart
- Add/remove items
- Update quantities
- Real-time price calculations
- Persistent cart state

### Checkout
- Mock Stripe payment form
- Order summary
- Tax and total calculation
- Order confirmation

### AI Chat Widget
- Floating chat button
- Real-time messaging (demo mode)
- Mock AI responses
- Chat history

## API Integration

The app integrates with the AWS backend via:

- **API Gateway REST API**: Product, cart, and order operations
- **Cognito**: User authentication
- **WebSocket API**: AI chat (coming soon)

All API calls are authenticated using JWT tokens from Cognito.

## Styling

The app uses Tailwind CSS with custom utility classes:

- `btn-primary` - Primary button style
- `btn-secondary` - Secondary button style
- `btn-danger` - Danger button style
- `input-field` - Form input style
- `card` - Card container style
- `gradient-bg` - Gradient background
- `gradient-text` - Gradient text

## Error Handling

- Error Boundary for React errors
- Toast notifications for user feedback
- 404 page for unknown routes
- Loading states for async operations

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

## Deployment

Deploy to AWS S3:

```bash
# Build the app
npm run build

# Deploy to S3 (replace with your bucket name)
aws s3 sync dist/ s3://your-bucket-name --delete
```

## Troubleshooting

### Environment Variables Not Loading
- Ensure `.env.local` is in the root directory
- Restart the dev server after changing env vars
- Verify variables have `VITE_` prefix

### Authentication Issues
- Check Cognito User Pool ID and Client ID
- Ensure region matches your AWS setup
- Clear browser cache and cookies

### API Errors
- Verify API Gateway endpoint is correct
- Check that backend Lambda functions are deployed
- Review browser console for detailed errors

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

MIT
