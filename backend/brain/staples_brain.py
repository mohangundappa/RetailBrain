import os
import logging
from typing import Dict, Any, List, Optional
import json
import asyncio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGenerationChunk
from langchain_core.messages import AIMessageChunk, BaseMessage
from backend.agents.base_agent import BaseAgent
from backend.brain.orchestrator import Orchestrator

# Import all agent classes for factory method access
from backend.agents.package_tracking import PackageTrackingAgent
from backend.agents.reset_password import ResetPasswordAgent
from backend.agents.store_locator import StoreLocatorAgent
from backend.agents.product_info import ProductInfoAgent
from backend.agents.returns_processing import ReturnsProcessingAgent

# Get OpenAI configuration from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

def get_openai_client():
    """
    Returns an initialized OpenAI client using the API key from environment.
    
    This function is used by various components that need direct access to the OpenAI API,
    including the agent builder's LLM assist feature.
    
    Returns:
        OpenAI client instance
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        return client
    except ImportError:
        logger.error("OpenAI package not installed. Please install it with 'pip install openai'.")
        raise
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        raise

logger = logging.getLogger(__name__)

class StaplesBrain:
    """
    The main Staples Brain class that orchestrates all agents and handles user requests.
    
    This class serves as the main entry point for external systems to interact with 
    the Staples AI ecosystem.
    """
    
    def __init__(self):
        """Initialize the Staples Brain with all required agents."""
        logger.debug("Initializing Staples Brain")
        
        # Initialize language model
        try:
            if OPENAI_API_KEY:
                # Use actual OpenAI if API key is available
                from langchain_openai import ChatOpenAI
                import importlib.metadata
                
                # Debug: Log version information
                openai_version = importlib.metadata.version("openai")
                langchain_openai_version = importlib.metadata.version("langchain-openai")
                logger.info(f"Using OpenAI version: {openai_version}")
                logger.info(f"Using langchain-openai version: {langchain_openai_version}")
                
                # Handle compatibility issues between different versions of LangChain and OpenAI
                # Particularly for Python 3.12.7 where 'proxies' parameter is causing issues
                
                try:
                    import platform
                    python_version = platform.python_version()
                    logger.info(f"Python version: {python_version}")
                    
                    # For Python 3.12+ specific handling
                    if python_version.startswith("3.12"):
                        logger.info("Using Python 3.12+ compatibility mode for OpenAI client")
                        # Directly initialize with minimal parameters to avoid proxies param
                        self.llm = ChatOpenAI(
                            model_name=OPENAI_MODEL,
                            temperature=0.3,
                            openai_api_key=OPENAI_API_KEY
                        )
                        logger.info("Initialized with minimal parameters for Python 3.12+")
                    else:
                        # Standard initialization for other Python versions
                        from openai import OpenAI
                        try:
                            # Create a dedicated OpenAI client for newer versions
                            openai_client = OpenAI(api_key=OPENAI_API_KEY)
                            
                            # Try initializing with the client parameter first (newer approach)
                            self.llm = ChatOpenAI(
                                model_name=OPENAI_MODEL,
                                client=openai_client,
                                temperature=0.3
                            )
                            logger.info("Initialized with custom OpenAI client")
                        except (TypeError, ValueError) as client_error:
                            logger.warning(f"Error initializing with client parameter: {client_error}")
                            # Fall back to direct initialization (older approach)
                            self.llm = ChatOpenAI(
                                model_name=OPENAI_MODEL,
                                openai_api_key=OPENAI_API_KEY,
                                temperature=0.3
                            )
                            logger.info("Initialized with direct API key")
                except Exception as e:
                    logger.warning(f"LLM initialization error: {str(e)}")
                    if "proxies" in str(e):
                        logger.warning("Detected proxies compatibility issue. Using minimal initialization.")
                        # Try with absolute minimum parameters
                        self.llm = ChatOpenAI(temperature=0.3)
                        logger.info("Initialized with minimal parameters")
                    else:
                        # If it's a different error, re-raise it
                        raise
                logger.info(f"Initialized LLM with model {OPENAI_MODEL}")
            else:
                # Use a mock LLM for demonstration if no API key
                logger.warning("OPENAI_API_KEY not found. Using demo mode with mock responses.")
                
                # Use a demo model with canned responses 
                self.llm = self._create_demo_chat_model()
        except Exception as e:
            logger.error(f"Error initializing language model: {str(e)}", exc_info=True)
            logger.warning("Falling back to demo mode with simple mock responses due to error.")
            self.llm = self._create_simple_chat_model()
        
        # Initialize agents
        self.agents = []
        self._initialize_agents()
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator()
        
        logger.info(f"Staples Brain initialized with {len(self.agents)} agents")
    
    def _create_demo_chat_model(self) -> BaseChatModel:
        """Create a mock chat model with canned responses for demos."""
        class DemoChatModel(BaseChatModel):
            def __init__(self):
                super().__init__()
                self._response_counter = 0
                self._responses = [
                    "0.9",  # For confidence checks
                    '{"tracking_number": "TRACK123456", "shipping_carrier": "UPS", "order_number": null, "time_frame": "3 days"}',
                    "Your package with tracking number TRACK123456 is currently in transit and expected to be delivered in 3 days. It's currently in Chicago, IL and should arrive at your location soon. You can track its progress using the UPS website or app with your tracking number.",
                    "0.85",  # For confidence checks
                    '{"email": "user@example.com", "username": null, "account_type": "Staples.com", "issue": "forgot password"}',
                    "I've sent password reset instructions to your email address (user@example.com). Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes. If you don't see it, please check your spam folder."
                ]
            
            @property
            def _llm_type(self) -> str:
                return "demo_chat_model"
                
            async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, 
                               run_manager = None, **kwargs):
                response = self._responses[self._response_counter % len(self._responses)]
                self._response_counter += 1
                
                message = AIMessageChunk(content=response)
                chunk = ChatGenerationChunk(message=message)
                return ChatResult(generations=[chunk])
            
            def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, 
                        run_manager = None, **kwargs):
                return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))
        
        return DemoChatModel()
    
    def _create_simple_chat_model(self) -> BaseChatModel:
        """Create a simple mock chat model for fallback situations."""
        class SimpleChatModel(BaseChatModel):
            @property
            def _llm_type(self) -> str:
                return "simple_chat_model"
                
            async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, 
                              run_manager = None, **kwargs):
                message = AIMessageChunk(content="This is a mock response for demonstration purposes.")
                chunk = ChatGenerationChunk(message=message)
                return ChatResult(generations=[chunk])
            
            def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, 
                       run_manager = None, **kwargs):
                return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))
        
        return SimpleChatModel()
    
    def _initialize_agents(self):
        """Initialize all required agents using the factory method for standardization."""
        try:
            # Define the agent types to initialize
            agent_types = [
                "package_tracking", 
                "reset_password", 
                "store_locator", 
                # Removed product_info and returns_processing agents as requested
            ]
            
            # Create each agent using the factory method for standardized naming
            for agent_type in agent_types:
                agent = BaseAgent.create_agent(agent_type, self.llm)
                self.agents.append(agent)
                logger.info(f"{agent.name} initialized")
                
        except Exception as e:
            logger.error(f"Error initializing agents: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize agents: {str(e)}")
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request and route it to the appropriate agent.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A response from the appropriate agent
        """
        if context is None:
            context = {}
            
        logger.debug(f"Processing request: {user_input}")
        
        try:
            # Use the orchestrator to route to the best agent
            session_id = context.get("session_id", "default_session")
            user_id = context.get("user_id")
            # Call the async process_request method in the orchestrator
            response = await self.orchestrator.process_request(user_input, session_id, context)
            return response
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I'm sorry, I encountered an error while processing your request. Please try again or contact customer support.",
                "agent": "Error Handler"
            }
    
    def get_agent_names(self) -> List[str]:
        """
        Get a list of available agent names.
        
        Returns:
            A list of agent names
        """
        return [agent.name for agent in self.agents]
    
    def get_agent_by_name(self, name: str):
        """
        Get an agent by name.
        
        Args:
            name: The name of the agent to retrieve
            
        Returns:
            The agent if found, None otherwise
        """
        for agent in self.agents:
            if agent.name.lower() == name.lower():
                return agent
        return None

def initialize_staples_brain():
    """
    Factory function to create and initialize a Staples Brain instance.
    
    Returns:
        An initialized StaplesBrain instance
    """
    try:
        brain = StaplesBrain()
        return brain
    except Exception as e:
        logger.error(f"Failed to initialize Staples Brain: {str(e)}", exc_info=True)
        raise
