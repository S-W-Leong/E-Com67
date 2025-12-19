# E-Com67 Platform API Endpoints

This document describes the REST API endpoints configured in the E-Com67 platform.

## Base URL

The API base URL will be provided in the CloudFormation stack outputs after deployment:
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```

## Authentication

The API uses Amazon Cognito User Pools for authentication. Protected endpoints require:
- `Authorization` header with JWT token from Cognito
- Admin endpoints additionally require the user to be in the `admin` group

## Endpoints

### Product Management

#### Public Endpoints (No Authentication Required)

**GET /products**
- Description: List all products with optional filtering
- Query Parameters:
  - `category` (optional): Filter by product category
  - `limit` (optional): Number of products to return (default: 20)
  - `offset` (optional): Pagination offset
- Response: Array of product objects

**GET /products/{id}**
- Description: Get detailed information about a specific product
- Path Parameters:
  - `id`: Product ID
- Response: Product object or 404 if not found

**GET /search**
- Description: Search products by name, description, or tags
- Query Parameters:
  - `q`: Search query string
  - `category` (optional): Filter by category
  - `limit` (optional): Number of results to return
- Response: Array of matching product objects

#### Admin Endpoints (Authentication + Admin Role Required)

**POST /products**
- Description: Create a new product
- Request Body: Product object with name, description, price, category, etc.
- Response: Created product object with generated ID

**PUT /products/{id}**
- Description: Update an existing product
- Path Parameters:
  - `id`: Product ID
- Request Body: Updated product fields
- Response: Updated product object

**DELETE /products/{id}**
- Description: Delete a product
- Path Parameters:
  - `id`: Product ID
- Response: 204 No Content on success

**GET /admin/products**
- Description: List all products with admin-specific details (inventory, analytics, etc.)
- Response: Array of product objects with extended information

### Shopping Cart Management

#### User Endpoints (Authentication Required)

**GET /cart**
- Description: Get current user's cart contents
- Response: Array of cart items with product details and quantities

**POST /cart**
- Description: Add or update item in cart
- Request Body:
  ```json
  {
    "productId": "string",
    "quantity": number
  }
  ```
- Response: Updated cart item

**DELETE /cart**
- Description: Remove item from cart
- Query Parameters:
  - `productId`: ID of product to remove
- Response: 204 No Content on success

### Order Management

#### User Endpoints (Authentication Required)

**GET /orders**
- Description: Get user's order history
- Query Parameters:
  - `limit` (optional): Number of orders to return
  - `offset` (optional): Pagination offset
- Response: Array of order objects

**POST /orders**
- Description: Place a new order (triggers checkout workflow)
- Request Body:
  ```json
  {
    "paymentMethodId": "string",
    "shippingAddress": {
      "street": "string",
      "city": "string",
      "state": "string",
      "zipCode": "string",
      "country": "string"
    }
  }
  ```
- Response: Order execution details from Step Functions

**GET /orders/{id}**
- Description: Get detailed information about a specific order
- Path Parameters:
  - `id`: Order ID
- Response: Order object with items, status, and tracking information

#### Admin Endpoints (Authentication + Admin Role Required)

**GET /admin/orders**
- Description: List all orders with admin-specific details
- Query Parameters:
  - `status` (optional): Filter by order status
  - `limit` (optional): Number of orders to return
  - `offset` (optional): Pagination offset
- Response: Array of order objects with extended information

**PUT /admin/orders/{id}**
- Description: Update order status
- Path Parameters:
  - `id`: Order ID
- Request Body:
  ```json
  {
    "status": "PROCESSING|SHIPPED|DELIVERED|CANCELLED"
  }
  ```
- Response: Updated order object

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error details"
    }
  }
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `204`: No Content
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error

## CORS Configuration

The API is configured with CORS to allow requests from web browsers:
- Allowed Origins: All origins (restrict in production)
- Allowed Methods: All HTTP methods
- Allowed Headers: Standard headers plus Authorization
- Credentials: Allowed

## Rate Limiting

API Gateway is configured with:
- Rate limit: 1000 requests per second
- Burst limit: 2000 requests

## Monitoring and Logging

- CloudWatch logging enabled for all requests
- X-Ray tracing enabled for distributed tracing
- Custom metrics for business analytics
- Access logs in JSON format

## WebSocket API

### Real-Time Chat

The platform includes a WebSocket API for real-time chat functionality:

**WebSocket URL**: `wss://{websocket-api-id}.execute-api.{region}.amazonaws.com/prod`

#### Routes

**$connect**
- Description: Establish WebSocket connection
- Response: Connection confirmation message

**$disconnect**
- Description: Clean up WebSocket connection
- Response: Disconnection confirmation

**sendMessage**
- Description: Send chat message (placeholder implementation)
- Message Format:
  ```json
  {
    "action": "sendMessage",
    "message": "Hello, I need help with my order"
  }
  ```
- Response: Echo message with placeholder AI response

*Note: Full AI chat functionality will be implemented in Phase 6 with Amazon Bedrock integration.*

## Next Steps

This API configuration provides the foundation for:
1. Frontend React application integration
2. Full AI chat implementation with Amazon Bedrock (Phase 6)
3. OpenSearch integration for advanced search (Phase 5)
4. Additional admin endpoints for analytics and reporting