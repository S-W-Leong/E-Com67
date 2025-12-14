"""Database table names and other constants."""

# DynamoDB Table Names
USERS_TABLE = "e-com67-users"
PRODUCTS_TABLE = "e-com67-products"
ORDERS_TABLE = "e-com67-orders"
CART_TABLE = "e-com67-cart"
CHAT_HISTORY_TABLE = "e-com67-chat-history"

# Index Names
PRODUCTS_CATEGORY_INDEX = "category-index"
ORDERS_USER_TIMESTAMP_INDEX = "userId-timestamp-index"

# API Gateway
API_NAME = "e-com67-api"

# Cognito
USER_POOL_NAME = "e-com67-user-pool"
USER_POOL_CLIENT_NAME = "e-com67-client"

# SQS/SNS
ORDER_QUEUE_NAME = "e-com67-order-queue"
ORDER_DLQ_NAME = "e-com67-order-dlq"
ORDER_TOPIC_NAME = "e-com67-order-notifications"

# S3 Buckets
FRONTEND_BUCKET_PREFIX = "e-com67-frontend"
KNOWLEDGE_BASE_BUCKET_PREFIX = "e-com67-kb"

# Lambda Timeouts (in seconds)
LAMBDA_DEFAULT_TIMEOUT = 30
LAMBDA_LONG_TIMEOUT = 60

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_404_NOT_FOUND = 404
HTTP_500_INTERNAL_ERROR = 500
