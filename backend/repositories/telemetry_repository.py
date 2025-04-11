"""
Repository for telemetry data access.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, update
from sqlalchemy.orm import selectinload

from backend.database.models import TelemetrySession, TelemetryEvent


class TelemetryRepository:
    """Repository for telemetry data access."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize with DB session.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_session(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelemetrySession:
        """
        Create a new telemetry session.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Optional metadata dictionary
            
        Returns:
            Created session instance
        """
        session = TelemetrySession(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        self.db.add(session)
        await self.db.flush()
        return session
    
    async def close_session(
        self, 
        session_id: str
    ) -> bool:
        """
        Close a telemetry session by setting end_time.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Whether the session was found and closed
        """
        query = (
            update(TelemetrySession)
            .where(TelemetrySession.session_id == session_id)
            .where(TelemetrySession.end_time.is_(None))
            .values(end_time=datetime.utcnow())
        )
        
        result = await self.db.execute(query)
        return result.rowcount > 0
    
    async def get_session_by_id(
        self, 
        session_id: str,
        include_events: bool = False
    ) -> Optional[TelemetrySession]:
        """
        Get a telemetry session by ID.
        
        Args:
            session_id: Session identifier
            include_events: Whether to include event relationship
            
        Returns:
            Session if found, None otherwise
        """
        query = select(TelemetrySession).where(TelemetrySession.session_id == session_id)
        
        if include_events:
            query = query.options(
                selectinload(TelemetrySession.events)
            )
        
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def add_event(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> TelemetryEvent:
        """
        Add an event to a session.
        
        Args:
            session_id: Session UUID
            event_type: Event type identifier
            data: Event data dictionary
            
        Returns:
            Created event instance
        """
        event = TelemetryEvent(
            session_id=session_id,
            event_type=event_type,
            data=data
        )
        self.db.add(event)
        await self.db.flush()
        return event
    
    async def get_session_events(
        self, 
        session_id: str,
        limit: int = 100
    ) -> List[TelemetryEvent]:
        """
        Get events for a session.
        
        Args:
            session_id: Session UUID
            limit: Maximum number of events to return
            
        Returns:
            List of event instances
        """
        query = (
            select(TelemetryEvent)
            .where(TelemetryEvent.session_id == session_id)
            .order_by(TelemetryEvent.timestamp)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_sessions(
        self,
        days: int = 7,
        limit: int = 20,
        offset: int = 0
    ) -> List[TelemetrySession]:
        """
        Get recent telemetry sessions.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of sessions
            offset: Offset for pagination
            
        Returns:
            List of session instances
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(TelemetrySession)
            .where(TelemetrySession.start_time >= start_date)
            .order_by(desc(TelemetrySession.start_time))
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_agent_distribution(
        self,
        days: int = 7
    ) -> Dict[str, int]:
        """
        Get distribution of agent usage.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary mapping agent names to usage counts
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # This would ideally use a more efficient SQL query
        # For now, we'll fetch the relevant events and process in Python
        query = (
            select(TelemetryEvent)
            .join(TelemetrySession)
            .where(and_(
                TelemetryEvent.event_type == 'conversation',
                TelemetrySession.start_time >= start_date
            ))
        )
        
        result = await self.db.execute(query)
        events = result.scalars().all()
        
        # Extract agent information from event data
        agent_counts = {}
        for event in events:
            if 'selected_agent' in event.data:
                agent_name = event.data['selected_agent']
                agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
        
        return agent_counts