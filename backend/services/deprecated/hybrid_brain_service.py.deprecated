"""
Hybrid Brain Service that supports both legacy agents and LangGraph agents.
This service provides a transition path from hardcoded agents to database-driven agents.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI

from backend.config.config import Config
from backend.services.brain_service import BrainService
from backend.services.langgraph_brain_service import LangGraphBrainService
from backend.utils.api_utils import create_success_response, create_error_response

logger = logging.getLogger(__name__)


class HybridBrainService:
    """
    Hybrid Brain Service that supports both legacy and LangGraph agents.
    
    This service delegates calls to either BrainService or LangGraphBrainService
    based on configuration and availability of agents.
    """
    
    def __init__(
        self,
        legacy_service: Optional[BrainService] = None,
        langgraph_service: Optional[LangGraphBrainService] = None,
        db_session: Optional[AsyncSession] = None,
        config: Optional[Config] = None,
        agent_factory = None  # Can be either type of agent factory
    ):
        """
        Initialize the hybrid brain service.
        
        Args:
            legacy_service: Optional legacy brain service
            langgraph_service: Optional LangGraph brain service
            db_session: Optional database session
            config: Optional configuration
            agent_factory: Optional agent factory
        """
        self.config = config or Config()
        self.db_session = db_session
        
        # Initialize services if not provided
        self.legacy_service = legacy_service
        self.langgraph_service = langgraph_service
        
        # Store agent factory for later use
        self.agent_factory = agent_factory
        
        # Track which agents are handled by which service
        self.langgraph_agent_names = set()
        self.legacy_agent_names = set()
        
        logger.info("Initialized Hybrid Brain Service")
    
    async def initialize(self):
        """
        Initialize the brain service.
        """
        # Initialize legacy service if not provided
        if not self.legacy_service and self.db_session:
            from backend.services.brain_service import BrainService
            self.legacy_service = BrainService(
                db_session=self.db_session,
                config=self.config,
                agent_factory=self.agent_factory if not hasattr(self.agent_factory, 'get_agent_by_name') else None
            )
            
        # Initialize LangGraph service if not provided
        if not self.langgraph_service and self.db_session:
            self.langgraph_service = LangGraphBrainService(
                db_session=self.db_session,
                config=self.config,
                agent_factory=self.agent_factory if hasattr(self.agent_factory, 'get_agent_by_name') else None
            )
        
        # Initialize both services
        if self.legacy_service and hasattr(self.legacy_service, 'initialize'):
            await self.legacy_service.initialize()
            
            # Get list of legacy agents
            result = await self.legacy_service.list_agents()
            if 'agents' in result:
                self.legacy_agent_names = set(result['agents'])
                logger.info(f"Legacy agents: {self.legacy_agent_names}")
        
        if self.langgraph_service and hasattr(self.langgraph_service, 'initialize'):
            await self.langgraph_service.initialize()
            
            # Get list of LangGraph agents
            result = await self.langgraph_service.list_agents()
            if 'agents' in result:
                self.langgraph_agent_names = set(result['agents'])
                logger.info(f"LangGraph agents: {self.langgraph_agent_names}")
        
        logger.info("Hybrid Brain Service initialization complete")
    
    async def cleanup(self):
        """
        Clean up resources used by the service.
        """
        if self.legacy_service and hasattr(self.legacy_service, 'cleanup'):
            await self.legacy_service.cleanup()
            
        if self.langgraph_service and hasattr(self.langgraph_service, 'cleanup'):
            await self.langgraph_service.cleanup()
    
    async def process_request(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user request by routing to the appropriate agent service.
        
        Args:
            message: User message
            session_id: Session identifier for maintaining conversation state
            context: Additional context information
            agent_name: Optional name of agent to use
            
        Returns:
            Response with content and metadata
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Initialize context if not provided
            context = context or {}
            
            # If agent name is specified, use the appropriate service
            if agent_name:
                if agent_name in self.langgraph_agent_names:
                    return await self.langgraph_service.process_request(
                        message, session_id, context
                    )
                elif agent_name in self.legacy_agent_names:
                    return await self.legacy_service.process_request(
                        message, session_id, context
                    )
            
            # Try LangGraph service first if available
            if self.langgraph_service:
                try:
                    result = await self.langgraph_service.process_request(
                        message, session_id, context
                    )
                    
                    # If successful with reasonable confidence, return result
                    if result.get('confidence', 0) > 0.5:
                        return result
                except Exception as e:
                    logger.warning(f"LangGraph service error: {str(e)}")
            
            # Fall back to legacy service
            if self.legacy_service:
                return await self.legacy_service.process_request(
                    message, session_id, context
                )
            
            # If no service could handle the request
            return {
                "response": "I'm sorry, I couldn't process your request. No agent service is available.",
                "agent": "error_handler",
                "confidence": 0.0,
                "metadata": {
                    "session_id": session_id,
                    "error": "No agent service available"
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing request in hybrid service: {str(e)}", exc_info=True)
            return {
                "response": "I apologize, but I encountered an error while processing your request.",
                "agent": "error_handler",
                "confidence": 0.0,
                "error": str(e),
                "metadata": {
                    "session_id": session_id
                }
            }
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        Get a list of available agents from all services.
        
        Returns:
            Dictionary containing merged agent information
        """
        try:
            all_agents = []
            
            # Get agents from legacy service
            if self.legacy_service:
                try:
                    legacy_result = await self.legacy_service.list_agents()
                    if 'agents' in legacy_result:
                        if isinstance(legacy_result['agents'], list):
                            # Check if it's a list of strings or dictionaries
                            if legacy_result['agents'] and isinstance(legacy_result['agents'][0], dict):
                                for agent in legacy_result['agents']:
                                    agent['source'] = 'legacy'
                                    agent['db_driven'] = False
                                    all_agents.append(agent)
                            else:
                                # It's a list of strings
                                self.legacy_agent_names = set(legacy_result['agents'])
                                for agent_name in legacy_result['agents']:
                                    all_agents.append({
                                        'name': agent_name,
                                        'source': 'legacy',
                                        'db_driven': False
                                    })
                except Exception as e:
                    logger.error(f"Error getting legacy agents: {str(e)}", exc_info=True)
            
            # Get agents from LangGraph service
            if self.langgraph_service:
                try:
                    langgraph_result = await self.langgraph_service.list_agents()
                    if 'agents' in langgraph_result:
                        if isinstance(langgraph_result['agents'], list):
                            # Check if it's a list of strings or dictionaries
                            if langgraph_result['agents'] and isinstance(langgraph_result['agents'][0], dict):
                                for agent in langgraph_result['agents']:
                                    agent['source'] = 'langgraph'
                                    agent['db_driven'] = True
                                    all_agents.append(agent)
                            else:
                                # It's a list of strings
                                self.langgraph_agent_names = set(langgraph_result['agents'])
                                for agent_name in langgraph_result['agents']:
                                    all_agents.append({
                                        'name': agent_name,
                                        'source': 'langgraph',
                                        'db_driven': True
                                    })
                except Exception as e:
                    logger.error(f"Error getting langgraph agents: {str(e)}", exc_info=True)
            
            return {
                'agents': all_agents,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return {
                'agents': [],
                'success': False,
                'error': str(e)
            }
    
    async def register_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new agent with the appropriate service.
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            Result of registration
        """
        # Determine which service to use based on agent type
        agent_type = agent_config.get('agent_type', '').upper()
        
        if agent_type == 'LANGGRAPH' and self.langgraph_service:
            return await self.langgraph_service.register_agent(agent_config)
        elif self.legacy_service:
            return await self.legacy_service.register_agent(agent_config)
        else:
            return {
                'success': False,
                'error': f"No service available to register agent of type {agent_type}"
            }
    
    async def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system statistics from all services.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing merged statistics
        """
        all_stats = {
            'period_days': days,
        }
        
        # Get stats from legacy service
        if self.legacy_service and hasattr(self.legacy_service, 'get_system_stats'):
            try:
                legacy_stats = await self.legacy_service.get_system_stats(days)
                if legacy_stats and not 'error' in legacy_stats:
                    all_stats['legacy'] = legacy_stats
                    
                    # Copy top-level stats if not set yet
                    for key in ['total_conversations', 'agent_distribution', 'response_times', 'error_stats']:
                        if key in legacy_stats and key not in all_stats:
                            all_stats[key] = legacy_stats[key]
            except Exception as e:
                logger.error(f"Error getting legacy stats: {str(e)}", exc_info=True)
        
        # Get stats from LangGraph service
        if self.langgraph_service and hasattr(self.langgraph_service, 'get_system_stats'):
            try:
                langgraph_stats = await self.langgraph_service.get_system_stats(days)
                if langgraph_stats and not 'error' in langgraph_stats:
                    all_stats['langgraph'] = langgraph_stats
                    
                    # Merge top-level stats if already set
                    for key in ['total_conversations', 'agent_distribution', 'response_times', 'error_stats']:
                        if key in langgraph_stats:
                            if key in all_stats:
                                # Combine stats
                                if key == 'total_conversations':
                                    all_stats[key] += langgraph_stats[key]
                                elif key == 'agent_distribution':
                                    all_stats[key].update(langgraph_stats[key])
                                elif key == 'error_stats':
                                    if 'types' in all_stats[key] and 'types' in langgraph_stats[key]:
                                        all_stats[key]['types'].update(langgraph_stats[key]['types'])
                            else:
                                all_stats[key] = langgraph_stats[key]
            except Exception as e:
                logger.error(f"Error getting langgraph stats: {str(e)}", exc_info=True)
        
        return all_stats