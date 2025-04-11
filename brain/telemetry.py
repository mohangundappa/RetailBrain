"""
Telemetry system for the orchestration engine.
This module provides detailed visibility into the agent selection process 
and tracks events throughout the lifetime of a request.

The telemetry system is designed to be:
1. Lightweight: Minimal impact on performance
2. Informative: Provides detailed insights into decision-making processes
3. Persistent: Events can be retrieved for debugging and analysis
4. Extensible: Easy to add new event types and tracking capabilities

Usage:
    # Track a request
    event_id = collector.track_request_received(session_id, user_input)
    
    # Track agent selection
    collector.track_agent_selection(
        session_id, 
        agent_name="OrderTrackingAgent", 
        confidence=0.85, 
        selection_method="confidence_threshold",
        parent_id=event_id
    )
    
    # Get session events
    events = telemetry_system.get_session_events(session_id)
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Union

logger = logging.getLogger(__name__)


class OrchestrationEvent:
    """Represents a single event in the orchestration process."""
    
    def __init__(self, 
                event_type: str,
                timestamp: Optional[datetime] = None,
                details: Optional[Dict[str, Any]] = None,
                parent_id: Optional[str] = None):
        """
        Initialize an orchestration event.
        
        Args:
            event_type: Type of event (e.g., 'request_received', 'agent_confidence')
            timestamp: When this event occurred
            details: Additional event details
            parent_id: ID of parent event (for hierarchical relationships)
        """
        self.event_type = event_type
        self.timestamp = timestamp or datetime.now()
        self.details = details or {}
        self.parent_id = parent_id
        self.id = f"{int(time.time() * 1000)}-{hash(str(self.details))}"
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            Dictionary representation of this event
        """
        return {
            "event_id": self.id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
            "details": self.details
        }


