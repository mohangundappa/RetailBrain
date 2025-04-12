"""
Graph-based brain service for Staples Brain using native LangGraph.
Handles coordination between different agents using LangGraph's StateGraph.
"""
import logging
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
import openai

from backend.config.config import Config
from backend.brain.native_graph import GraphOrchestrator
from backend.brain.agents import LangGraphAgentFactory
from backend.utils.api_utils import create_success_response, create_error_response
from backend.services.langgraph_brain_service import retry_async

logger = logging.getLogger(__name__)


class GraphBrainService:
    """
    Core brain service using native LangGraph that coordinates processing of user requests.
    """
    
    def __init__(
        self,
        orchestrator: Optional[GraphOrchestrator] = None,
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
        self.orchestrator = orchestrator or GraphOrchestrator(llm=self.llm)
        
        # Register a default agent for testing
        from backend.brain.agents.langgraph_factory import DefaultLangGraphAgent
        default_agent = DefaultLangGraphAgent(
            id="package_tracking",
            name="Package Tracking Agent",
            description="Helps track packages and provide shipping updates"
        )
        self.orchestrator.register_agent(default_agent)
        
        logger.info("Initialized GraphBrainService")
    
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
                
            logger.info(f"Initialized GraphBrainService with {len(agents)} agents")
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
        logger.info(f"TRACE: Entered GraphBrainService.process_request")
        
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