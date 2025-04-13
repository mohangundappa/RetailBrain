"""
LangGraph Agent interface for GraphOrchestrator.

This module defines the base class for agents that can be used with the LangGraph
orchestration system. It provides a common interface for different types of agents.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class LangGraphAgent(ABC):
    """
    Base interface for agents used in the LangGraph orchestration.
    
    This class defines the common interface that all agents must implement
    to be compatible with the orchestration system.
    """
    
    def __init__(
        self, 
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent with identification and configuration.
        
        Args:
            id: Unique identifier for the agent
            name: Display name for the agent
            description: Description of the agent's capabilities
            config: Configuration dictionary for the agent
        """
        self.id = id or str(uuid.uuid4())
        self.name = name or f"agent_{self.id[:8]}"
        self.description = description or f"Agent {self.name}"
        self.config = config or {}
        
        # Track metrics
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.average_response_time = 0
        
        logger.info(f"Initialized agent {self.name} with ID {self.id}")
    
    @abstractmethod
    async def process(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message and generate a response.
        
        Args:
            message: User input message
            context: Additional context information
            
        Returns:
            Dictionary containing the response and metadata
        """
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message from the orchestration system.
        
        This method is called by the orchestration system and maintains
        compatibility with the expected interface.
        
        Args:
            message: User input message
            session_id: Session identifier
            context: Additional context information
            
        Returns:
            Dictionary containing the response and metadata
        """
        logger.info(f"Agent {self.name} processing message for session {session_id}")
        
        # Add session_id to context if present
        if session_id and context:
            context["session_id"] = session_id
        
        # Call the underlying process method
        result = await self.process(message, context)
        
        return result
        pass
    
    def get_id(self) -> str:
        """
        Get the unique identifier for this agent.
        
        Returns:
            Agent ID
        """
        return self.id
        
    def get_name(self) -> str:
        """
        Get the display name of this agent.
        
        Returns:
            Agent name
        """
        return self.name
        
    def get_description(self) -> str:
        """
        Get the agent description.
        
        Returns:
            Agent description string
        """
        return self.description
    
    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities this agent supports.
        
        Returns:
            List of capability strings
        """
        return self.config.get("capabilities", [])
    
    def update_metrics(self, success: bool, response_time: float) -> None:
        """
        Update the agent's performance metrics.
        
        Args:
            success: Whether the request was successful
            response_time: Time taken to process the request in seconds
        """
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Update average response time with exponential moving average
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            # Use a weight of 0.1 for the new data point
            self.average_response_time = (0.9 * self.average_response_time) + (0.1 * response_time)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get the agent's performance metrics.
        
        Returns:
            Dictionary containing metrics
        """
        return {
            "id": self.id,
            "name": self.name,
            "request_count": self.request_count,
            "success_rate": self.success_count / max(1, self.request_count),
            "error_count": self.error_count,
            "average_response_time": self.average_response_time,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None
        }