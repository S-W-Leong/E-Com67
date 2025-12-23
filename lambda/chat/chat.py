"""
E-Com67 Platform Chat Function

AI-powered customer support using Amazon Bedrock with retrieval-augmented generation.
Handles WebSocket connections and provides product recommendations and support.
"""

import json
import boto3
import logging
import os
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients (will be initialized lazily)
dynamodb = None
bedrock_runtime = None
apigateway_management = None  # Will be initialized per request

# Environment variables
CHAT_HISTORY_TABLE_NAME = os.environ.get('CHAT_HISTORY_TABLE_NAME')
PRODUCTS_TABLE_NAME = os.environ.get('PRODUCTS_TABLE_NAME')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.titan-text-express-v1')

# DynamoDB tables (will be initialized lazily)
chat_history_table = None
products_table = None


def _initialize_aws_clients():
    """Initialize AWS clients lazily to avoid issues during testing"""
    global dynamodb, bedrock_runtime, chat_history_table, products_table
    
    if dynamodb is None:
        dynamodb = boto3.resource('dynamodb')
        chat_history_table = dynamodb.Table(CHAT_HISTORY_TABLE_NAME)
        products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)
    
    if bedrock_runtime is None:
        bedrock_runtime = boto3.client('bedrock-runtime')


class ChatError(Exception):
    """Custom exception for chat-related errors"""
    pass


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main handler for WebSocket chat events.
    
    Handles connection management and message processing for AI chat.
    """
    try:
        # Initialize AWS clients
        _initialize_aws_clients()
        
        route_key = event.get('requestContext', {}).get('routeKey', '')
        connection_id = event.get('requestContext', {}).get('connectionId', '')
        domain_name = event.get('requestContext', {}).get('domainName', '')
        stage = event.get('requestContext', {}).get('stage', '')
        
        # Initialize API Gateway Management API client
        global apigateway_management
        apigateway_management = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f'https://{domain_name}/{stage}'
        )
        
        logger.info(f"Processing WebSocket event: {route_key} for connection {connection_id}")
        
        if route_key == '$connect':
            return handle_connect(connection_id, event)
        elif route_key == '$disconnect':
            return handle_disconnect(connection_id, event)
        elif route_key == 'sendMessage':
            return handle_send_message(connection_id, event)
        else:
            logger.warning(f"Unknown route key: {route_key}")
            return create_response(400, {'error': 'Unknown route'})
            
    except Exception as e:
        logger.exception(f"Error processing WebSocket event: {str(e)}")
        metrics.add_metric(name="ChatErrors", unit=MetricUnit.Count, value=1)
        return create_response(500, {'error': 'Internal server error'})


def handle_connect(connection_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket connection establishment"""
    try:
        # Extract user information from the connection (if authenticated)
        user_id = extract_user_id(event)
        
        logger.info(f"WebSocket connection established: {connection_id} for user: {user_id}")
        
        # Send welcome message
        welcome_message = {
            'type': 'welcome',
            'message': 'Welcome to E-Com67 AI Assistant! How can I help you today?',
            'timestamp': int(time.time() * 1000)
        }
        
        send_message_to_connection(connection_id, welcome_message)
        
        metrics.add_metric(name="ChatConnections", unit=MetricUnit.Count, value=1)
        
        return create_response(200, {'message': 'Connected successfully'})
        
    except Exception as e:
        logger.exception(f"Error handling connection: {str(e)}")
        return create_response(500, {'error': 'Connection failed'})


def handle_disconnect(connection_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket disconnection"""
    try:
        user_id = extract_user_id(event)
        
        logger.info(f"WebSocket disconnection: {connection_id} for user: {user_id}")
        
        # Optional: Clean up old chat sessions for this user
        # This helps manage storage costs by removing very old conversations
        cleanup_old_sessions(user_id, days_to_keep=30)
        
        metrics.add_metric(name="ChatDisconnections", unit=MetricUnit.Count, value=1)
        
        return create_response(200, {'message': 'Disconnected successfully'})
        
    except Exception as e:
        logger.exception(f"Error handling disconnection: {str(e)}")
        return create_response(500, {'error': 'Disconnection failed'})


def handle_send_message(connection_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming chat messages and generate AI responses"""
    try:
        user_id = extract_user_id(event)
        
        # Parse message body
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '').strip()
        session_id = body.get('sessionId', str(uuid.uuid4()))
        
        if not user_message:
            return create_response(400, {'error': 'Message cannot be empty'})
        
        logger.info(f"Processing message from user {user_id}: {user_message[:100]}...")
        
        # Save user message to chat history
        save_chat_message(user_id, user_message, 'user', session_id)
        
        # Get conversation context
        conversation_history = get_conversation_history(user_id, session_id, limit=10)
        
        # Get relevant product context for RAG
        product_context = get_relevant_products(user_message)
        
        # Generate AI response using Bedrock
        ai_response = generate_ai_response(user_message, conversation_history, product_context)
        
        # Save AI response to chat history
        save_chat_message(user_id, ai_response, 'assistant', session_id)
        
        # Send response back to user
        response_message = {
            'type': 'message',
            'message': ai_response,
            'timestamp': int(time.time() * 1000),
            'sessionId': session_id
        }
        
        send_message_to_connection(connection_id, response_message)
        
        metrics.add_metric(name="MessagesProcessed", unit=MetricUnit.Count, value=1)
        
        return create_response(200, {'message': 'Message processed successfully'})
        
    except Exception as e:
        logger.exception(f"Error processing message: {str(e)}")
        
        # Send error message to user
        error_message = {
            'type': 'error',
            'message': 'Sorry, I encountered an error processing your message. Please try again.',
            'timestamp': int(time.time() * 1000)
        }
        
        try:
            send_message_to_connection(connection_id, error_message)
        except:
            pass  # Don't fail if we can't send error message
        
        return create_response(500, {'error': 'Message processing failed'})