class OrchestratorTelemetry:
    """Telemetry system for tracking the orchestration process."""
    
    def __init__(self, enable_persistence: bool = True, max_sessions: int = 20):
        """
        Initialize the telemetry system.
        
        Args:
            enable_persistence: Whether to store events in memory
            max_sessions: Maximum number of sessions to track
        """
        self.enable_persistence = enable_persistence
        self.max_sessions = max_sessions
        self.current_sessions = {}  # session_id -> list of events
        
    def track_event(self, session_id: str, event: OrchestrationEvent) -> None:
        """
        Track an orchestration event.
        
        Args:
            session_id: Session identifier
            event: The event to track
        """
        # Log the event
        event_dict = event.to_dict()
        logger.debug(f"TELEMETRY:{session_id}:{event.event_type}: {json.dumps(event_dict)}")
        
        # Store if persistence is enabled
        if self.enable_persistence:
            if session_id not in self.current_sessions:
                # Ensure we don't exceed max sessions
                if len(self.current_sessions) >= self.max_sessions:
                    # Remove oldest session
                    oldest_session = min(self.current_sessions.keys(), 
                                      key=lambda k: self.current_sessions[k][0].timestamp 
                                      if self.current_sessions[k] else datetime.now())
                    del self.current_sessions[oldest_session]
                
                # Initialize new session
                self.current_sessions[session_id] = []
                
            # Add event to session
            self.current_sessions[session_id].append(event)
            
    def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of event dictionaries
        """
        if not self.enable_persistence:
            logger.warning("Attempting to get session events when persistence is disabled")
            return []
            
        return [event.to_dict() for event in self.current_sessions.get(session_id, [])]
        
    def get_latest_sessions(self, limit: int = 5) -> List[str]:
        """
        Get the most recent session IDs.
        
        Args:
            limit: Maximum number of session IDs to return
            
        Returns:
            List of session IDs
        """
        if not self.enable_persistence:
            logger.warning("Attempting to get latest sessions when persistence is disabled")
            return []
            
        # Sort sessions by most recent event
        sorted_sessions = sorted(
            self.current_sessions.items(),
            key=lambda item: max((event.timestamp for event in item[1]), default=datetime.min),
            reverse=True
        )
        
        return [session_id for session_id, _ in sorted_sessions[:limit]]
        
    def clear_session(self, session_id: str) -> None:
        """
        Clear events for a specific session.
        
        Args:
            session_id: Session identifier
        """
        if self.enable_persistence and session_id in self.current_sessions:
            del self.current_sessions[session_id]
            logger.debug(f"Cleared telemetry for session {session_id}")
            
    def clear_all_sessions(self) -> None:
        """Clear all tracked sessions."""
        if self.enable_persistence:
            self.current_sessions = {}
            logger.debug("Cleared all telemetry sessions")


class OrchestrationTelemetryCollector:
    """Collects telemetry for the orchestration process."""
    
    def __init__(self, telemetry: OrchestratorTelemetry):
        """
        Initialize with a telemetry system.
        
        Args:
            telemetry: Telemetry system to use
        """
        self.telemetry = telemetry
        
    def track_request_received(self, session_id: str, user_input: str) -> str:
        """
        Track a new user request.
        
        Args:
            session_id: Session identifier
            user_input: User's input text
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="request_received",
            details={
                "user_input": user_input[:100] + "..." if len(user_input) > 100 else user_input
            }
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_intent_identification(self, session_id: str, intent: str, 
                                  confidence: float, parent_id: Optional[str] = None) -> str:
        """
        Track intent identification.
        
        Args:
            session_id: Session identifier
            intent: Identified intent
            confidence: Confidence score
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="intent_identified",
            details={
                "intent": intent,
                "confidence": confidence
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_special_case_check(self, session_id: str, is_special_case: bool, 
                               case_type: Optional[str] = None, 
                               parent_id: Optional[str] = None) -> str:
        """
        Track special case handling.
        
        Args:
            session_id: Session identifier
            is_special_case: Whether a special case was identified
            case_type: Type of special case
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="special_case_check",
            details={
                "is_special_case": is_special_case,
                "case_type": case_type,
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_intent_routing(self, session_id: str, intent: str, 
                           agent_name: Optional[str] = None,
                           succeeded: bool = False,
                           parent_id: Optional[str] = None) -> str:
        """
        Track intent-based routing.
        
        Args:
            session_id: Session identifier
            intent: Identified intent
            agent_name: Selected agent (if any)
            succeeded: Whether routing succeeded
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="intent_routing",
            details={
                "intent": intent,
                "agent_name": agent_name,
                "succeeded": succeeded
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_continuity_check(self, session_id: str, last_agent: Optional[str] = None,
                             is_recent: bool = False,
                             continue_same_agent: bool = False,
                             reason: Optional[str] = None,
                             parent_id: Optional[str] = None) -> str:
        """
        Track conversation continuity check.
        
        Args:
            session_id: Session identifier
            last_agent: Last agent used
            is_recent: Whether the last interaction was recent
            continue_same_agent: Whether to continue with the same agent
            reason: Reason for decision
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="continuity_check",
            details={
                "last_agent": last_agent,
                "is_recent": is_recent,
                "continue_same_agent": continue_same_agent,
                "reason": reason
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_topic_change(self, session_id: str, from_agent: Optional[str] = None,
                         to_agent: Optional[str] = None,
                         detected: bool = False,
                         detector_type: Optional[str] = None,
                         parent_id: Optional[str] = None) -> str:
        """
        Track topic change detection.
        
        Args:
            session_id: Session identifier
            from_agent: Current agent
            to_agent: New agent
            detected: Whether a topic change was detected
            detector_type: Type of detector that found the change
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="topic_change",
            details={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "detected": detected,
                "detector_type": detector_type
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_agent_confidence(self, session_id: str, agent_name: str,
                             base_confidence: float,
                             adjusted_confidence: float,
                             context_used: bool = False,
                             parent_id: Optional[str] = None) -> str:
        """
        Track agent confidence scoring.
        
        Args:
            session_id: Session identifier
            agent_name: Agent name
            base_confidence: Base confidence score
            adjusted_confidence: Adjusted confidence score
            context_used: Whether context was used
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="agent_confidence",
            details={
                "agent_name": agent_name,
                "base_confidence": base_confidence,
                "adjusted_confidence": adjusted_confidence,
                "context_used": context_used
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_agent_selection(self, session_id: str, agent_name: Optional[str] = None,
                            confidence: float = 0.0,
                            selection_method: Optional[str] = None,
                            parent_id: Optional[str] = None) -> str:
        """
        Track agent selection.
        
        Args:
            session_id: Session identifier
            agent_name: Selected agent
            confidence: Confidence score
            selection_method: Method used for selection
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="agent_selection",
            details={
                "agent_name": agent_name,
                "confidence": confidence,
                "selection_method": selection_method
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_response_generation(self, session_id: str, agent_name: Optional[str] = None,
                                success: bool = True,
                                response_type: Optional[str] = None,
                                processing_time: Optional[float] = None,
                                parent_id: Optional[str] = None) -> str:
        """
        Track response generation.
        
        Args:
            session_id: Session identifier
            agent_name: Agent that generated the response
            success: Whether response generation succeeded
            response_type: Type of response
            processing_time: Time taken to generate response
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="response_generation",
            details={
                "agent_name": agent_name,
                "success": success,
                "response_type": response_type,
                "processing_time": processing_time
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_error(self, session_id: str, error_type: str,
                  error_message: str,
                  recoverable: bool = True,
                  parent_id: Optional[str] = None) -> str:
        """
        Track an error.
        
        Args:
            session_id: Session identifier
            error_type: Type of error
            error_message: Error message
            recoverable: Whether the error is recoverable
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type="error",
            details={
                "error_type": error_type,
                "error_message": error_message,
                "recoverable": recoverable
            },
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id
        
    def track_custom_event(self, session_id: str, event_type: str,
                         details: Dict[str, Any],
                         parent_id: Optional[str] = None) -> str:
        """
        Track a custom event.
        
        Args:
            session_id: Session identifier
            event_type: Custom event type
            details: Event details
            parent_id: Parent event ID
            
        Returns:
            Event ID
        """
        event = OrchestrationEvent(
            event_type=event_type,
            details=details,
            parent_id=parent_id
        )
        self.telemetry.track_event(session_id, event)
        return event.id


# Global telemetry instance
telemetry_system = OrchestratorTelemetry()
collector = OrchestrationTelemetryCollector(telemetry_system)