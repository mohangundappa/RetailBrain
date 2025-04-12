"""
Repository for conversation data access.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector

from backend.database.models import Conversation, Message


class ConversationRepository:
    """Repository for conversation data access."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize with DB session.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_conversation(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Optional metadata dictionary
            
        Returns:
            Created conversation instance
        """
        # Explicitly set timestamps
        current_time = datetime.utcnow()
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            meta_data=metadata or {},
            created_at=current_time,
            updated_at=current_time
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation
    
    async def get_conversation_by_session_id(
        self, 
        session_id: str,
        include_messages: bool = False
    ) -> Optional[Conversation]:
        """
        Get a conversation by session ID.
        
        Args:
            session_id: Session identifier
            include_messages: Whether to include message relationship
            
        Returns:
            Conversation if found, None otherwise
        """
        query = select(Conversation).where(Conversation.session_id == session_id)
        
        if include_messages:
            query = query.options(
                selectinload(Conversation.messages)
            )
        
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system)
            content: Message content
            embedding: Optional vector embedding
            metadata: Optional metadata dictionary
            
        Returns:
            Created message instance
        """
        # Explicitly set the timestamp
        current_time = datetime.utcnow()
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            embedding=embedding,
            meta_data=metadata or {},
            created_at=current_time
        )
        self.db.add(message)
        await self.db.flush()
        
        # Also update the conversation's updated_at timestamp
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
        )
        result = await self.db.execute(query)
        conversation = result.scalars().first()
        
        if conversation:
            conversation.updated_at = current_time
            
        return message
    
    async def get_conversation_messages(
        self, 
        conversation_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages to return
            
        Returns:
            List of message instances
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def find_similar_messages(
        self,
        embedding: List[float],
        limit: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[Message, float]]:
        """
        Find messages with similar embeddings.
        
        Args:
            embedding: Vector embedding to compare against
            limit: Maximum number of results
            threshold: Maximum distance threshold
            
        Returns:
            List of (message, distance) tuples
        """
        # Use raw SQL for vector distance calculation
        query = (
            select(Message)
            .where(Message.embedding.is_not(None))
            .order_by(Message.embedding.l2_distance(embedding))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        # Calculate distances here since we're not using a direct comparison function
        # For demonstration only, this would need to be replaced with proper pgvector operations
        return [(msg, 0.1) for msg in messages]  # Placeholder distance calculation
    
    async def get_recent_conversations(
        self,
        days: int = 7,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """
        Get recent conversations.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of conversations
            offset: Offset for pagination
            
        Returns:
            List of conversation instances
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Handle the case where created_at might be null
        query = (
            select(Conversation)
            .where(or_(
                Conversation.created_at >= start_date,
                Conversation.created_at.is_(None)  # Include conversations with null timestamps
            ))
            .order_by(desc(Conversation.id))  # Fall back to ID ordering when timestamps are null
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
        
    async def count_conversation_messages(
        self,
        conversation_id: int
    ) -> int:
        """
        Count the total number of messages in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Total number of messages
        """
        query = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one()