def extract_user_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from WebSocket event (if authenticated)"""
    try:
        # For now, return a placeholder user ID
        # In production, this would extract from JWT token or connection context
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        return authorizer.get('principalId', 'anonymous')
    except:
        return 'anonymous'


def save_chat_message(user_id: str, content: str, role: str, session_id: str) -> None:
    """Save chat message to DynamoDB"""
    try:
        timestamp = int(time.time() * 1000)
        message_id = str(uuid.uuid4())
        
        chat_history_table.put_item(
            Item={
                'userId': user_id,
                'timestamp': timestamp,
                'messageId': message_id,
                'role': role,
                'content': content,
                'sessionId': session_id,
                'metadata': {
                    'createdAt': datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.debug(f"Saved chat message: {message_id} for user {user_id}")
        
    except Exception as e:
        logger.exception(f"Error saving chat message: {str(e)}")
        # Don't fail the request if we can't save to history
        pass


def cleanup_old_sessions(user_id: str, days_to_keep: int = 30) -> None:
    """Clean up old chat sessions to manage storage costs"""
    try:
        # Calculate cutoff timestamp (30 days ago)
        import time
        cutoff_timestamp = int((time.time() - (days_to_keep * 24 * 60 * 60)) * 1000)
        
        # Query old messages for this user
        response = chat_history_table.query(
            KeyConditionExpression='userId = :user_id AND #ts < :cutoff',
            ExpressionAttributeNames={
                '#ts': 'timestamp'
            },
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':cutoff': cutoff_timestamp
            },
            ProjectionExpression='userId, #ts',  # Only get keys for deletion
            Limit=100  # Limit to avoid timeout
        )
        
        # Delete old messages in batches
        old_messages = response.get('Items', [])
        if old_messages:
            with chat_history_table.batch_writer() as batch:
                for message in old_messages:
                    batch.delete_item(
                        Key={
                            'userId': message['userId'],
                            'timestamp': message['timestamp']
                        }
                    )
            
            logger.info(f"Cleaned up {len(old_messages)} old chat messages for user {user_id}")
        
    except Exception as e:
        logger.exception(f"Error cleaning up old sessions for user {user_id}: {str(e)}")
        # Don't fail the disconnect if cleanup fails
        pass


def get_conversation_history(user_id: str, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent conversation history for context"""
    try:
        response = chat_history_table.query(
            KeyConditionExpression='userId = :user_id',
            FilterExpression='sessionId = :session_id',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':session_id': session_id
            },
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        # Reverse to get chronological order
        messages = list(reversed(response.get('Items', [])))
        
        logger.debug(f"Retrieved {len(messages)} messages from conversation history")
        
        return messages
        
    except Exception as e:
        logger.exception(f"Error retrieving conversation history: {str(e)}")
        return []


