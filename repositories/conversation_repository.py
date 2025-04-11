"""
Conversation Repository for Staples Brain.
Implements data access for conversations using SQLAlchemy with async support.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector

from database.models import Conversation, Message, AgentSelectionEvent, TelemetryEvent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("conversation_repository")

class ConversationRepository:
    """
    Repository for conversation data access.
    
    This class:
    1. Provides methods for creating, reading, updating, and deleting conversations
    2. Implements vector similarity search for semantic retrieval
    3. Manages related entities like messages and telemetry events
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session"""
        self.db = db_session
    
    async def create_conversation(
        self,
        session_id: str,
        user_input: str,
        brain_response: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        selected_agent: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> Conversation:
        """
        Create a new conversation record
        
        Args:
            session_id: Session identifier
            user_input: User's message
            brain_response: System's response
            intent: Detected intent
            confidence: Confidence score
            selected_agent: Selected agent name
            embedding: Vector embedding of conversation
            
        Returns:
            Created conversation
        """
        conversation = Conversation(
            session_id=session_id,
            user_input=user_input,
            brain_response=brain_response,
            intent=intent,
            confidence=confidence,
            selected_agent=selected_agent,
            embedding=embedding
        )
        
        self.db.add(conversation)
        await self.db.flush()
        
        # Add messages
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=user_input
        )
        
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=brain_response
        )
        
        self.db.add_all([user_message, assistant_message])
        await self.db.commit()
        
        logger.info(f"Created conversation with ID {conversation.id} for session {session_id}")
        return conversation
    
    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add a message to an existing conversation
        
        Args:
            conversation_id: Parent conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Additional metadata
            
        Returns:
            Created message
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata
        )
        
        self.db.add(message)
        await self.db.commit()
        
        logger.info(f"Added {role} message to conversation {conversation_id}")
        return message
    
    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """
        Get a conversation by ID with all related messages
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation with messages or None
        """
        query = select(Conversation).where(
            Conversation.id == conversation_id
        ).options(
            selectinload(Conversation.messages)
        )
        
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_conversations_by_session_id(
        self, 
        session_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Get conversations for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of results
            
        Returns:
            List of conversations
        """
        query = select(Conversation).where(
            Conversation.session_id == session_id
        ).options(
            selectinload(Conversation.messages)
        ).order_by(
            desc(Conversation.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_conversation_context(
        self,
        session_id: str,
        max_history: int = 10
    ) -> Dict[str, Any]:
        """
        Get conversation context from the session's message history
        
        Args:
            session_id: Session identifier
            max_history: Maximum number of message pairs to include
            
        Returns:
            Context dictionary with conversation history
        """
        # Get conversations for this session
        conversations = await self.get_conversations_by_session_id(
            session_id=session_id,
            limit=max_history
        )
        
        # Extract messages as conversation history
        history = []
        for conv in reversed(conversations):
            # Get messages for this conversation
            for msg in sorted(conv.messages, key=lambda m: m.created_at):
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Build context object
        context = {
            "conversation_history": history[-max_history*2:] if history else [],
            "session_id": session_id
        }
        
        return context
    
    async def search_similar_conversations(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Conversation]:
        """
        Search for similar conversations using vector similarity
        
        Args:
            query_embedding: Vector representation to compare
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar conversations
        """
        # Convert to pgvector Vector
        embedding = Vector(query_embedding)
        
        # Calculate cosine similarity and filter by threshold
        # Cosine distance = 1 - cosine similarity, so we want distance < (1 - threshold)
        max_distance = 1.0 - similarity_threshold
        
        query = select(Conversation).where(
            Conversation.embedding.l2_distance(embedding) < max_distance
        ).order_by(
            Conversation.embedding.cosine_distance(embedding)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def record_agent_selection(
        self,
        conversation_id: int,
        user_input: str,
        selected_agent: str,
        confidence: float,
        agent_scores: Optional[Dict[str, float]] = None
    ) -> AgentSelectionEvent:
        """
        Record an agent selection event
        
        Args:
            conversation_id: Related conversation ID
            user_input: User's message that triggered selection
            selected_agent: Selected agent name
            confidence: Confidence score for selection
            agent_scores: Scores for all agents
            
        Returns:
            Created event
        """
        event = AgentSelectionEvent(
            conversation_id=conversation_id,
            user_input=user_input,
            selected_agent=selected_agent,
            confidence=confidence,
            agent_scores=agent_scores
        )
        
        self.db.add(event)
        await self.db.commit()
        
        logger.info(f"Recorded agent selection event for conversation {conversation_id}")
        return event
    
    async def record_telemetry_event(
        self,
        conversation_id: int,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> TelemetryEvent:
        """
        Record a telemetry event
        
        Args:
            conversation_id: Related conversation ID
            event_type: Type of event
            event_data: Event data
            
        Returns:
            Created event
        """
        event = TelemetryEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            event_data=event_data
        )
        
        self.db.add(event)
        await self.db.commit()
        
        logger.info(f"Recorded telemetry event {event_type} for conversation {conversation_id}")
        return event
    
    async def get_conversation_stats(
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
        # Total conversations
        count_query = select(func.count(Conversation.id))
        if start_date:
            count_query = count_query.where(Conversation.created_at >= start_date)
        if end_date:
            count_query = count_query.where(Conversation.created_at <= end_date)
            
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        # Agent distribution
        agent_query = select(
            Conversation.selected_agent,
            func.count(Conversation.id).label("count")
        ).group_by(
            Conversation.selected_agent
        )
        
        if start_date:
            agent_query = agent_query.where(Conversation.created_at >= start_date)
        if end_date:
            agent_query = agent_query.where(Conversation.created_at <= end_date)
            
        agent_result = await self.db.execute(agent_query)
        agent_counts = {row[0]: row[1] for row in agent_result}
        
        return {
            "total_conversations": total_count,
            "agent_distribution": agent_counts
        }