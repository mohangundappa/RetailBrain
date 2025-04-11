"""
Enhanced logging for the orchestration system.
This module provides structured logging to improve observability.
"""
import logging
import json
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class OrchestrationLogger:
    """Enhanced logging for orchestration operations."""
    
    def __init__(self, logger=None):
        """
        Initialize with a logger instance.
        
        Args:
            logger: Logger instance to use (if None, use module logger)
        """
        self.logger = logger or logging.getLogger(__name__)
        
    def log_request(self, user_input: str, session_id: str) -> None:
        """
        Log a new user request.
        
        Args:
            user_input: The user's input text
            session_id: The session identifier
        """
        # Truncate long inputs
        truncated_input = user_input[:100] + "..." if len(user_input) > 100 else user_input
        self.logger.info(f"Processing request: session={session_id}, input={truncated_input}")
        
    def log_intent(self, intent: str, confidence: float, user_input: str) -> None:
        """
        Log intent identification.
        
        Args:
            intent: The identified intent
            confidence: The confidence score
            user_input: The user's input text
        """
        truncated_input = user_input[:50] + "..." if len(user_input) > 50 else user_input
        self.logger.info(f"Identified intent: {intent} (confidence: {confidence:.2f}) for input: {truncated_input}")
        
    def log_agent_scores(self, agent_scores: List[Tuple[str, float]]) -> None:
        """
        Log agent confidence scores.
        
        Args:
            agent_scores: List of (agent_name, confidence) tuples
        """
        formatted_scores = ", ".join([f"{agent}: {score:.2f}" for agent, score in agent_scores])
        self.logger.debug(f"Agent confidence scores: {formatted_scores}")
        
    def log_agent_selection(self, agent_name: str, confidence: float, 
                          context_used: bool, intent: Optional[str] = None) -> None:
        """
        Log the selection of an agent.
        
        Args:
            agent_name: The selected agent name
            confidence: The confidence score
            context_used: Whether context contributed to selection
            intent: The identified intent (if any)
        """
        context_info = " (using context)" if context_used else ""
        intent_info = f", intent: {intent}" if intent else ""
        self.logger.info(f"Selected agent '{agent_name}' with confidence {confidence:.2f}{context_info}{intent_info}")
        
    def log_no_suitable_agent(self, user_input: str) -> None:
        """
        Log when no suitable agent is found.
        
        Args:
            user_input: The user's input text
        """
        truncated_input = user_input[:50] + "..." if len(user_input) > 50 else user_input
        self.logger.warning(f"No suitable agent found for: {truncated_input}")
        
    def log_topic_change(self, from_agent: str, to_agent: str, reason: str) -> None:
        """
        Log a detected topic change.
        
        Args:
            from_agent: Current agent name
            to_agent: New agent name
            reason: Reason for the topic change
        """
        self.logger.info(f"Topic change detected: {from_agent} -> {to_agent} (reason: {reason})")
        
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """
        Log an error with context information.
        
        Args:
            error: The exception that was raised
            context: Additional context information
        """
        error_message = f"Error in orchestration: {str(error)}"
        if context:
            # Safely convert context to string, handling non-serializable objects
            try:
                context_str = json.dumps(context)
                error_message += f" Context: {context_str}"
            except:
                error_message += f" Context available but not serializable"
                
        self.logger.error(error_message, exc_info=True)
        
    def log_continuity(self, agent_name: str, base_confidence: float, 
                     adjusted_confidence: float, is_explicit: bool) -> None:
        """
        Log the application of a continuity bonus.
        
        Args:
            agent_name: The agent's name
            base_confidence: Original confidence score
            adjusted_confidence: Confidence after continuity bonus
            is_explicit: Whether this was an explicit continuity request
        """
        continuity_type = "explicit" if is_explicit else "time-based"
        self.logger.debug(f"Applied {continuity_type} continuity bonus to {agent_name}: "
                       f"{base_confidence:.2f} -> {adjusted_confidence:.2f}")