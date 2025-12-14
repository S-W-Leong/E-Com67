# 🛍️ E-Com67 - Serverless E-Commerce Platform

A monorepo project implementing a full-stack serverless e-commerce platform on AWS using CDK, Lambda, DynamoDB, Cognito, and React.

---

## 📁 Project Structure

```
e-com67/
├── backend/                          # AWS CDK Infrastructure & Lambda Functions
│   ├── app.py                        # CDK app entry point
│   ├── e_com67/                      # CDK stack definitions
│   ├── lambda/                       # Lambda function handlers
│   │   ├── products/                 # Product CRUD operations
│   │   ├── cart/                     # Shopping cart operations
│   │   ├── payment/                  # Payment processing
│   │   ├── order_processor/          # Order processing from SQS
│   │   └── layers/                   # Lambda layers (shared code)
│   ├── tests/                        # Backend unit tests
│   ├── docs/                         # Backend documentation
│   ├── requirements.txt              # Python dependencies
│   ├── requirements-dev.txt          # Dev dependencies
│   └── cdk.json                      # CDK configuration
│
├── frontend/                         # React Frontend Application
│   ├── src/
│   │   ├── pages/                    # Page components (Login, Products, Cart, etc)
│   │   ├── components/               # Reusable components (Navbar, etc)
│   │   ├── services/                 # API clients and utilities
│   │   ├── App.js                    # Main app component
│   │   └── index.js                  # React entry point
│   ├── public/                       # Static assets
│   ├── package.json                  # Node dependencies
│   └── .env.local                    # Environment variables (not in git)
│
├── shared/                           # Shared utilities between frontend and backend
│   ├── constants/                    # Shared constants (table names, etc)
│   ├── types/                        # Type definitions
│   └── __init__.py
│
└── docs/                             # Root documentation
    ├── guide.md                      # Full architecture guide
    ├── frontend-setup.md             # Frontend setup instructions
    └── todo.md                       # Project todo list
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 16+
- Python 3.9+
- AWS Account & AWS CLI configured
- Git

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local file with values from CDK outputs
echo "REACT_APP_API_ENDPOINT=your-api-endpoint" > .env.local
echo "REACT_APP_USER_POOL_ID=your-user-pool-id" >> .env.local
echo "REACT_APP_USER_POOL_CLIENT_ID=your-client-id" >> .env.local

# Start development server
npm start
```

---

## 📚 Documentation

- **[Architecture Guide](backend/docs/guide.md)** - Complete system design and component breakdown
- **[Frontend Setup](backend/docs/frontend-setup.md)** - Detailed React frontend setup instructions
- **[Todo List](backend/docs/todo.md)** - Project milestones and tasks

---

## 🔧 Key Technologies

### Backend
- **AWS CDK** - Infrastructure as Code
- **Lambda** - Serverless compute
- **DynamoDB** - NoSQL database
- **Cognito** - User authentication
- **API Gateway** - REST API management
- **SQS/SNS** - Message queuing and notifications
- **OpenSearch** - Full-text search
- **S3** - Object storage
- **Step Functions** - Workflow orchestration

### Frontend
- **React 18** - UI framework
- **Amplify** - AWS SDK for frontend
- **Tailwind CSS** - Styling
- **React Router** - Navigation

### Shared
- **Python Type Hints** - Type definitions
- **Shared Constants** - Configuration values

---

## 💼 Architecture Highlights

### Authentication Flow
```
User → React (Amplify Auth) → Cognito → JWT Token → API Gateway Authorizer
                                    ↓
                    Post-Auth Trigger → Lambda → DynamoDB (save user profile)
```

### Checkout Flow
```
User clicks "Place Order" → API Gateway → Step Function
  ├─ Step 1: Validate Cart (Lambda)
  ├─ Step 2: Process Payment (Lambda → Stripe) [with retry]
  └─ Step 3: Success → Send to SQS

SQS → Lambda Consumer
  ├─ Create Order in DynamoDB
  ├─ Clear Cart
  ├─ Update Product Stock
  └─ Trigger SNS → SES (send email)
```

---

## 🛠️ Development Workflow

### Backend Changes
```bash
cd backend

# Make changes to CDK or Lambda code
# ...

# Synthesize and review CloudFormation template
cdk synth

# Deploy changes
cdk deploy

# View logs
cdk logs
```

### Frontend Changes
```bash
cd frontend

# Make changes to React components
# ...

# Run development server with hot reload
npm start

# Build for production
npm run build
```

### Shared Code Changes
Changes to `/shared` can be imported in:
- **Backend**: `from shared.constants import PRODUCTS_TABLE`
- **Frontend**: `import { PRODUCTS_TABLE } from '../../shared/constants'` (after build step)

---

## 🧪 Testing

### Backend Unit Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests (Coming Soon)
```bash
cd frontend
npm test
```

---

## 📊 Project Status

- [x] Architecture designed
- [x] Backend infrastructure (CDK)
- [x] Database schemas
- [x] Cognito authentication
- [x] API Gateway setup
- [x] Frontend React app structure
- [ ] Lambda functions implementation
- [ ] Integration testing
- [ ] CI/CD pipeline
- [ ] Production deployment

See [todo list](backend/docs/todo.md) for detailed tasks.

---

## 🤝 Contributing

1. Make changes in appropriate directory (backend, frontend, or shared)
2. Commit with descriptive messages
3. Test before pushing
4. Create pull requests for major changes

---

## 📝 Notes

- **Development Only**: CDK RemovalPolicy set to DESTROY; adjust for production
- **Environment Variables**: Never commit `.env.local` files
- **AWS Costs**: Monitor costs; some services may incur charges
- **Secrets**: Store Stripe API keys in AWS Secrets Manager, not in code

---

## 📞 Support

Refer to individual README files:
- [Backend README](backend/README.md) (if exists)
- [Frontend README](frontend/README.md) (if exists)

---

Happy coding! 🚀

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
