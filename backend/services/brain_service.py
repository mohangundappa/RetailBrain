"""
Core brain service for Staples Brain.
Handles coordination between different agents and processing of user requests.
"""
import os
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Type
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from openai import OpenAIError

from backend.brain.orchestrator import Orchestrator
from backend.utils.langsmith_utils import init_langsmith
from backend.config.config import Config

# Set up logging
logger = logging.getLogger("staples_brain")

# Initialize LangSmith for telemetry if API key is available
init_langsmith()

# Retry decorator for handling transient errors
def retry_async(max_attempts=3, base_delay=1, max_delay=10):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except (OpenAIError, asyncio.TimeoutError) as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        logger.warning(
                            f"Attempt {attempt} failed with error: {str(e)}. "
                            f"Retrying in {delay} seconds..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {str(e)}"
                        )
            # Re-raise the last exception
            raise last_exception
        return wrapper
    return decorator


class BrainService:
    """
    Core brain service that coordinates processing of user requests.
    """
    
    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        llm: Optional[BaseChatModel] = None,
        config: Optional[Config] = None,
        agent_factory: Optional[Any] = None,
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
        # Set up configuration
        self.config = config or Config()
        
        # Get API key from config or environment
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
            raise ValueError("OpenAI API key not found")
        
        # Initialize the language model
        model_name = getattr(self.config, 'OPENAI_MODEL', 'gpt-4o')
        temperature = getattr(self.config, 'OPENAI_TEMPERATURE', 0.2)
        max_tokens = getattr(self.config, 'OPENAI_MAX_TOKENS', 1024)
        
        self.llm = llm or ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Initialize the orchestrator
        self.orchestrator = orchestrator or Orchestrator()
        
        # Store the database session for later use
        self.db_session = db_session
        
        # Store agent factory if provided (will be used during initialization)
        self.agent_factory = agent_factory
        
        # Set service timeout from config
        self.timeout = getattr(self.config, 'SERVICE_TIMEOUT', 30)
        
        logger.info(f"Brain service initialized with model {model_name}")
    
    async def initialize(self):
        """
        Initialize the brain service by loading agents from the database.
        This method should be called after the service is created but before it's used.
        """
        logger.info("Initializing brain service...")
        
        # If we have a database session and agent factory, use them to load agents
        if self.db_session and self.agent_factory:
            try:
                # Import here to avoid circular imports
                from backend.brain.factory import AgentFactory
                
                # Create agent factory if not provided
                if not self.agent_factory:
                    self.agent_factory = AgentFactory(self.db_session)
                
                # Register all active agents with the orchestrator
                registered_count = await self.agent_factory.register_all_agents_with_orchestrator(self.orchestrator)
                logger.info(f"Loaded {registered_count} agents from database into orchestrator")
                
                return True
            except ImportError as ie:
                logger.warning(f"Could not import AgentFactory: {str(ie)}")
                return False
            except Exception as e:
                logger.error(f"Error initializing agents from database: {str(e)}", exc_info=True)
                return False
        else:
            logger.info("No database session or agent factory provided, skipping agent loading")
            return False
    
    async def cleanup(self):
        """
        Clean up resources used by the service.
        This method is called when the service is being disposed.
        """
        logger.debug("Cleaning up brain service resources")
        
        # Clean up orchestrator if it has a cleanup method
        if hasattr(self.orchestrator, 'cleanup') and callable(getattr(self.orchestrator, 'cleanup')):
            try:
                await self.orchestrator.cleanup()
            except Exception as e:
                logger.error(f"Error during orchestrator cleanup: {str(e)}", exc_info=True)
    
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
        # Input validation
        if not message or not isinstance(message, str):
            return {
                "response": "I'm sorry, but I received an invalid message format.",
                "metadata": {
                    "agent": "error_handler",
                    "confidence": 1.0,
                    "processing_time": 0,
                    "error": "invalid_input"
                }
            }
        
        # Get session context
        session_context = context or {}
        
        # Log the request
        logger.info(f"Processing request for session {session_id}")
        start_time = time.time()
        
        try:
            # Use timeout to prevent hanging requests
            async with asyncio.timeout(self.timeout):
                # Use the orchestrator to route the request to the appropriate agent
                # Adapt parameters to match the expected signature
                result = await self.orchestrator.process_message(
                    message=message,
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
                
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            logger.error(f"Request timed out after {processing_time:.2f}s for session {session_id}")
            
            return {
                "response": "I'm sorry, but I couldn't process your request in time. Please try again or break your question into smaller parts.",
                "metadata": {
                    "agent": "error_handler",
                    "confidence": 1.0,
                    "processing_time": processing_time,
                    "error": "timeout"
                }
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            
            return {
                "response": "I'm sorry, but an error occurred while processing your request. Our team has been notified of the issue.",
                "metadata": {
                    "agent": "error_handler",
                    "confidence": 1.0,
                    "processing_time": processing_time,
                    "error": str(e)
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
            required_fields = ["name", "description", "template"]
            for field in required_fields:
                if field not in agent_config:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            # Register the agent with the orchestrator
            if hasattr(self.orchestrator, 'register_agent') and callable(getattr(self.orchestrator, 'register_agent')):
                agent = await self.orchestrator.register_agent(agent_config)
                return {
                    "success": True,
                    "agent": {
                        "id": agent.id,
                        "name": agent.name,
                        "description": agent.description
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Agent registration not supported by the current orchestrator"
                }
                
        except Exception as e:
            logger.error(f"Failed to register agent: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
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
            # In a production system, this would pull from telemetry database
            # We'll implement more realistic stats using the components available
            
            # Get agent usage stats if available
            agent_distribution = await self._get_agent_distribution(days)
            
            # Get performance metrics
            response_times = await self._get_response_time_metrics(days)
            
            # Get error metrics
            error_stats = await self._get_error_stats(days)
            
            # Get conversation count
            conversation_count = await self._get_conversation_count(days)
            
            return {
                "total_conversations": conversation_count,
                "agent_distribution": agent_distribution,
                "response_times": response_times,
                "error_stats": error_stats,
                "days_analyzed": days
            }
            
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