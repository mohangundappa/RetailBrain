"""
Chat service for Staples Brain.
Manages conversations and integration with the brain service.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.conversation_repository import ConversationRepository
from backend.services.brain_service import BrainService
from backend.services.telemetry_service import TelemetryService
from backend.database.models import Conversation, Message

# Set up logging
logger = logging.getLogger("staples_brain")

class ChatService:
    """
    Service for managing chat conversations.
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        brain_service: BrainService,
        telemetry_service: Optional[TelemetryService] = None
    ):
        """
        Initialize with dependencies.
        
        Args:
            db: Database session
            brain_service: Brain service instance
            telemetry_service: Optional telemetry service instance
        """
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.brain_service = brain_service
        self.telemetry_service = telemetry_service
        
        logger.info("Chat service initialized")
    
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
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get or create conversation
        conversation = await self.conversation_repo.get_conversation_by_session_id(session_id)
        if not conversation:
            conversation = await self.conversation_repo.create_conversation(session_id)
        
        # Store user message
        user_message = await self.conversation_repo.add_message(
            conversation_id=str(conversation.id),
            role="user",
            content=message
        )
        
        # Process with brain
        try:
            brain_response = await self.brain_service.process_request(
                message=message,
                session_id=session_id,
                context=context
            )
            
            # Store assistant response
            assistant_message = await self.conversation_repo.add_message(
                conversation_id=str(conversation.id),
                role="assistant",
                content=brain_response["response"],
                metadata=brain_response["metadata"]
            )
            
            # Record telemetry if service is available
            if self.telemetry_service:
                await self.telemetry_service.record_conversation(
                    session_id=session_id,
                    user_input=message,
                    response=brain_response["response"],
                    selected_agent=brain_response["metadata"]["agent"],
                    confidence=brain_response["metadata"]["confidence"],
                    processing_time=brain_response["metadata"]["processing_time"]
                )
            
            await self.db.commit()
            
            return {
                "success": True,
                "response": brain_response["response"],
                "metadata": brain_response["metadata"],
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await self.db.rollback()
            
            # Store system error message
            await self.conversation_repo.add_message(
                conversation_id=str(conversation.id),
                role="system",
                content=f"Error: {str(e)}",
                metadata={"error": True}
            )
            
            await self.db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def get_conversation_history(
        self, 
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            
        Returns:
            Dictionary containing messages and metadata
        """
        conversation = await self.conversation_repo.get_conversation_by_session_id(
            session_id=session_id
        )
        
        if not conversation:
            return {
                "success": False,
                "error": "Conversation not found",
                "session_id": session_id,
                "messages": []
            }
        
        messages = await self.conversation_repo.get_conversation_messages(
            conversation_id=str(conversation.id),
            limit=limit
        )
        
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
        
        return {
            "success": True,
            "session_id": session_id,
            "messages": formatted_messages,
            "conversation_id": str(conversation.id),
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
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
        
        # Enhance with conversation stats if telemetry service is available
        if self.telemetry_service:
            telemetry_stats = await self.telemetry_service.get_stats(days)
            stats.update(telemetry_stats)
        
        return {
            "success": True,
            **stats
        }