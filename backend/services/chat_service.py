"""
Chat service for Staples Brain.
Manages conversations and integration with the brain service.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.conversation_repository import ConversationRepository
from backend.services.langgraph_brain_service import LangGraphBrainService
from backend.services.telemetry_service import TelemetryService
from backend.database.models import Conversation, Message
from backend.config.config import Config

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
        brain_service: LangGraphBrainService,
        telemetry_service: Optional[TelemetryService] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize with dependencies.
        
        Args:
            db: Database session
            brain_service: LangGraphBrainService instance
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
        # Input validation
        if not message or not isinstance(message, str):
            return {
                "success": False, 
                "error": "Invalid message format", 
                "session_id": session_id or str(uuid.uuid4())
            }
            
        if len(message) > self.max_message_size:
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
        
        # Use transaction context manager
        async with self.db.begin() as transaction:
            try:
                # Get or create conversation
                conversation = await self.conversation_repo.get_conversation_by_session_id(session_id)
                if not conversation:
                    logger.debug(f"Creating new conversation for session: {session_id}")
                    conversation = await self.conversation_repo.create_conversation(session_id)
                
                # Store user message
                user_message = await self.conversation_repo.add_message(
                    conversation_id=conversation.id,
                    role="user",
                    content=message
                )
                
                # Process with brain
                brain_response = await self.brain_service.process_request(
                    message=message,
                    session_id=session_id,
                    context=context
                )
                
                # Store assistant response
                assistant_message = await self.conversation_repo.add_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=brain_response["response"],
                    metadata=brain_response["metadata"]
                )
                
                # Record telemetry (using null object pattern, no need for null check)
                await self.telemetry_service.record_conversation(
                    session_id=session_id,
                    user_input=message,
                    response=brain_response["response"],
                    selected_agent=brain_response["metadata"]["agent"],
                    confidence=brain_response["metadata"]["confidence"],
                    processing_time=brain_response["metadata"]["processing_time"]
                )
                
                # Transaction will be committed automatically
                
                return {
                    "success": True,
                    "response": brain_response["response"],
                    "metadata": brain_response["metadata"],
                    "session_id": session_id
                }
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                # Transaction will be rolled back automatically
                
                # Make sure we have a valid conversation before attempting to store error
                if conversation:
                    # Store system error message in a new transaction
                    async with self.db.begin():
                        await self.conversation_repo.add_message(
                            conversation_id=conversation.id,
                            role="system",
                            content=f"Error: {str(e)}",
                            metadata={"error": True}
                        )
                
                return {
                    "success": False,
                    "error": str(e),
                    "session_id": session_id
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
        # Implementation would be added to repository layer
        # For now, simulate with two separate queries
        conversation = await self.conversation_repo.get_conversation_by_session_id(session_id)
        if not conversation:
            return None, []
            
        messages = await self.conversation_repo.get_conversation_messages(
            conversation_id=conversation.id,
            limit=limit or self.default_limit
        )
        
        return conversation, messages
    
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
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "metadata": msg.metadata
            })
        
        total_messages = await self.conversation_repo.count_conversation_messages(
            conversation_id=str(conversation.id)
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "messages": formatted_messages,
            "conversation_id": str(conversation.id),
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_messages,
                "has_more": total_messages > (offset + len(formatted_messages))
            }
        }
    
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