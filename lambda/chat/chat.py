"""
E-Com67 Platform Chat Function

AI-powered customer support using Strands SDK with Amazon Bedrock integration.
Handles WebSocket connections and provides intelligent product recommendations,
cart management, and order tracking through custom tools.
"""

# CRITICAL: Apply OpenTelemetry fix BEFORE any other imports
# This must be the very first import to prevent StopIteration errors
import otel_fix  # Pre-creates opentelemetry.context module with working implementation

import os
import sys

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

# Import Strands configuration and models
from strands_config import StrandsAgentManager, StrandsAgentConfig
from models import AgentResponse, ErrorResponse, WebSocketMessage, WebSocketMessageType, ResponseType, ErrorType
from response_formatters import format_websocket_message, format_typing_indicator, format_agent_response, format_error_response

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients (will be initialized lazily)
dynamodb = None
apigateway_management = None  # Will be initialized per request

# Environment variables
CHAT_HISTORY_TABLE_NAME = os.environ.get('CHAT_HISTORY_TABLE_NAME')
PRODUCTS_TABLE_NAME = os.environ.get('PRODUCTS_TABLE_NAME')

# DynamoDB tables (will be initialized lazily)
chat_history_table = None
products_table = None

# Strands agent manager (will be initialized lazily)
agent_manager = None


def _initialize_aws_clients():
    """Initialize AWS clients lazily to avoid issues during testing"""
    global dynamodb, chat_history_table, products_table, agent_manager
    
    if dynamodb is None:
        dynamodb = boto3.resource('dynamodb')
        chat_history_table = dynamodb.Table(CHAT_HISTORY_TABLE_NAME)
        products_table = dynamodb.Table(PRODUCTS_TABLE_NAME)
    
    if agent_manager is None:
        agent_manager = StrandsAgentManager()