def get_relevant_products(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get relevant products for RAG context.
    
    This is a simple implementation that scans products.
    In production, this would use OpenSearch for better relevance.
    """
    try:
        # Simple keyword matching for now
        # In production, this would use OpenSearch with semantic search
        query_lower = query.lower()
        keywords = query_lower.split()
        
        # Scan products table (not efficient, but simple for learning)
        response = products_table.scan(
            FilterExpression='contains(#name, :query) OR contains(description, :query) OR contains(category, :query)',
            ExpressionAttributeNames={
                '#name': 'name'  # 'name' is a reserved word in DynamoDB
            },
            ExpressionAttributeValues={
                ':query': query_lower
            },
            Limit=limit
        )
        
        products = response.get('Items', [])
        
        logger.debug(f"Found {len(products)} relevant products for query: {query}")
        
        return products
        
    except Exception as e:
        logger.exception(f"Error retrieving relevant products: {str(e)}")
        return []


def get_relevant_context_from_knowledge_base(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get relevant context from S3-based knowledge base using vector similarity.
    
    This uses semantic search with embeddings for better relevance.
    """
    try:
        # Generate embedding for the query
        query_embedding = generate_embedding_for_search(query)
        if not query_embedding:
            logger.warning("Could not generate embedding for query, falling back to product search")
            return []
        
        # Import OpenSearch client
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from aws_requests_auth.aws_auth import AWSRequestsAuth
        import boto3
        
        # Set up AWS authentication for OpenSearch
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT', '')
        if not opensearch_endpoint:
            logger.warning("OpenSearch endpoint not configured")
            return []
        
        host = opensearch_endpoint.replace('https://', '')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        service = 'aoss'  # OpenSearch Serverless
        credentials = boto3.Session().get_credentials()
        awsauth = AWSRequestsAuth(credentials, region, service)
        
        opensearch_client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=10
        )
        
        # Search OpenSearch for similar embeddings
        search_body = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": limit
                    }
                }
            },
            "_source": ["text", "source", "metadata"],
            "size": limit
        }
        
        # Execute search
        response = opensearch_client.search(
            index="knowledge-base",
            body=search_body
        )
        
        # Extract relevant context
        context_chunks = []
        for hit in response['hits']['hits']:
            context_chunks.append({
                'text': hit['_source']['text'],
                'source': hit['_source'].get('source', 'unknown'),
                'score': hit['_score'],
                'metadata': hit['_source'].get('metadata', {})
            })
        
        logger.debug(f"Found {len(context_chunks)} relevant context chunks for query: {query}")
        
        return context_chunks
        
    except ImportError:
        logger.warning("OpenSearch client not available, falling back to product search")
        return []
    except Exception as e:
        logger.exception(f"Error retrieving context from knowledge base: {str(e)}")
        return []


def generate_embedding_for_search(text: str) -> Optional[List[float]]:
    """Generate embedding for search queries using Amazon Bedrock"""
    try:
        # Prepare the request for Bedrock
        request_body = {
            "inputText": text
        }
        
        # Call Bedrock
        embedding_model_id = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
        response = bedrock_runtime.invoke_model(
            modelId=embedding_model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding', [])
        
        logger.debug(f"Generated search embedding with dimension {len(embedding)}")
        
        return embedding
        
    except Exception as e:
        logger.exception(f"Error generating search embedding: {str(e)}")
        return None


def generate_ai_response(user_message: str, conversation_history: List[Dict[str, Any]], 
                        product_context: List[Dict[str, Any]]) -> str:
    """Generate AI response using Amazon Bedrock with knowledge base context"""
    try:
        # Build context for the AI
        context_parts = []
        
        # Add knowledge base context (semantic search)
        knowledge_context = get_relevant_context_from_knowledge_base(user_message)
        if knowledge_context:
            context_parts.append("Relevant information from our knowledge base:")
            for ctx in knowledge_context:
                context_parts.append(f"- {ctx['text']}")
        
        # Add product context if available
        if product_context:
            context_parts.append("\nRelevant products from our catalog:")
            for product in product_context:
                context_parts.append(f"- {product.get('name', 'Unknown')}: {product.get('description', 'No description')} (${product.get('price', 'N/A')})")
        
        # Add conversation history
        if conversation_history:
            context_parts.append("\nRecent conversation:")
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                context_parts.append(f"{role.title()}: {content}")
        
        context = "\n".join(context_parts)
        
        # Create the prompt
        prompt = f"""You are a helpful AI assistant for E-Com67, an e-commerce platform. You help customers with product recommendations, questions about orders, and general support.

{context}

Customer: {user_message}

Please provide a helpful, friendly response. If the customer is asking about products, use the product information provided above. If you have knowledge base information, use that to provide accurate answers. Keep responses concise but informative. If you don't have specific information, be honest about it and suggest how the customer can get help.
Assistant: """
        
        # Prepare the request for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Call Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        ai_response = response_body.get('content', [{}])[0].get('text', 'Sorry, I could not generate a response.')
        
        logger.debug(f"Generated AI response: {ai_response[:100]}...")
        metrics.add_metric(name="BedrockInvocations", unit=MetricUnit.Count, value=1)
        
        return ai_response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.exception(f"Bedrock error ({error_code}): {str(e)}")
        
        if error_code == 'AccessDeniedException':
            return "I'm currently unable to access the AI service. Please contact support for assistance."
        elif error_code == 'ThrottlingException':
            return "I'm experiencing high demand right now. Please try again in a moment."
        else:
            return "I encountered an error while processing your request. Please try again or contact support."
            
    except Exception as e:
        logger.exception(f"Error generating AI response: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request. Please try again."


def send_message_to_connection(connection_id: str, message: Dict[str, Any]) -> None:
    """Send message to WebSocket connection"""
    try:
        apigateway_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        
        logger.debug(f"Sent message to connection {connection_id}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'GoneException':
            logger.warning(f"Connection {connection_id} is no longer available")
        else:
            logger.exception(f"Error sending message to connection {connection_id}: {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error sending message: {str(e)}")
        raise


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized Lambda response"""
    return {
        'statusCode': status_code,
        'body': json.dumps(body)
    }