import logging
from typing import Dict, Any, List, Optional
import asyncio
from agents.base_agent import BaseAgent
from utils.memory import ConversationMemory

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates multiple agents to handle user requests.
    
    This class determines which agent is best suited to handle a specific user request
    and routes the request accordingly. It maintains conversation memory and context
    between agent interactions.
    """
    
    def __init__(self, agents: List[BaseAgent]):
        """
        Initialize the orchestrator with a list of agents.
        
        Args:
            agents: List of agent instances to orchestrate
        """
        self.agents = agents
        self.memories = {}  # Dictionary of session_id -> ConversationMemory
        logger.info(f"Initialized orchestrator with {len(agents)} agents")
    
    def _get_memory(self, session_id: str) -> ConversationMemory:
        """
        Get or create a conversation memory for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The conversation memory instance
        """
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory(session_id)
        return self.memories[session_id]
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request by selecting the most appropriate agent.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            Response from the most appropriate agent
        """
        if not context:
            context = {}
            
        logger.debug(f"Orchestrator processing request: {user_input}")
        
        try:
            # Get session ID from context, default to 'default' if not present
            session_id = context.get('session_id', 'default')
            
            # Get or create memory for this session
            memory = self._get_memory(session_id)
            
            # Add memory to context for agents to use
            context['conversation_memory'] = memory
            
            # Update working memory with user input
            memory.update_working_memory('last_user_input', user_input)
            memory.update_working_memory('timestamp', asyncio.get_event_loop().time())
            
            # Determine which agent can best handle this request
            best_agent, confidence = self._select_agent(user_input, context)
            
            if best_agent is None:
                logger.warning("No suitable agent found to handle the request")
                return {
                    "success": False,
                    "error": "No suitable agent found",
                    "response": "I'm sorry, I don't have the capability to help with that request at the moment."
                }
            
            logger.info(f"Selected agent '{best_agent.name}' with confidence {confidence:.2f}")
            
            # Process the request with the selected agent
            response = await best_agent.process(user_input, context)
            
            # Add orchestrator metadata
            response.update({
                "selected_agent": best_agent.name,
                "confidence": confidence
            })
            
            # Use memory to track last selected agent
            memory.update_working_memory('last_selected_agent', best_agent.name)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error while processing your request. Please try again or rephrase your question."
            }
    
    def _select_agent(self, user_input: str, context: Dict[str, Any] = None) -> tuple:
        """
        Select the most appropriate agent to handle a user request.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A tuple containing (best_agent, confidence_score)
        """
        if not self.agents:
            logger.warning("No agents available to select from")
            return None, 0.0
        
        best_agent = None
        best_confidence = 0.0
        
        # Check if a specific agent is requested in the context
        if context and "agent_name" in context:
            requested_agent_name = context["agent_name"].lower()
            for agent in self.agents:
                if agent.name.lower() == requested_agent_name:
                    logger.info(f"Using explicitly requested agent: {agent.name}")
                    return agent, 1.0
        
        # Check if we should continue using the same agent from a previous interaction
        if (context and 'conversation_memory' in context and 
            context['conversation_memory'].get_working_memory('continue_with_same_agent', False) and
            context['conversation_memory'].get_working_memory('last_selected_agent')):
            
            last_agent_name = context['conversation_memory'].get_working_memory('last_selected_agent')
            for agent in self.agents:
                if agent.name == last_agent_name:
                    # Check if this agent still has some confidence in handling the new input
                    confidence = agent.can_handle(user_input, context)
                    if confidence > 0.2:  # Lower threshold for continuity
                        logger.info(f"Continuing with same agent: {agent.name} (confidence: {confidence:.2f})")
                        return agent, confidence
        
        # Ask each agent how confident it is in handling this request
        for agent in self.agents:
            try:
                confidence = agent.can_handle(user_input, context)
                logger.debug(f"Agent '{agent.name}' confidence: {confidence:.2f}")
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_agent = agent
            except Exception as e:
                logger.error(f"Error getting confidence from agent '{agent.name}': {str(e)}")
        
        # Only select an agent if confidence is above a threshold
        if best_confidence < 0.3:
            logger.warning(f"Best confidence ({best_confidence:.2f}) is below threshold")
            return None, 0.0
            
        return best_agent, best_confidence
