"""
Chat service for Staples Brain.
Manages conversations and integration with the brain service.
"""
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Protocol, Union, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.conversation_repository import ConversationRepository
from backend.services.telemetry_service import TelemetryService
from backend.database.models import Conversation, Message
from backend.config.config import Config
from backend.services.graph_brain_service import GraphBrainService

# Define a type alias for brain services
BrainServiceType = GraphBrainService

# Set up logging
logger = logging.getLogger("staples_brain")


class TelemetryServiceProtocol(Protocol):
    """Protocol for telemetry service to support null object pattern."""
    
    async def record_conversation(
        self, 
        session_id: str,
        user_input: str,
        response: str,
        selected_agent: str,
        confidence: float,
        processing_time: float,
        **kwargs
    ) -> None:
        """Record conversation telemetry."""
        ...
        
    async def get_stats(self, days: int, **kwargs) -> Dict[str, Any]:
        """Get telemetry statistics."""
        ...


class NullTelemetryService:
    """Null object implementation of telemetry service."""
    
    async def record_conversation(
        self, 
        session_id: str,
        user_input: str,
        response: str,
        selected_agent: str,
        confidence: float,
        processing_time: float,
        **kwargs
    ) -> None:
        """Do nothing implementation."""
        pass
        
    async def get_stats(self, days: int, **kwargs) -> Dict[str, Any]:
        """Return empty stats."""
        return {}


