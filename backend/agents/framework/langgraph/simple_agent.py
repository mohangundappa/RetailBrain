"""
Simple LangGraph Agent implementation.

This module provides a concrete implementation of the LangGraphAgent
that can be used for testing and prototyping.
"""

import logging
import time
from typing import Dict, Any, Optional

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)


class SimpleAgent(LangGraphAgent):
    """
    Simple implementation of LangGraphAgent for testing purposes.
    
    This agent provides a basic implementation that can be used
    when database agents can't be loaded.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        agent_type: str = "LLM",
        config: Optional[Dict[str, Any]] = None,
        status: str = "active",
        is_system: bool = False,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        version: int = 1
    ):
        """
        Initialize a simple agent.
        
        Args:
            id: Agent ID
            name: Agent name
            description: Agent description
            agent_type: Agent type (LLM, RULE, etc.)
            config: Agent configuration
            status: Agent status
            is_system: Whether the agent is a system agent
            created_at: Creation timestamp
            updated_at: Last update timestamp
            version: Agent version
        """
        super().__init__(id, name, description, config)
        self.agent_type = agent_type
        self.status = status
        self.is_system = is_system
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version
    
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
        start_time = time.time()
        self.request_count += 1
        self.last_request_time = start_time
        
        # Default context
        context = context or {}
        
        try:
            # Get configuration
            system_prompt = self.config.get("system_prompt", "You are a helpful assistant.")
            temperature = self.config.get("temperature", 0.7)
            model = self.config.get("model", "gpt-4")
            
            # Simple mock response based on agent name
            if "general" in self.name.lower():
                response = f"Hello! This is {self.name}. How can I help you today? (Your message: {message})"
            elif "guardrails" in self.name.lower():
                response = f"Content checked by {self.name}. Your message about '{message[:20]}...' is appropriate."
            else:
                response = f"Response from {self.name} (type: {self.agent_type}): Mock response to '{message}'."
            
            # Calculate metrics
            elapsed_time = time.time() - start_time
            self.average_response_time = (
                (self.average_response_time * (self.request_count - 1) + elapsed_time) / self.request_count
            )
            self.success_count += 1
            
            # Log the response
            logger.info(f"Agent {self.name} processed message in {elapsed_time:.2f}s")
            
            # Return response with metadata
            return {
                "message": response,
                "agent_id": self.id,
                "agent_name": self.name,
                "confidence": 0.9,
                "elapsed_time": elapsed_time,
                "model": model,
                "temperature": temperature
            }
            
        except Exception as e:
            # Record error
            self.error_count += 1
            elapsed_time = time.time() - start_time
            
            # Log the error
            logger.error(f"Error in agent {self.name}: {str(e)}")
            
            # Return error response
            return {
                "message": f"Error processing your request: {str(e)}",
                "agent_id": self.id,
                "agent_name": self.name,
                "confidence": 0.0,
                "error": str(e),
                "elapsed_time": elapsed_time
            }