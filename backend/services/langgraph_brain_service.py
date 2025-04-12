"""
Core brain service for Staples Brain using LangGraph.
Handles coordination between different agents and processing of user requests.
"""
import logging
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import openai

from backend.config.config import Config
from backend.brain.agents import LangGraphAgentFactory, LangGraphOrchestrator
from backend.utils.api_utils import create_success_response, create_error_response

logger = logging.getLogger(__name__)


def retry_async(max_attempts=3, base_delay=1, max_delay=10):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"Retry {attempt+1}/{max_attempts} after error: {str(e)}. Waiting {delay}s...")
                        await asyncio.sleep(delay)
            
            # If we've exhausted all retries, raise the last exception
            raise last_exception
        return wrapper
    return decorator


class LangGraphBrainService:
    """
    Core brain service using LangGraph agents that coordinates processing of user requests.
    """
    
    def __init__(
        self,
        orchestrator: Optional[LangGraphOrchestrator] = None,
        llm: Optional[ChatOpenAI] = None,
        config: Optional[Config] = None,
        agent_factory: Optional[LangGraphAgentFactory] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """
        Initialize the brain service with dependencies.
        
        Args:
            orchestrator: Optional orchestrator instance
            llm: Optional language model instance
            config: Optional configuration instance
            agent_factory: Optional agent factory instance
            db_session: Optional database session
        """
        self.config = config or Config()
        self.db_session = db_session
        
        # Initialize language model if not provided
        self.llm = llm or self._initialize_llm()
        
        # Initialize agent factory if not provided
        self.agent_factory = agent_factory
        
        # Initialize orchestrator if not provided
        self.orchestrator = orchestrator or LangGraphOrchestrator(llm=self.llm)
        
        logger.info("Initialized LangGraph Brain Service")
    
    def _initialize_llm(self) -> ChatOpenAI:
        """
        Initialize the language model for the brain service.
        
        Returns:
            ChatOpenAI instance
        """
        # Get API key from environment or config
        api_key = getattr(self.config, "OPENAI_API_KEY", None)
        
        # Get default model from config or use a sensible default
        default_model = getattr(self.config, "DEFAULT_LLM_MODEL", "gpt-4o")
        
        # Get OpenAI client options from config
        client_kwargs = getattr(self.config, "OPENAI_CLIENT_KWARGS", {})
        
        # Log OpenAI version information
        try:
            logger.info(f"Using OpenAI version: {openai.__version__}")
            logger.info(f"Using langchain-openai version: {ChatOpenAI.__module__}")
            
            # Get Python version information
            import sys
            logger.info(f"Python version: {sys.version.split(' ')[0]}")
        except Exception as e:
            logger.warning(f"Error logging version information: {str(e)}")
        
        # Initialize custom OpenAI client if needed
        if client_kwargs:
            logger.info("Initialized with custom OpenAI client")
            
        # Initialize the language model
        llm = ChatOpenAI(
            api_key=api_key,
            model=default_model,
            temperature=0.7,
            **client_kwargs
        )
        
        logger.info(f"Initialized LLM with model {default_model}")
        return llm
    
    async def initialize(self):
        """
        Initialize the brain service by loading agents from the database.
        This method should be called after the service is created but before it's used.
        """
        if not self.db_session:
            logger.error("Cannot initialize brain service: No database session provided")
            return
            
        if not self.agent_factory:
            self.agent_factory = LangGraphAgentFactory(self.db_session)
            
        # Load all active agents from the database
        try:
            agents = await self.agent_factory.get_all_active_agents()
            
            # Register agents with the orchestrator
            for agent in agents:
                self.orchestrator.register_agent(agent)
                
            logger.info(f"Initialized LangGraph Brain Service with {len(agents)} agents")
        except Exception as e:
            logger.error(f"Error initializing brain service: {str(e)}", exc_info=True)
    
    async def cleanup(self):
        """
        Clean up resources used by the service.
        This method is called when the service is being disposed.
        """
        # Nothing to clean up for now
        pass
    
    @retry_async(max_attempts=3, base_delay=1, max_delay=10)
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
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
                
            # Process message through orchestrator
            result = await self.orchestrator.process_message(
                message=message,
                session_id=session_id,
                context=context or {}
            )
            
            # Return processed result
            return {
                "response": result.get("response", ""),
                "agent": result.get("agent", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "metadata": {
                    "session_id": session_id,
                    "entities": result.get("entities", {}),
                    "tools_used": result.get("tools_used", []),
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                "response": "I apologize, but I encountered an error while processing your request.",
                "agent": "error_handler",
                "confidence": 0.0,
                "error": str(e),
                "metadata": {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        Get a list of available agents.
        
        Returns:
            Dictionary containing agent information
        """
        try:
            # Get agent names from orchestrator
            agent_names = self.orchestrator.list_agents()
            
            # For simple integration just return the names
            # The API endpoint will add additional details from database
            return {"agents": agent_names}
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return {
                "agents": [],
                "error": str(e)
            }
    
    async def register_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new agent with the system.
        
        Args:
            agent_config: Agent configuration dictionary
            
        Returns:
            Result of agent registration
        """
        try:
            # Validate required fields
            required_fields = ["name", "description", "agent_type"]
            for field in required_fields:
                if field not in agent_config:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            if not self.agent_factory or not self.db_session:
                return {
                    "success": False,
                    "error": "Agent factory or database session not initialized"
                }
            
            # Create the agent in the database
            from backend.repositories.agent_repository import AgentRepository
            agent_repo = AgentRepository(self.db_session)
            
            # Create agent definition
            agent_id = await agent_repo.create_agent(
                name=agent_config["name"],
                description=agent_config["description"],
                agent_type=agent_config["agent_type"],
                created_by=agent_config.get("created_by", "system"),
                is_system=agent_config.get("is_system", False),
                status=agent_config.get("status", "draft")
            )
            
            return {
                "success": True,
                "agent_id": str(agent_id),
                "message": f"Agent {agent_config['name']} created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error registering agent: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Error registering agent: {str(e)}"
            }
    
    async def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing system statistics
        """
        try:
            # Collect statistics
            stats = {
                "total_conversations": await self._get_conversation_count(days),
                "agent_distribution": await self._get_agent_distribution(days),
                "response_times": await self._get_response_time_metrics(days),
                "error_stats": await self._get_error_stats(days),
                "period_days": days,
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
            return {
                "error": f"Failed to retrieve system statistics: {str(e)}"
            }
    
    async def _get_agent_distribution(self, days: int) -> Dict[str, Any]:
        """
        Get agent usage distribution.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Agent distribution data
        """
        # This would be implemented with actual telemetry data
        # For now, return placeholder data based on available agents
        try:
            agent_names = self.orchestrator.list_agents()
            distribution = {}
            
            # Create distribution based on agent names
            for agent_name in agent_names:
                distribution[agent_name] = 0
            
            # For now, we're returning zeroes since we don't have real data
            # In a real system, this would query a database
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting agent distribution: {str(e)}", exc_info=True)
            return {}
    
    async def _get_response_time_metrics(self, days: int) -> Dict[str, float]:
        """
        Get response time metrics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Response time metrics
        """
        # This would be implemented with actual telemetry data
        return {
            "avg": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0
        }
    
    async def _get_error_stats(self, days: int) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Error statistics
        """
        # This would be implemented with actual telemetry data
        return {
            "rate": 0.0,
            "types": {}
        }
    
    async def _get_conversation_count(self, days: int) -> int:
        """
        Get total conversation count.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Conversation count
        """
        # This would be implemented with actual database queries
        return 0