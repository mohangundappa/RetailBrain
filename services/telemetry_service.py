"""
Telemetry Service for Staples Brain.
This service handles telemetry data collection, processing, and retrieval.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from repositories.conversation_repository import ConversationRepository

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telemetry_service")

class TelemetryService:
    """
    Service for telemetry-related functionality.
    
    This class:
    1. Records telemetry events
    2. Provides access to telemetry data
    3. Generates reports and metrics
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the telemetry service
        
        Args:
            db_session: Database session
        """
        logger.info("Initializing Telemetry Service")
        self.db = db_session
        self.conversation_repo = ConversationRepository(db_session)
        logger.info("Telemetry Service initialized")
    
    async def record_event(
        self,
        event_type: str,
        conversation_id: int,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Record a telemetry event
        
        Args:
            event_type: Type of event
            conversation_id: Conversation ID
            event_data: Event data
            
        Returns:
            Success flag
        """
        try:
            await self.conversation_repo.record_telemetry_event(
                conversation_id=conversation_id,
                event_type=event_type,
                event_data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"Error recording telemetry event: {e}")
            return False
    
    async def get_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get telemetry sessions
        
        Args:
            limit: Maximum number of sessions
            offset: Offset for pagination
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of session data
        """
        try:
            # For now, we'll use a simplified implementation
            # that uses conversation data as session data
            
            # Get unique session IDs
            session_ids = await self._get_session_ids(
                limit=limit,
                offset=offset,
                start_date=start_date or (datetime.now() - timedelta(days=7)),
                end_date=end_date or datetime.now()
            )
            
            # Get session data
            sessions = []
            for session_id in session_ids:
                # Get conversations for this session
                conversations = await self.conversation_repo.get_conversations_by_session_id(
                    session_id=session_id,
                    limit=10
                )
                
                if not conversations:
                    continue
                
                # Get first and last timestamps
                timestamps = [conv.created_at for conv in conversations if conv.created_at]
                start_time = min(timestamps) if timestamps else None
                end_time = max(timestamps) if timestamps else None
                
                # Count by agent
                agent_counts = {}
                for conv in conversations:
                    if conv.selected_agent:
                        agent_counts[conv.selected_agent] = agent_counts.get(conv.selected_agent, 0) + 1
                
                sessions.append({
                    "session_id": session_id,
                    "conversation_count": len(conversations),
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "duration": (end_time - start_time).total_seconds() if end_time and start_time else None,
                    "agents": agent_counts
                })
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting telemetry sessions: {e}")
            raise
    
    async def get_session_events(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get events for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of event data
        """
        try:
            # Get conversations for this session
            conversations = await self.conversation_repo.get_conversations_by_session_id(
                session_id=session_id
            )
            
            events = []
            for conv in conversations:
                # Add conversation event
                events.append({
                    "event_type": "conversation",
                    "timestamp": conv.created_at.isoformat() if conv.created_at else None,
                    "data": {
                        "conversation_id": conv.id,
                        "user_input": conv.user_input,
                        "brain_response": conv.brain_response,
                        "selected_agent": conv.selected_agent,
                        "confidence": conv.confidence
                    }
                })
                
                # Add telemetry events
                for event in conv.telemetry_events:
                    events.append({
                        "event_type": event.event_type,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                        "data": event.event_data
                    })
            
            # Sort by timestamp
            events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
            
            return events
        except Exception as e:
            logger.error(f"Error getting session events: {e}")
            raise
    
    async def _get_session_ids(
        self,
        limit: int = 20,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[str]:
        """
        Get unique session IDs
        
        Args:
            limit: Maximum number of sessions
            offset: Offset for pagination
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of session IDs
        """
        # This method will be implemented to actually query the database
        # For now, returning a placeholder implementation
        async with self.db as session:
            from sqlalchemy import select, distinct, func
            from database.models import Conversation
            
            query = select(distinct(Conversation.session_id)).order_by(
                func.max(Conversation.created_at).desc()
            )
            
            if start_date:
                query = query.where(Conversation.created_at >= start_date)
            if end_date:
                query = query.where(Conversation.created_at <= end_date)
                
            query = query.group_by(Conversation.session_id).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return [row[0] for row in result]