class ChatService:
    """
    Service for managing chat conversations.
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        brain_service: BrainServiceType,
        telemetry_service: Optional[TelemetryService] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize with dependencies.
        
        Args:
            db: Database session
            brain_service: Brain service instance (LangGraphBrainService or GraphBrainService)
            telemetry_service: Optional telemetry service instance
            config: Application configuration
        """
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.brain_service = brain_service
        self.telemetry_service = telemetry_service or NullTelemetryService()
        self.config = config or Config()
        
        # Configuration settings with defaults
        self.default_limit = getattr(self.config, 'DEFAULT_MESSAGE_LIMIT', 50)
        self.max_limit = getattr(self.config, 'MAX_MESSAGES_PER_REQUEST', 100)
        self.max_message_size = getattr(self.config, 'MAX_MESSAGE_SIZE', 4000)
        self.service_timeout = getattr(self.config, 'SERVICE_TIMEOUT', 30)
        
        logger.info("Chat service initialized with configuration")
    
    async def cleanup(self):
        """
        Clean up resources used by the service.
        This method is called when the service is being disposed.
        """
        logger.debug("Cleaning up chat service resources")
        # Any cleanup operations would go here
    
    async def process_message(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message, storing in conversation history and routing to brain.
        
        Args:
            message: User message
            session_id: Session identifier for maintaining conversation state
            context: Additional context information
            
        Returns:
            Response with content and metadata
        """
        logger.info(f"TRACE: Entered ChatService.process_message in backend/services/chat_service.py")
        
        # Input validation
        if not message or not isinstance(message, str):
            logger.info(f"TRACE: Invalid message format validation in ChatService.process_message")
            return {
                "success": False, 
                "error": "Invalid message format", 
                "session_id": session_id or str(uuid.uuid4())
            }
            
        if len(message) > self.max_message_size:
            logger.info(f"TRACE: Message size exceeded in ChatService.process_message")
            return {
                "success": False, 
                "error": f"Message exceeds maximum size of {self.max_message_size} characters", 
                "session_id": session_id or str(uuid.uuid4())
            }
        
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generated new session ID: {session_id}")
        
        # Initialize conversation variable outside the try block
        conversation = None
        
        try:
            # Step 1: Get or create conversation with explicit transaction control
            conversation = None
            user_message = None
            assistant_message = None
            
            # Start a transaction for conversation operations
            async with self.db.begin():
                # Get conversation
                conversation = await self.conversation_repo.get_conversation_by_session_id(session_id)
                
                # Create conversation if it doesn't exist
                if not conversation:
                    logger.debug(f"Creating new conversation for session: {session_id}")
                    conversation = await self.conversation_repo.create_conversation(session_id)
                
                # Store user message
                user_message = await self.conversation_repo.add_message(
                    conversation_id=conversation.id,
                    role="user",
                    content=message
                )
            
            # Step 2: Process with brain outside of transaction
            brain_response = await self.brain_service.process_request(
                message=message,
                session_id=session_id,
                context=context
            )
            
            # Safely extract metadata values with defaults
            metadata = brain_response.get("metadata", {})
            
            # Step 3: Store the assistant response in a separate transaction
            async with self.db.begin():
                assistant_message = await self.conversation_repo.add_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=brain_response["response"],
                    metadata=metadata  # Using the safely extracted metadata
                )
            
            # Step 4: Record telemetry if needed
            
            await self.telemetry_service.record_conversation(
                session_id=session_id,
                user_input=message,
                response=brain_response["response"],
                selected_agent=metadata.get("agent", "unknown"),
                confidence=metadata.get("confidence", 0.0),
                processing_time=metadata.get("processing_time", 0.0)
            )
            
            # Construct response with safe metadata access
            return {
                "success": True,
                "message_id": str(assistant_message.id),
                "content": brain_response["response"],
                "session_id": session_id,
                "agent_type": metadata.get("agent", "default"),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            
            # Make sure we have a valid conversation before attempting to store error
            if conversation:
                # Store system error message in a separate transaction
                try:
                    async with self.db.begin():
                        await self.conversation_repo.add_message(
                            conversation_id=conversation.id,
                            role="system",
                            content=f"Error: {str(e)}",
                            metadata={"error": True}
                        )
                except Exception as inner_error:
                    logger.error(f"Error storing error message: {str(inner_error)}", exc_info=True)
            
            # For error responses, we still need to include required fields from the schema
            return {
                "success": False,
                "message_id": "error-" + str(uuid.uuid4()),
                "content": f"An error occurred: {str(e)}",
                "session_id": session_id,
                "error": str(e)
            }
    
    async def get_conversation_with_messages(
        self, 
        session_id: str,
        limit: Optional[int] = None
    ) -> Tuple[Optional[Conversation], List[Message]]:
        """
        Get both conversation and its messages in one optimized query.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            
        Returns:
            Tuple of (conversation, messages)
        """
        # Implementation with explicit transaction control
        conversation = None
        messages = []
        
        try:
            # Use a transaction to ensure consistent read
            async with self.db.begin():
                conversation = await self.conversation_repo.get_conversation_by_session_id(session_id)
                if not conversation:
                    return None, []
                    
                messages = await self.conversation_repo.get_conversation_messages(
                    conversation_id=conversation.id,
                    limit=limit or self.default_limit
                )
            
            # Ensure we're returning safe-to-serialize objects
            # Sometimes SQLAlchemy objects can have unserializable metadata
            # For safety, we'll do a simple check
            if conversation is not None:
                # Ensure relationship data is loaded
                if hasattr(conversation, '_sa_instance_state'):
                    # Force detach from session if needed
                    self.db.expunge(conversation)
            
            return conversation, messages
        
        except Exception as e:
            logger.error(f"Error getting conversation and messages: {str(e)}", exc_info=True)
            return None, []
    
    async def get_conversation_history(
        self, 
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip for pagination
            
        Returns:
            Dictionary containing messages and metadata
        """
        try:
            # Apply limit constraints
            if limit is None:
                limit = self.default_limit
            elif limit > self.max_limit:
                limit = self.max_limit
            
            # Use the optimized method to get conversation and messages
            conversation, messages = await self.get_conversation_with_messages(
                session_id=session_id,
                limit=limit
            )
            
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found",
                    "session_id": session_id,
                    "messages": []
                }
            
            # Format messages with safe timestamp handling
            formatted_messages = []
            for msg in messages:
                # Handle possibly None timestamp
                timestamp = None
                if msg.created_at:
                    timestamp = msg.created_at.isoformat()
                
                # Convert metadata to a safe dictionary
                safe_metadata = {}
                if msg.metadata:
                    try:
                        # Handle potentially non-dict metadata
                        if hasattr(msg.metadata, 'items') and callable(msg.metadata.items):
                            # If metadata is a dict-like object, try to convert keys/values
                            for k, v in msg.metadata.items():
                                if isinstance(v, (str, int, float, bool, type(None))):
                                    safe_metadata[str(k)] = v
                        elif hasattr(msg.metadata, '__dict__'):
                            # If metadata is an object with __dict__, use its attributes
                            for k, v in msg.metadata.__dict__.items():
                                if not k.startswith('_') and isinstance(v, (str, int, float, bool, type(None))):
                                    safe_metadata[k] = v
                        else:
                            # Last resort, try string representation
                            safe_metadata = {"value": str(msg.metadata)}
                    except Exception as e:
                        # If all else fails, include minimal information
                        logger.warning(f"Failed to convert metadata to dict: {str(e)}")
                        safe_metadata = {"metadata_type": type(msg.metadata).__name__}
                
                formatted_messages.append({
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": timestamp,
                    "metadata": safe_metadata  # Use safely processed metadata
                })
            
            # Get total message count in a transaction
            total_messages = 0
            async with self.db.begin():
                total_messages = await self.conversation_repo.count_conversation_messages(
                    conversation_id=conversation.id
                )
            
            # Safely handle dates that might be None
            created_at = None
            updated_at = None
            
            if conversation.created_at:
                created_at = conversation.created_at.isoformat()
            
            if conversation.updated_at:
                updated_at = conversation.updated_at.isoformat()
                
            return {
                "success": True,
                "session_id": session_id,
                "messages": formatted_messages,
                "conversation_id": str(conversation.id),
                "created_at": created_at,
                "updated_at": updated_at,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_messages,
                    "has_more": total_messages > (offset + len(formatted_messages))
                }
            }
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Error getting conversation history: {str(e)}",
                "session_id": session_id,
                "messages": []
            }
    
    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List active sessions/conversations.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            
        Returns:
            Dictionary with session information
        """
        try:
            # Fetch recent conversations with explicit transaction control
            conversations = []
            async with self.db.begin():
                # Get conversations from repository
                conversations = await self.conversation_repo.get_recent_conversations(
                    days=30,  # Last 30 days
                    limit=limit,
                    offset=offset
                )
            
            # Format sessions for the response with safe timestamp handling
            sessions = []
            for conv in conversations:
                # Safely handle dates that might be None
                created_at = None
                updated_at = None
                
                if conv.created_at:
                    created_at = conv.created_at.isoformat()
                
                if conv.updated_at:
                    updated_at = conv.updated_at.isoformat()
                
                # Convert metadata to a safe dictionary
                safe_metadata = {}
                if conv.meta_data:
                    try:
                        # Handle potentially non-dict metadata
                        if hasattr(conv.meta_data, 'items') and callable(conv.meta_data.items):
                            # If metadata is a dict-like object, try to convert keys/values
                            for k, v in conv.meta_data.items():
                                if isinstance(v, (str, int, float, bool, type(None))):
                                    safe_metadata[str(k)] = v
                        elif hasattr(conv.meta_data, '__dict__'):
                            # If metadata is an object with __dict__, use its attributes
                            for k, v in conv.meta_data.__dict__.items():
                                if not k.startswith('_') and isinstance(v, (str, int, float, bool, type(None))):
                                    safe_metadata[k] = v
                        else:
                            # Last resort, try string representation
                            safe_metadata = {"value": str(conv.meta_data)}
                    except Exception as e:
                        # If all else fails, include minimal information
                        logger.warning(f"Failed to convert metadata to dict: {str(e)}")
                        safe_metadata = {"metadata_type": type(conv.meta_data).__name__}
                
                sessions.append({
                    "id": str(conv.id),
                    "session_id": conv.session_id,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "user_id": conv.user_id,
                    "metadata": safe_metadata
                })
            
            return {
                "success": True,
                "sessions": sessions,
                "metadata": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(sessions)  # For full count, would need another query
                }
            }
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Error listing sessions: {str(e)}",
                "sessions": []
            }
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get all messages for a specific session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            
        Returns:
            Dictionary with messages
        """
        # This is just a wrapper around get_conversation_history for API consistency
        return await self.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        Get a list of available agents.
        
        Returns:
            Dictionary containing agent information
        """
        result = await self.brain_service.list_agents()
        return {
            "success": True,
            **result
        }
    
    async def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing system statistics
        """
        stats = await self.brain_service.get_system_stats(days)
        
        # Enhance with conversation stats (using null object pattern)
        telemetry_stats = await self.telemetry_service.get_stats(days)
        stats.update(telemetry_stats)
        
        return {
            "success": True,
            **stats
        }