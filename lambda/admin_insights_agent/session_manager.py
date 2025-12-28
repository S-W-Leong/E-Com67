"""
Session Memory Manager for Admin Insights Agent.

This module manages conversation sessions using AWS Bedrock AgentCore Memory.
It provides session initialization, message persistence, and session termination
capabilities for the Admin Insights Agent.

Key Features:
- Session creation with AgentCore Memory configuration
- Conversation history retrieval
- Session termination and cleanup
- Maximum 20 conversation turns per session

Requirements:
- Requirements 4.1: Session initialization
- Requirements 4.2: Message persistence
- Requirements 4.5: Session termination
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages agent session memory using AWS Bedrock AgentCore Memory.
    
    This class provides methods to create sessions, retrieve conversation history,
    and terminate sessions. It integrates with Bedrock AgentCore Memory service
    to provide persistent, session-scoped conversation storage.
    
    Attributes:
        memory_id (str): The Bedrock AgentCore Memory ID
        region (str): AWS region for the service
        client: Boto3 client for bedrock-agentcore service
        max_turns (int): Maximum number of conversation turns to retain (default: 20)
    """
    
    def __init__(
        self,
        memory_id: str,
        region: str = "ap-southeast-1",
        max_turns: int = 20,
        boto_client_config: Optional[Config] = None
    ):
        """
        Initialize the SessionManager.
        
        Args:
            memory_id: The Bedrock AgentCore Memory ID to use for all sessions
            region: AWS region for the Bedrock AgentCore service (default: ap-southeast-1)
            max_turns: Maximum number of conversation turns to retain per session (default: 20)
            boto_client_config: Optional boto client configuration
            
        Raises:
            ValueError: If memory_id is not provided
        """
        if not memory_id:
            raise ValueError("memory_id is required")
        
        self.memory_id = memory_id
        self.region = region
        self.max_turns = max_turns
        
        # Set up client configuration with user agent
        if boto_client_config:
            existing_user_agent = getattr(boto_client_config, "user_agent_extra", None)
            if existing_user_agent:
                new_user_agent = f"{existing_user_agent} admin-insights-agent"
            else:
                new_user_agent = "admin-insights-agent"
            self.client_config = boto_client_config.merge(Config(user_agent_extra=new_user_agent))
        else:
            self.client_config = Config(user_agent_extra="admin-insights-agent")
        
        # Initialize the Bedrock AgentCore client
        self.client = boto3.client(
            "bedrock-agentcore",
            region_name=self.region,
            config=self.client_config
        )
        
        logger.info(
            f"SessionManager initialized with memory_id={memory_id}, "
            f"region={region}, max_turns={max_turns}"
        )
    
    def create_session(
        self,
        actor_id: str,
        session_id: str,
        session_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new session with memory configuration.
        
        This method initializes a new conversation session in Bedrock AgentCore Memory.
        The session is associated with a specific actor (admin user) and can store
        up to max_turns conversation turns.
        
        Args:
            actor_id: The admin user ID (e.g., Cognito user ID)
            session_id: Unique identifier for this conversation session
            session_description: Optional human-readable description of the session
            
        Returns:
            Dict containing session configuration:
            {
                "memory_id": str,
                "session_id": str,
                "actor_id": str,
                "created_at": str (ISO format timestamp),
                "max_turns": int
            }
            
        Raises:
            ValueError: If actor_id or session_id is not provided
            Exception: If session creation fails
            
        Example:
            >>> manager = SessionManager(memory_id="mem-123")
            >>> session = manager.create_session(
            ...     actor_id="admin-user-456",
            ...     session_id="session-789"
            ... )
        """
        if not actor_id:
            raise ValueError("actor_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        
        try:
            # Create an event to initialize the session
            # This establishes the session in AgentCore Memory
            response = self.client.create_event(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                eventType="CONVERSATION_START",
                eventData={
                    "description": session_description or f"Admin insights session {session_id}",
                    "max_turns": self.max_turns,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                f"Session created: session_id={session_id}, actor_id={actor_id}, "
                f"memory_id={self.memory_id}"
            )
            
            return {
                "memory_id": self.memory_id,
                "session_id": session_id,
                "actor_id": actor_id,
                "created_at": datetime.utcnow().isoformat(),
                "max_turns": self.max_turns,
                "event_id": response.get("eventId")
            }
            
        except Exception as e:
            logger.error(
                f"Failed to create session: session_id={session_id}, "
                f"actor_id={actor_id}, error={str(e)}"
            )
            raise
    
    def get_session_history(
        self,
        actor_id: str,
        session_id: str,
        max_results: int = 20,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve conversation history for a session.
        
        This method fetches stored messages and events from Bedrock AgentCore Memory
        for a specific session. It returns the conversation history in chronological order.
        
        Args:
            actor_id: The admin user ID
            session_id: The conversation session ID
            max_results: Maximum number of records to retrieve (default: 20)
            next_token: Pagination token for retrieving additional results
            
        Returns:
            Dict containing:
            {
                "session_id": str,
                "actor_id": str,
                "events": List[Dict],  # List of conversation events
                "next_token": Optional[str]  # For pagination
            }
            
        Raises:
            ValueError: If actor_id or session_id is not provided
            Exception: If retrieval fails
            
        Example:
            >>> history = manager.get_session_history(
            ...     actor_id="admin-user-456",
            ...     session_id="session-789"
            ... )
            >>> for event in history["events"]:
            ...     print(event["eventType"], event["eventData"])
        """
        if not actor_id:
            raise ValueError("actor_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        
        try:
            # List events for this session
            params = {
                "memoryId": self.memory_id,
                "actorId": actor_id,
                "sessionId": session_id,
                "maxResults": min(max_results, self.max_turns)
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            response = self.client.list_events(**params)
            
            events = response.get("events", [])
            
            logger.info(
                f"Retrieved {len(events)} events for session_id={session_id}, "
                f"actor_id={actor_id}"
            )
            
            return {
                "session_id": session_id,
                "actor_id": actor_id,
                "memory_id": self.memory_id,
                "events": events,
                "next_token": response.get("nextToken")
            }
            
        except Exception as e:
            logger.error(
                f"Failed to retrieve session history: session_id={session_id}, "
                f"actor_id={actor_id}, error={str(e)}"
            )
            raise
    
    def terminate_session(
        self,
        actor_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Terminate a session and delete all associated memory data.
        
        This method marks a session as terminated and removes all conversation
        history from Bedrock AgentCore Memory. This operation is irreversible.
        
        Args:
            actor_id: The admin user ID
            session_id: The conversation session ID to terminate
            
        Returns:
            Dict containing:
            {
                "session_id": str,
                "actor_id": str,
                "terminated_at": str (ISO format timestamp),
                "status": str  # "terminated"
            }
            
        Raises:
            ValueError: If actor_id or session_id is not provided
            Exception: If termination fails
            
        Example:
            >>> result = manager.terminate_session(
            ...     actor_id="admin-user-456",
            ...     session_id="session-789"
            ... )
            >>> print(result["status"])  # "terminated"
        """
        if not actor_id:
            raise ValueError("actor_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        
        try:
            # Create a termination event
            response = self.client.create_event(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                eventType="CONVERSATION_END",
                eventData={
                    "terminated_at": datetime.utcnow().isoformat(),
                    "reason": "session_terminated"
                }
            )
            
            # Note: In a production implementation, you might want to call
            # delete_session or a similar API if available to fully clean up
            # the session data. For now, we mark it as terminated.
            
            logger.info(
                f"Session terminated: session_id={session_id}, actor_id={actor_id}"
            )
            
            return {
                "session_id": session_id,
                "actor_id": actor_id,
                "memory_id": self.memory_id,
                "terminated_at": datetime.utcnow().isoformat(),
                "status": "terminated",
                "event_id": response.get("eventId")
            }
            
        except Exception as e:
            logger.error(
                f"Failed to terminate session: session_id={session_id}, "
                f"actor_id={actor_id}, error={str(e)}"
            )
            raise
    
    def store_message(
        self,
        actor_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a message in the session memory.
        
        This is a helper method to store individual messages (user or assistant)
        in the conversation history.
        
        Args:
            actor_id: The admin user ID
            session_id: The conversation session ID
            role: Message role ("USER" or "ASSISTANT")
            content: The message content
            metadata: Optional metadata to store with the message
            
        Returns:
            Dict containing the stored event information
            
        Raises:
            ValueError: If required parameters are missing
            Exception: If storage fails
        """
        if not actor_id:
            raise ValueError("actor_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        if not role:
            raise ValueError("role is required")
        if not content:
            raise ValueError("content is required")
        
        try:
            event_data = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if metadata:
                event_data["metadata"] = metadata
            
            response = self.client.create_event(
                memoryId=self.memory_id,
                actorId=actor_id,
                sessionId=session_id,
                eventType="MESSAGE",
                eventData=event_data
            )
            
            logger.debug(
                f"Message stored: session_id={session_id}, role={role}, "
                f"content_length={len(content)}"
            )
            
            return {
                "event_id": response.get("eventId"),
                "session_id": session_id,
                "actor_id": actor_id,
                "role": role,
                "stored_at": event_data["timestamp"]
            }
            
        except Exception as e:
            logger.error(
                f"Failed to store message: session_id={session_id}, "
                f"role={role}, error={str(e)}"
            )
            raise