class AgentManager:
    """Enhanced agent manager for user-specific agent initialization and lifecycle"""
    
    def __init__(self):
        """Initialize the agent manager"""
        self.config = StrandsAgentConfig.from_environment()
        self._agent_cache = {}  # Cache agents per session
        self._conversation_cache = {}  # Cache conversation summaries
        
    def get_agent_for_user(self, user_context: Dict[str, Any]):
        """
        Get or create a Strands agent instance for a specific user context.
        
        Args:
            user_context: User-specific context including user_id, session_id, etc.
            
        Returns:
            Configured Strands agent instance
        """
        session_id = user_context.get('session_id', 'default')
        
        # Check if we have a cached agent for this session
        if session_id in self._agent_cache:
            return self._agent_cache[session_id]
        
        try:
            # Create new agent instance
            strands_manager = StrandsAgentManager(self.config)
            agent = strands_manager.get_agent(user_context)
            
            # Cache the agent for this session
            self._agent_cache[session_id] = agent
            
            logger.info(f"Created new Strands agent for session {session_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create Strands agent: {str(e)}")
            raise RuntimeError(f"Agent initialization failed: {str(e)}")
    
    def get_conversation_summary(self, user_id: str, session_id: str) -> Optional[str]:
        """
        Get cached conversation summary for a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Conversation summary or None if not cached
        """
        cache_key = f"{user_id}:{session_id}"
        return self._conversation_cache.get(cache_key)
    
    def update_conversation_summary(self, user_id: str, session_id: str, 
                                  conversation_history: List[Dict[str, Any]]) -> str:
        """
        Update conversation summary for a session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            conversation_history: Full conversation history
            
        Returns:
            Updated conversation summary
        """
        cache_key = f"{user_id}:{session_id}"
        
        # Generate summary if conversation is getting long
        if len(conversation_history) > self.config.conversation_memory_limit:
            summary = self._generate_conversation_summary(conversation_history)
            self._conversation_cache[cache_key] = summary
            
            # Store summary in DynamoDB for persistence
            self._store_conversation_summary(user_id, session_id, summary)
            
            return summary
        
        return ""
    
    def _generate_conversation_summary(self, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the conversation to maintain context within token limits.
        
        Args:
            conversation_history: Full conversation history
            
        Returns:
            Conversation summary
        """
        try:
            # Take the first part of the conversation for summarization
            # Keep the most recent messages as-is
            messages_to_summarize = conversation_history[:-5]  # All but last 5 messages
            
            if not messages_to_summarize:
                return ""
            
            # Extract key topics and actions
            user_messages = [msg['content'] for msg in messages_to_summarize if msg.get('role') == 'user']
            assistant_messages = [msg['content'] for msg in messages_to_summarize if msg.get('role') == 'assistant']
            
            # Build summary parts
            summary_parts = []
            
            # Identify key topics (simple keyword extraction)
            key_topics = self._extract_key_topics(user_messages)
            if key_topics:
                summary_parts.append(f"Topics discussed: {', '.join(key_topics)}")
            
            # Identify actions taken (simple pattern matching)
            actions_taken = self._extract_actions_taken(assistant_messages)
            if actions_taken:
                summary_parts.append(f"Actions taken: {', '.join(actions_taken)}")
            
            # Add message count context
            summary_parts.append(f"Previous conversation had {len(messages_to_summarize)} messages")
            
            summary = ". ".join(summary_parts) + "."
            
            logger.debug(f"Generated conversation summary: {summary[:100]}...")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return f"Previous conversation with {len(conversation_history)} messages (summary unavailable)"
    
    def _extract_key_topics(self, user_messages: List[str]) -> List[str]:
        """Extract key topics from user messages using simple keyword matching"""
        topics = set()
        
        # Define topic keywords
        topic_keywords = {
            'products': ['product', 'item', 'buy', 'purchase', 'search', 'find'],
            'cart': ['cart', 'add', 'remove', 'checkout', 'basket'],
            'orders': ['order', 'track', 'shipping', 'delivery', 'status'],
            'account': ['account', 'profile', 'login', 'password', 'settings'],
            'support': ['help', 'problem', 'issue', 'question', 'support']
        }
        
        for message in user_messages:
            message_lower = message.lower()
            for topic, keywords in topic_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    topics.add(topic)
        
        return list(topics)[:3]  # Limit to top 3 topics
    
    def _extract_actions_taken(self, assistant_messages: List[str]) -> List[str]:
        """Extract actions taken from assistant messages using simple pattern matching"""
        actions = set()
        
        # Define action patterns
        action_patterns = {
            'product search': ['found', 'search', 'products', 'results'],
            'cart management': ['added to cart', 'removed from cart', 'updated cart'],
            'order lookup': ['order', 'tracking', 'status', 'shipped'],
            'recommendations': ['recommend', 'suggest', 'similar', 'might like'],
            'information provided': ['here', 'information', 'details', 'about']
        }
        
        for message in assistant_messages:
            message_lower = message.lower()
            for action, patterns in action_patterns.items():
                if any(pattern in message_lower for pattern in patterns):
                    actions.add(action)
        
        return list(actions)[:3]  # Limit to top 3 actions
    
    def _store_conversation_summary(self, user_id: str, session_id: str, summary: str):
        """Store conversation summary in DynamoDB for persistence"""
        try:
            # Store in a separate table or as metadata in chat history
            # For now, we'll store it as a special message type
            timestamp = int(time.time() * 1000)
            
            chat_history_table.put_item(
                Item={
                    'userId': user_id,
                    'timestamp': timestamp,
                    'messageId': f"summary_{session_id}_{timestamp}",
                    'role': 'system',
                    'content': summary,
                    'sessionId': session_id,
                    'messageType': 'conversation_summary',
                    'metadata': {
                        'createdAt': datetime.utcnow().isoformat(),
                        'type': 'summary'
                    }
                }
            )
            
            logger.debug(f"Stored conversation summary for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error storing conversation summary: {str(e)}")
    
    def restore_session_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Restore session context including conversation history and summary.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Dictionary with restored context
        """
        try:
            # Get recent conversation history
            conversation_history = get_conversation_history(user_id, session_id, limit=20)
            
            # Get cached or stored conversation summary
            summary = self.get_conversation_summary(user_id, session_id)
            
            if not summary:
                # Try to load summary from DynamoDB
                summary = self._load_conversation_summary(user_id, session_id)
            
            # Update summary if conversation has grown
            if len(conversation_history) > self.config.conversation_memory_limit:
                summary = self.update_conversation_summary(user_id, session_id, conversation_history)
            
            context = {
                'conversation_history': conversation_history,
                'conversation_summary': summary,
                'session_restored': True,
                'message_count': len(conversation_history)
            }
            
            logger.info(f"Restored session context: {len(conversation_history)} messages, summary: {bool(summary)}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error restoring session context: {str(e)}")
            return {
                'conversation_history': [],
                'conversation_summary': "",
                'session_restored': False,
                'message_count': 0
            }
    
    def _load_conversation_summary(self, user_id: str, session_id: str) -> Optional[str]:
        """Load conversation summary from DynamoDB"""
        try:
            # Query for summary messages
            response = chat_history_table.query(
                KeyConditionExpression='userId = :user_id',
                FilterExpression='sessionId = :session_id AND messageType = :msg_type',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':session_id': session_id,
                    ':msg_type': 'conversation_summary'
                },
                ScanIndexForward=False,  # Most recent first
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return items[0].get('content', '')
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading conversation summary: {str(e)}")
            return None
    
    def cleanup_session(self, session_id: str):
        """Clean up cached agent and conversation data for a session"""
        if session_id in self._agent_cache:
            del self._agent_cache[session_id]
            logger.debug(f"Cleaned up agent cache for session {session_id}")
        
        # Clean up conversation cache for this session
        keys_to_remove = [key for key in self._conversation_cache.keys() if key.endswith(f":{session_id}")]
        for key in keys_to_remove:
            del self._conversation_cache[key]
            logger.debug(f"Cleaned up conversation cache for key {key}")
    
    def get_context_aware_prompt(self, user_id: str, session_id: str, current_message: str) -> str:
        """
        Generate context-aware prompt including conversation history and summary.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            current_message: Current user message
            
        Returns:
            Enhanced prompt with context
        """
        try:
            # Restore session context
            context = self.restore_session_context(user_id, session_id)
            
            conversation_history = context.get('conversation_history', [])
            conversation_summary = context.get('conversation_summary', '')
            
            # Build context-aware prompt
            prompt_parts = []
            
            # Add conversation summary if available
            if conversation_summary:
                prompt_parts.append(f"Previous conversation summary: {conversation_summary}")
            
            # Add recent conversation history
            if conversation_history:
                prompt_parts.append("Recent conversation:")
                
                # Include last few messages for immediate context
                recent_messages = conversation_history[-5:]
                for msg in recent_messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    
                    # Truncate very long messages
                    if len(content) > 150:
                        content = content[:150] + "..."
                    
                    prompt_parts.append(f"{role.title()}: {content}")
            
            # Add current message
            prompt_parts.append(f"Current message: {current_message}")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Error generating context-aware prompt: {str(e)}")
            return current_message


# Global agent manager instance
global_agent_manager = None


class ChatError(Exception):
    """Custom exception for chat-related errors"""
    pass


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main handler for WebSocket chat events.
    
    Handles connection management and message processing for AI chat with Strands agent.
    """
    try:
        # Initialize AWS clients and agent manager
        _initialize_aws_clients()
        
        global global_agent_manager
        if global_agent_manager is None:
            global_agent_manager = AgentManager()
        
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

        # Note: Cannot send messages during $connect - connection isn't fully established yet
        # Welcome message will be sent by the client after connection is open

        metrics.add_metric(name="ChatConnections", unit=MetricUnit.Count, value=1)

        return create_response(200, {'message': 'Connected successfully'})

    except Exception as e:
        logger.exception(f"Error handling connection: {str(e)}")
        return create_response(500, {'error': 'Connection failed'})


def handle_disconnect(connection_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket disconnection with agent cleanup"""
    try:
        user_id = extract_user_id(event)
        
        # Extract session ID if available
        session_id = None
        try:
            body = json.loads(event.get('body', '{}'))
            session_id = body.get('sessionId')
        except:
            pass  # Session ID not available in disconnect event
        
        logger.info(f"WebSocket disconnection: {connection_id} for user: {user_id}")
        
        # Clean up agent session if we have session ID
        if session_id and global_agent_manager:
            global_agent_manager.cleanup_session(session_id)
        
        # Optional: Clean up old chat sessions for this user
        # This helps manage storage costs by removing very old conversations
        cleanup_old_sessions(user_id, days_to_keep=30)
        
        metrics.add_metric(name="ChatDisconnections", unit=MetricUnit.Count, value=1)
        
        return create_response(200, {'message': 'Disconnected successfully'})
        
    except Exception as e:
        logger.exception(f"Error handling disconnection: {str(e)}")
        return create_response(500, {'error': 'Disconnection failed'})


def handle_send_message(connection_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced message handling with Strands agent integration"""
    try:
        user_id = extract_user_id(event)

        # Parse message body
        body = json.loads(event.get('body', '{}'))
        # Support both 'message' and 'content' field names for flexibility
        user_message = (body.get('message') or body.get('content') or '').strip()
        session_id = body.get('sessionId', str(uuid.uuid4()))

        if not user_message:
            logger.warning(f"Empty message received. Body: {body}")
            return create_response(400, {'error': 'Message cannot be empty'})
        
        logger.info(f"Processing message from user {user_id}: {user_message[:100]}...")
        
        # Create user context for agent
        user_context = {
            'user_id': user_id,
            'session_id': session_id,
            'connection_id': connection_id
        }
        
        # Send typing indicator
        send_typing_indicator(connection_id, session_id, True)
        
        # Save user message to chat history
        save_chat_message(user_id, user_message, 'user', session_id)
        
        # Process message with Strands agent
        try:
            # Get agent for this user context
            agent = global_agent_manager.get_agent_for_user(user_context)
            
            # Restore session context with conversation history and summary
            session_context = global_agent_manager.restore_session_context(user_id, session_id)
            conversation_history = session_context.get('conversation_history', [])
            conversation_summary = session_context.get('conversation_summary', '')
            
            # Update conversation summary if needed
            if len(conversation_history) > global_agent_manager.config.conversation_memory_limit:
                conversation_summary = global_agent_manager.update_conversation_summary(
                    user_id, session_id, conversation_history
                )
            
            # Build enhanced conversation context
            conversation_context = build_conversation_context(conversation_history, conversation_summary)
            
            # Process message with agent
            start_time = time.time()
            
            # Call the Strands agent with the user message and context
            if conversation_context:
                # Include context in the agent call
                enhanced_message = f"{conversation_context}\n\nCurrent user message: {user_message}"
                result = agent(enhanced_message)
            else:
                result = agent(user_message)
            
            execution_time = time.time() - start_time

            # Extract agent response and tool results
            agent_response_content = extract_agent_response_content(result)
            tool_results = extract_tool_results(result)

            # Debug logging for response extraction
            logger.info(f"Extracted agent response content: {agent_response_content[:200] if agent_response_content else 'EMPTY'}...")

            # Format structured response
            structured_response = format_agent_response(
                message=agent_response_content,
                response_type=determine_response_type(tool_results),
                session_id=session_id,
                data=extract_response_data(tool_results),
                suggestions=generate_follow_up_suggestions(tool_results, user_message),
                tools_used=[tool.get('tool_name', 'unknown') for tool in tool_results],
                requires_action=check_if_action_required(tool_results),
                action_buttons=generate_action_buttons(tool_results)
            )
            
            # Convert to WebSocket message format
            websocket_response = format_websocket_message(
                message_type='message',
                content=structured_response.message,
                session_id=session_id,
                data=structured_response.model_dump(exclude={'message', 'session_id'})
            )

            # Debug logging for WebSocket response
            logger.info(f"WebSocket response message field: {websocket_response.get('message', 'MISSING')[:200] if websocket_response.get('message') else 'EMPTY'}...")
            logger.info(f"Agent processed message in {execution_time:.2f}s using {len(tool_results)} tools")
            
        except Exception as agent_error:
            logger.exception(f"Agent processing error: {str(agent_error)}")
            
            # Create fallback response
            error_response = format_error_response(
                error_code="AGENT_ERROR",
                error_message="I encountered an error processing your request. Please try again.",
                error_type="internal",
                session_id=session_id,
                suggestions=["Try rephrasing your question", "Contact support if the issue persists"],
                retry_possible=True
            )
            
            websocket_response = format_websocket_message(
                message_type='error',
                content=error_response.error_message,
                session_id=session_id,
                data=error_response.model_dump(exclude={'error_message', 'session_id'})
            )
        
        finally:
            # Stop typing indicator
            send_typing_indicator(connection_id, session_id, False)
        
        # Save AI response to chat history
        save_chat_message(user_id, websocket_response['message'], 'assistant', session_id)
        
        # Send response to user
        send_message_to_connection(connection_id, websocket_response)
        
        metrics.add_metric(name="MessagesProcessed", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="StrandsAgentInvocations", unit=MetricUnit.Count, value=1)
        
        return create_response(200, {'message': 'Message processed successfully'})
        
    except Exception as e:
        logger.exception(f"Error processing message: {str(e)}")
        
        # Send error message to user
        error_message = format_websocket_message(
            message_type='error',
            content='Sorry, I encountered an error processing your message. Please try again.',
            session_id=body.get('sessionId') if 'body' in locals() else None
        )
        
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


def send_typing_indicator(connection_id: str, session_id: str, is_typing: bool) -> None:
    """Send typing indicator to WebSocket connection"""
    try:
        typing_message = format_typing_indicator(session_id, is_typing)
        send_message_to_connection(connection_id, typing_message)
        
        logger.debug(f"Sent typing indicator: {is_typing} for connection {connection_id}")
        
    except Exception as e:
        logger.warning(f"Failed to send typing indicator: {str(e)}")
        # Don't fail if we can't send typing indicator


def build_conversation_context(conversation_history: List[Dict[str, Any]], 
                             conversation_summary: str = "") -> str:
    """
    Build conversation context string for the Strands agent with summary support.
    
    Args:
        conversation_history: List of previous messages
        conversation_summary: Optional conversation summary for long conversations
        
    Returns:
        Formatted conversation context
    """
    context_parts = []
    
    # Add conversation summary if available
    if conversation_summary:
        context_parts.append(f"Previous conversation summary: {conversation_summary}")
    
    # Add recent conversation history
    if conversation_history:
        context_parts.append("Recent conversation:")
        
        # Include last 5 messages for immediate context
        recent_messages = conversation_history[-5:]
        
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            # Skip system messages (like summaries)
            if role == 'system':
                continue
            
            # Truncate very long messages
            if len(content) > 200:
                content = content[:200] + "..."
            
            context_parts.append(f"{role.title()}: {content}")
    
    return "\n".join(context_parts) if context_parts else ""


def extract_agent_response_content(agent_result: Any) -> str:
    """
    Extract the main response content from Strands agent result.

    The Strands SDK AgentResult class has a __str__ method that properly
    extracts and concatenates all text content from the message.

    Args:
        agent_result: Result from Strands agent call (AgentResult instance)

    Returns:
        Main response message content
    """
    try:
        # The AgentResult.__str__() method handles text extraction properly:
        # It iterates through message.content array and extracts 'text' from each item
        response_text = str(agent_result).strip()

        if response_text:
            return response_text

        # Fallback: try to access message content directly if str() returns empty
        if hasattr(agent_result, 'message') and isinstance(agent_result.message, dict):
            content = agent_result.message.get('content', [])
            if content and isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item.get('text', ''))
                if text_parts:
                    return '\n'.join(text_parts).strip()

        return "I processed your request but couldn't generate a proper response."

    except Exception as e:
        logger.error(f"Error extracting agent response content: {str(e)}")
        return "I encountered an error generating a response."


def extract_tool_results(agent_result: Any) -> List[Dict[str, Any]]:
    """
    Extract tool execution results from Strands agent result.
    
    Args:
        agent_result: Result from Strands agent call
        
    Returns:
        List of tool execution results
    """
    try:
        tool_results = []
        
        # Check if agent result has tool calls or tool results
        if hasattr(agent_result, 'tool_calls'):
            for tool_call in agent_result.tool_calls:
                tool_results.append({
                    'tool_name': getattr(tool_call, 'name', 'unknown'),
                    'success': True,  # Assume success if no error
                    'result': getattr(tool_call, 'result', None),
                    'error': getattr(tool_call, 'error', None)
                })
        
        # Alternative: check for tools_used attribute
        elif hasattr(agent_result, 'tools_used'):
            for tool in agent_result.tools_used:
                tool_results.append({
                    'tool_name': tool.get('name', 'unknown'),
                    'success': tool.get('success', True),
                    'result': tool.get('result'),
                    'error': tool.get('error')
                })
        
        return tool_results
        
    except Exception as e:
        logger.error(f"Error extracting tool results: {str(e)}")
        return []


def determine_response_type(tool_results: List[Dict[str, Any]]) -> str:
    """
    Determine the response type based on tools used.
    
    Args:
        tool_results: List of tool execution results
        
    Returns:
        Response type string
    """
    if not tool_results:
        return "info"
    
    # Check what types of tools were used
    tool_names = [result.get('tool_name', '') for result in tool_results]
    
    if any('product_search' in name or 'get_product' in name for name in tool_names):
        return "product_list"
    elif any('cart' in name for name in tool_names):
        return "cart_update"
    elif any('order' in name for name in tool_names):
        return "order_info"
    elif any('recommendation' in name for name in tool_names):
        return "recommendation"
    else:
        return "info"


def extract_response_data(tool_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extract structured data from tool results for the response.
    
    Args:
        tool_results: List of tool execution results
        
    Returns:
        Structured data dictionary or None
    """
    if not tool_results:
        return None
    
    response_data = {}
    
    for result in tool_results:
        tool_name = result.get('tool_name', '')
        tool_result = result.get('result')
        
        if tool_result and result.get('success', True):
            # Add tool-specific data to response
            if 'product' in tool_name:
                response_data['products'] = tool_result
            elif 'cart' in tool_name:
                response_data['cart'] = tool_result
            elif 'order' in tool_name:
                response_data['orders'] = tool_result
    
    return response_data if response_data else None


def generate_follow_up_suggestions(tool_results: List[Dict[str, Any]], original_message: str) -> List[str]:
    """
    Generate follow-up suggestions based on tool results and user message.
    
    Args:
        tool_results: List of tool execution results
        original_message: Original user message (for context)
        
    Returns:
        List of follow-up suggestions
    """
    suggestions = []
    
    # Check what tools were used to generate contextual suggestions
    tool_names = [result.get('tool_name', '') for result in tool_results]
    
    if any('product_search' in name for name in tool_names):
        suggestions.extend([
            "Would you like to see more details about any of these products?",
            "Should I add any of these items to your cart?",
            "Would you like to see similar products?"
        ])
    elif any('cart' in name for name in tool_names):
        suggestions.extend([
            "Ready to checkout?",
            "Would you like to continue shopping?",
            "Need help with shipping options?"
        ])
    elif any('order' in name for name in tool_names):
        suggestions.extend([
            "Would you like to track another order?",
            "Need help with returns or exchanges?",
            "Have questions about your order?"
        ])
    else:
        # General suggestions
        suggestions.extend([
            "What else can I help you with?",
            "Would you like to browse our products?",
            "Need help with your account?"
        ])
    
    return suggestions[:3]  # Limit to 3 suggestions


def check_if_action_required(tool_results: List[Dict[str, Any]]) -> bool:
    """
    Check if user action is required based on tool results.
    
    Args:
        tool_results: List of tool execution results
        
    Returns:
        True if user action is required
    """
    # Check for specific conditions that require user action
    for result in tool_results:
        tool_name = result.get('tool_name', '')
        
        # Cart operations might require checkout action
        if 'add_to_cart' in tool_name and result.get('success', False):
            return True
        
        # Order queries might require tracking action
        if 'order' in tool_name and result.get('success', False):
            return False  # Usually informational
    
    return False


def generate_action_buttons(tool_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate action buttons based on tool results.
    
    Args:
        tool_results: List of tool execution results
        
    Returns:
        List of action button configurations
    """
    buttons = []
    
    tool_names = [result.get('tool_name', '') for result in tool_results]
    
    if any('add_to_cart' in name for name in tool_names):
        buttons.append({
            'text': 'View Cart',
            'action': 'view_cart'
        })
        buttons.append({
            'text': 'Checkout',
            'action': 'checkout'
        })
    elif any('product_search' in name for name in tool_names):
        buttons.append({
            'text': 'Refine Search',
            'action': 'refine_search'
        })
        buttons.append({
            'text': 'Browse Categories',
            'action': 'browse_categories'
        })
    
    return buttons


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


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def send_message_to_connection(connection_id: str, message: Dict[str, Any]) -> None:
    """Send message to WebSocket connection"""
    try:
        apigateway_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message, default=json_serial)
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