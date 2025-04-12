"""
Optimized Brain Service for Staples Brain.
This service uses the optimized agent selection components for improved performance.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.optimized.factory import OptimizedAgentFactory
from backend.brain.optimized.router import OptimizedAgentRouter
from backend.brain.optimized.agent_definition import AgentDefinition
from backend.config.config import Config

logger = logging.getLogger(__name__)


class OptimizedBrainService:
    """
    Brain service using optimized agent selection.
    
    This service provides:
    1. Efficient agent selection with minimal embedding API calls
    2. Integration with existing agent execution
    3. Support for conversation memory and context
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        config: Optional[Config] = None,
        memory_service: Optional[Any] = None
    ):
        """
        Initialize the optimized brain service.
        
        Args:
            db_session: Database session
            config: Application configuration
            memory_service: Optional memory service
        """
        self.db_session = db_session
        self.config = config or Config()
        self.memory_service = memory_service
        
        # Components initialized later
        self.agent_factory: Optional[OptimizedAgentFactory] = None
        self.router: Optional[OptimizedAgentRouter] = None
        
        # Traditional agent service for execution (loaded on demand)
        self._traditional_service = None
        
        logger.info("Initialized OptimizedBrainService")
        
    async def initialize(self) -> bool:
        """
        Initialize the service components.
        
        Returns:
            True if initialization was successful
        """
        try:
            # Create agent factory
            self.agent_factory = OptimizedAgentFactory(self.db_session)
            
            # Create components (router, etc.)
            self.router = await self.agent_factory.create_components(
                memory_service=self.memory_service
            )
            
            # Load agents from database
            await self.agent_factory.load_agents_from_database()
            
            logger.info("Optimized brain service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing optimized brain service: {str(e)}")
            return False
            
    async def _get_traditional_service(self) -> Any:
        """
        Get or create the traditional brain service for agent execution.
        
        Returns:
            Traditional brain service
        """
        if self._traditional_service is None:
            # Import here to avoid circular imports
            from backend.services.graph_brain_service import GraphBrainService
            self._traditional_service = GraphBrainService(
                db_session=self.db_session,
                config=self.config
            )
            # Initialize the service if needed
            if hasattr(self._traditional_service, 'initialize'):
                await self._traditional_service.initialize()
                
        return self._traditional_service
            
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message using optimized agent selection.
        
        Args:
            message: User message
            session_id: Session ID
            context: Optional context
            
        Returns:
            Response dictionary
        """
        if not message:
            return {
                "success": False,
                "error": "Empty message",
                "response": "I couldn't understand your message. Please try again."
            }
            
        if not self.router:
            success = await self.initialize()
            if not success:
                return {
                    "success": False,
                    "error": "Initialization failed",
                    "response": "I'm having trouble processing your request. Please try again later."
                }
                
        try:
            # Use optimized router to select agent
            start_time = __import__('time').time()
            agent, confidence, route_context = await self.router.route_and_prepare(
                message, session_id, context
            )
            selection_time = __import__('time').time() - start_time
            
            logger.info(f"Agent selection took {selection_time:.2f}s")
            logger.info(f"Selected agent: {agent.name if agent else 'None'} with confidence {confidence:.2f}")
            
            if not agent or confidence < 0.5:
                return {
                    "success": False,
                    "error": "No suitable agent found",
                    "response": "I'm not sure how to help with that. Could you please rephrase your question?"
                }
                
            # Pass to traditional service for execution
            # This maintains compatibility with existing agent execution
            traditional_service = await self._get_traditional_service()
            
            # We need to map our agent to the traditional agent
            # Use the agent_id since that should match between systems
            execution_result = await traditional_service.execute_agent(
                agent_id=agent.id,
                message=message,
                session_id=session_id,
                context=route_context
            )
            
            # Enhance the result with our selection info
            execution_result["selection_time"] = selection_time
            execution_result["optimized_selection"] = True
            execution_result["selection_confidence"] = confidence
            
            # Update memory if available
            if self.memory_service:
                await self._update_memory(session_id, message, agent, execution_result)
                
            return execution_result
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error processing your request. Please try again."
            }
            
    async def _update_memory(
        self,
        session_id: str,
        message: str,
        agent: AgentDefinition,
        result: Dict[str, Any]
    ) -> None:
        """
        Update conversation memory.
        
        Args:
            session_id: Session ID
            message: User message
            agent: Selected agent
            result: Execution result
        """
        if not self.memory_service:
            return
            
        try:
            # Store information about this interaction
            await self.memory_service.update_conversation(
                session_id=session_id,
                updates={
                    "last_message": message,
                    "last_agent_id": agent.id,
                    "last_agent_name": agent.name,
                    "current_topic": message,
                    "last_response": result.get("response", ""),
                    "last_entities": result.get("entities", {})
                }
            )
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            
    async def execute_agent(
        self,
        agent_id: str,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific agent directly.
        
        Args:
            agent_id: Agent ID to execute
            message: User message
            session_id: Session ID
            context: Optional context
            
        Returns:
            Response dictionary
        """
        if not self.agent_factory:
            success = await self.initialize()
            if not success:
                return {
                    "success": False,
                    "error": "Initialization failed",
                    "response": "I'm having trouble processing your request. Please try again later."
                }
                
        # Get agent from optimized store
        agent = await self.agent_factory.get_agent_by_id(agent_id)
        if not agent:
            return {
                "success": False,
                "error": f"Agent not found: {agent_id}",
                "response": "I couldn't find the agent you requested. Please try again."
            }
            
        # Extract entities if we have entity definitions
        entities = {}
        if agent.entity_definitions and message:
            entities = await self.router._extract_entities(message, agent)
            
        # Make sure context is initialized
        context = context or {}
        context["extracted_entities"] = entities
        context["session_id"] = session_id
        
        # Pass to traditional service for execution
        traditional_service = await self._get_traditional_service()
        return await traditional_service.execute_agent(
            agent_id=agent_id,
            message=message,
            session_id=session_id,
            context=context
        )