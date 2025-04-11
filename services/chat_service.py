"""
Chat Service for Staples Brain.
This service handles chat-related functionality, including message processing and conversation management.
"""

import os
import logging
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from repositories.conversation_repository import ConversationRepository
from brain.staples_brain import StaplesBrain

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chat_service")

class ChatService:
    """
    Service for chat-related functionality.
    
    This class:
    1. Processes messages through the Staples Brain
    2. Manages conversation state and context
    3. Persists conversation history
    4. Provides access to conversation data
    """
    
    def __init__(self, db_session: AsyncSession, brain: Optional[StaplesBrain] = None):
        """
        Initialize the chat service
        
        Args:
            db_session: Database session
            brain: Optional StaplesBrain instance (will create new if None)
        """
        logger.info("Initializing Chat Service")
        self.db = db_session
        self.conversation_repo = ConversationRepository(db_session)
        
        # Initialize or use provided brain
        if brain:
            self.brain = brain
        else:
            self._initialize_brain()
            
        logger.info("Chat Service initialized")
    
    def _initialize_brain(self):
        """Initialize the Staples Brain instance"""
        try:
            # Import the brain module here to avoid circular imports
            from brain.staples_brain import StaplesBrain
            
            # Get OpenAI API key from environment
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            
            # Initialize the brain
            self.brain = StaplesBrain(openai_api_key=openai_api_key)
            logger.info("Staples Brain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Staples Brain: {e}")
            raise
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the Staples Brain
        
        Args:
            message: The user's message
            session_id: The session identifier (generated if None)
            context: Additional context for the request
            
        Returns:
            Processed response with data and metadata
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        logger.info(f"Processing message for session {session_id}")
        
        start_time = time.time()
        
        try:
            # Get context from repository if needed
            if not context:
                context = await self.conversation_repo.get_conversation_context(session_id)
            
            # Process the message through the brain
            response = await self.brain.process_request(
                user_input=message,
                session_id=session_id,
                context=context
            )
            
            # Save the conversation
            conversation = await self.conversation_repo.create_conversation(
                session_id=session_id,
                user_input=message,
                brain_response=response.get("response", ""),
                intent=response.get("intent"),
                confidence=response.get("confidence"),
                selected_agent=response.get("selected_agent")
            )
            
            # Record agent selection if available
            if response.get("selected_agent") and conversation.id:
                await self.conversation_repo.record_agent_selection(
                    conversation_id=conversation.id,
                    user_input=message,
                    selected_agent=response.get("selected_agent"),
                    confidence=response.get("confidence", 0.0),
                    agent_scores=response.get("agent_scores")
                )
            
            # Add processing time
            processing_time = time.time() - start_time
            
            # Format the response for the API
            formatted_response = {
                "data": {
                    "message": response.get("response"),
                    "agent": response.get("selected_agent"),
                    "confidence": response.get("confidence"),
                    "suggested_actions": response.get("suggested_actions", [])
                },
                "metadata": {
                    "processing_time": processing_time,
                    "conversation_id": conversation.id,
                    "session_id": session_id,
                    "intent": response.get("intent"),
                    "intent_confidence": response.get("intent_confidence")
                }
            }
            
            logger.info(f"Message processed successfully for session {session_id} in {processing_time:.2f}s")
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation data
        """
        try:
            conversations = await self.conversation_repo.get_conversations_by_session_id(
                session_id=session_id,
                limit=limit
            )
            
            # Format for API response
            history = []
            for conv in conversations:
                messages = []
                for msg in sorted(conv.messages, key=lambda m: m.created_at):
                    messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None
                    })
                    
                history.append({
                    "id": conv.id,
                    "user_input": conv.user_input,
                    "brain_response": conv.brain_response,
                    "selected_agent": conv.selected_agent,
                    "confidence": conv.confidence,
                    "timestamp": conv.created_at.isoformat() if conv.created_at else None,
                    "messages": messages
                })
                
            return history
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise
    
    async def get_conversation_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get conversation statistics
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Statistics dictionary
        """
        try:
            stats = await self.conversation_repo.get_conversation_stats(
                start_date=start_date,
                end_date=end_date
            )
            return stats
        except Exception as e:
            logger.error(f"Error getting conversation statistics: {e}")
            raise