import logging
from typing import Dict, Any, List, Optional
import json
from brain.intent_handler import IntentHandler

logger = logging.getLogger(__name__)

class ExecutionPlanner:
    """
    Plans and coordinates the execution of user requests.
    
    This class serves as a bridge between intent recognition and agent execution,
    creating structured plans based on user intents and managing their execution.
    """
    
    def __init__(self, intent_handler: IntentHandler):
        """
        Initialize the execution planner.
        
        Args:
            intent_handler: An instance of IntentHandler
        """
        self.intent_handler = intent_handler
        logger.info("Execution planner initialized")
        
    async def create_plan(self, user_input: str) -> Dict[str, Any]:
        """
        Create an execution plan for a user input.
        
        Args:
            user_input: The user's request or query
            
        Returns:
            Dict containing the execution plan
        """
        try:
            # Step 1: Identify intent
            intent_result = await self.intent_handler.identify_intent(user_input)
            intent = intent_result.get("intent")
            confidence = intent_result.get("confidence", 0.0)
            
            # If confidence is too low, return unknown
            if confidence < 0.3:
                logger.warning(f"Low confidence intent ({confidence}): {intent}")
                return {
                    "agent": "Unknown",
                    "intent": "unknown",
                    "confidence": confidence,
                    "plan": None,
                    "entities": None,
                    "success": False,
                    "message": "Could not confidently determine user intent"
                }
            
            # Step 2: Extract entities
            entities = await self.intent_handler.extract_entities(user_input, intent)
            
            # Step 3: Create execution plan
            plan = await self.intent_handler.create_execution_plan(user_input, intent, entities)
            
            # Return complete planning information
            return {
                "agent": plan.get("agent"),
                "intent": intent,
                "confidence": confidence,
                "plan": plan,
                "entities": entities,
                "success": True,
                "message": f"Successfully created plan for {intent} intent"
            }
            
        except Exception as e:
            logger.error(f"Error creating execution plan: {str(e)}", exc_info=True)
            return {
                "agent": "Unknown",
                "intent": "unknown",
                "confidence": 0.0,
                "plan": None,
                "entities": None,
                "success": False,
                "message": f"Error creating plan: {str(e)}"
            }
            
    def get_agent_for_plan(self, plan: Dict[str, Any]) -> Optional[str]:
        """
        Get the agent name from an execution plan.
        
        Args:
            plan: The execution plan
            
        Returns:
            The agent name or None if not found
        """
        return plan.get("agent") if plan and "agent" in plan else None
        
    def get_context_for_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a context dictionary from an execution plan.
        
        Args:
            plan: The execution plan
            
        Returns:
            Context dictionary for agent
        """
        if not plan or not plan.get("success", False):
            return {}
            
        context = {
            "intent": plan.get("intent"),
            "confidence": plan.get("confidence"),
            "entities": plan.get("entities", {})
        }
        
        # Add agent name if available
        if plan.get("agent"):
            context["agent_name"] = plan.get("agent")
            
        return context