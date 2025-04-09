import logging
from typing import Dict, Any, List
import asyncio
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates multiple agents to handle user requests.
    
    This class determines which agent is best suited to handle a specific user request
    and routes the request accordingly.
    """
    
    def __init__(self, agents: List[BaseAgent]):
        """
        Initialize the orchestrator with a list of agents.
        
        Args:
            agents: List of agent instances to orchestrate
        """
        self.agents = agents
        logger.info(f"Initialized orchestrator with {len(agents)} agents")
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
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
