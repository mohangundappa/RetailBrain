"""
Repository for conversation data access.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import cosine_distance

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
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
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
        conversation_id: str,
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
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.db.add(message)
        await self.db.flush()
        return message
    
    async def get_conversation_messages(
        self, 
        conversation_id: str,
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
        query = (
            select(Message, cosine_distance(Message.embedding, embedding).label("distance"))
            .where(Message.embedding.is_not(None))
            .order_by("distance")
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        messages_with_distances = [(row.Message, row.distance) for row in result.all()]
        
        # Filter by threshold
        return [(msg, dist) for msg, dist in messages_with_distances if dist <= threshold]
    
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
        
        query = (
            select(Conversation)
            .where(Conversation.created_at >= start_date)
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())