"""
Telemetry service for Staples Brain.
Manages telemetry data collection and reporting.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.telemetry_repository import TelemetryRepository

# Set up logging
logger = logging.getLogger("staples_brain")

class TelemetryService:
    """
    Service for managing telemetry data.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize with dependencies.
        
        Args:
            db: Database session
        """
        self.db = db
        self.telemetry_repo = TelemetryRepository(db)
        
        logger.info("Telemetry service initialized")
    
    async def start_session(
        self, 
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new telemetry session.
        
        Args:
            session_id: Session identifier
            user_id: Optional user identifier
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary with session information
        """
        try:
            session = await self.telemetry_repo.create_session(
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "telemetry_id": str(session.id)
            }
            
        except Exception as e:
            logger.error(f"Error starting telemetry session: {str(e)}", exc_info=True)
            await self.db.rollback()
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a telemetry session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with success status
        """
        try:
            success = await self.telemetry_repo.close_session(session_id)
            await self.db.commit()
            
            return {
                "success": True,
                "session_closed": success,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error ending telemetry session: {str(e)}", exc_info=True)
            await self.db.rollback()
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def record_event(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record a telemetry event.
        
        Args:
            session_id: Session identifier
            event_type: Event type identifier
            data: Event data dictionary
            
        Returns:
            Dictionary with event information
        """
        try:
            # Get the telemetry session
            session = await self.telemetry_repo.get_session_by_id(session_id)
            
            if not session:
                # Create session if it doesn't exist
                session = await self.telemetry_repo.create_session(session_id)
            
            # Add the event
            event = await self.telemetry_repo.add_event(
                session_id=str(session.id),
                event_type=event_type,
                data=data
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "event_id": str(event.id),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error recording telemetry event: {str(e)}", exc_info=True)
            await self.db.rollback()
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def record_conversation(
        self,
        session_id: str,
        user_input: str,
        response: str,
        selected_agent: str,
        confidence: float,
        processing_time: float
    ) -> Dict[str, Any]:
        """
        Record a conversation event.
        
        Args:
            session_id: Session identifier
            user_input: User message
            response: System response
            selected_agent: Selected agent name
            confidence: Agent confidence score
            processing_time: Processing time in seconds
            
        Returns:
            Dictionary with event information
        """
        data = {
            "user_input": user_input,
            "response": response,
            "selected_agent": selected_agent,
            "confidence": confidence,
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.record_event(
            session_id=session_id,
            event_type="conversation",
            data=data
        )
    
    async def get_sessions(
        self,
        days: int = 7,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get recent telemetry sessions with analytics.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of sessions
            offset: Offset for pagination
            
        Returns:
            Dictionary with session information and analytics
        """
        try:
            # Get recent sessions
            sessions = await self.telemetry_repo.get_recent_sessions(
                days=days,
                limit=limit,
                offset=offset
            )
            
            # Format session data with analytics
            formatted_sessions = []
            for session in sessions:
                # Get events for this session
                events = await self.telemetry_repo.get_session_events(str(session.id))
                
                # Calculate session analytics
                conversation_count = sum(1 for e in events if e.event_type == "conversation")
                
                # Calculate duration if session is closed
                duration = None
                if session.end_time:
                    duration = (session.end_time - session.start_time).total_seconds()
                
                # Count agent usage
                agents = {}
                for event in events:
                    if event.event_type == "conversation" and "selected_agent" in event.data:
                        agent = event.data["selected_agent"]
                        agents[agent] = agents.get(agent, 0) + 1
                
                formatted_sessions.append({
                    "session_id": session.session_id,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat() if session.end_time else None,
                    "duration": duration,
                    "conversation_count": conversation_count,
                    "event_count": len(events),
                    "agents": agents,
                    "user_id": session.user_id,
                    "metadata": session.metadata
                })
            
            return {
                "success": True,
                "sessions": formatted_sessions,
                "total": len(formatted_sessions),
                "days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting telemetry sessions: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "sessions": []
            }
    
    async def get_session_events(
        self,
        session_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get events for a telemetry session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of events
            
        Returns:
            Dictionary with event information
        """
        try:
            # Get the telemetry session
            session = await self.telemetry_repo.get_session_by_id(session_id)
            
            if not session:
                return {
                    "success": False,
                    "error": "Session not found",
                    "session_id": session_id,
                    "events": []
                }
            
            # Get events
            events = await self.telemetry_repo.get_session_events(
                session_id=str(session.id),
                limit=limit
            )
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_events.append({
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                })
            
            return {
                "success": True,
                "session_id": session_id,
                "events": formatted_events,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None
            }
            
        except Exception as e:
            logger.error(f"Error getting session events: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "events": []
            }
    
    async def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get telemetry statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Get agent distribution
            agent_distribution = await self.telemetry_repo.get_agent_distribution(days)
            
            # For a complete implementation, we would calculate more metrics
            # For now, return basic statistics
            
            from sqlalchemy import func, select
            from backend.database.models import TelemetryEvent, TelemetrySession
            
            # Count total conversations
            query = select(func.count()).select_from(TelemetryEvent).where(
                TelemetryEvent.event_type == "conversation"
            )
            result = await self.db.execute(query)
            total_conversations = result.scalar() or 0
            
            return {
                "total_conversations": total_conversations,
                "agent_distribution": agent_distribution
            }
            
        except Exception as e:
            logger.error(f"Error getting telemetry stats: {str(e)}", exc_info=True)
            
            return {
                "total_conversations": 0,
                "agent_distribution": {}
            }