"""
Core brain service for Staples Brain.
Handles coordination between different agents and processing of user requests.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from backend.brain.orchestrator import Orchestrator
from backend.utils.langsmith_utils import init_langsmith

# Set up logging
logger = logging.getLogger("staples_brain")

# Initialize LangSmith for telemetry if API key is available
init_langsmith()

class BrainService:
    """
    Core brain service that coordinates processing of user requests.
    """
    
    def __init__(self):
        """Initialize the brain service."""
        # Get the OpenAI API key from environment variables
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
            raise ValueError("OpenAI API key not found")
        
        # Initialize the language model
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            max_tokens=1024,
        )
        
        # Initialize the orchestrator
        self.orchestrator = Orchestrator()
        
        logger.info("Brain service initialized")
    
    async def process_request(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request by routing to appropriate agent.
        
        Args:
            message: User message
            session_id: Session identifier for maintaining conversation state
            context: Additional context information
            
        Returns:
            Response with content and metadata
        """
        # Get session context
        session_context = context or {}
        
        # Log the request
        logger.info(f"Processing request for session {session_id}")
        
        # Use the orchestrator to route the request to the appropriate agent
        result = await self.orchestrator.process_message(
            user_input=message,
            session_id=session_id,
            context=session_context
        )
        
        # Return the formatted result
        return {
            "response": result["response"],
            "metadata": {
                "agent": result["agent"],
                "confidence": result["confidence"],
                "processing_time": result["processing_time"]
            }
        }
    
    async def list_agents(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a list of available agents.
        
        Returns:
            Dictionary containing agent information
        """
        agents = self.orchestrator.list_agents()
        
        # Format agent information
        formatted_agents = []
        for agent in agents:
            formatted_agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "is_built_in": agent.is_built_in,
                "capabilities": agent.capabilities,
                "creator": agent.creator if hasattr(agent, "creator") else None,
                "created_at": agent.created_at if hasattr(agent, "created_at") else None,
            })
        
        return {"agents": formatted_agents}
    
    async def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing system statistics
        """
        # In a real system, this would pull from telemetry database
        # For now, return basic information
        return {
            "total_conversations": 0,
            "agent_distribution": {},
            "avg_response_time": 0,
            "error_rate": 0
        }