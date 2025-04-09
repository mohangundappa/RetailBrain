import logging
import time
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
        start_time = time.time()
        
        try:
            # Step 1: Identify intent
            intent_start = time.time()
            intent_result = await self.intent_handler.identify_intent(user_input)
            intent_time = time.time() - intent_start
            
            intent = intent_result.get("intent")
            confidence = intent_result.get("confidence", 0.0)
            
            logger.info(f"Intent identification took {intent_time:.2f}s: {intent} ({confidence:.2f})")
            
            # Log intent metrics to Databricks if enabled
            try:
                from utils.databricks_utils import log_intent_metrics
                log_intent_metrics(
                    intent=intent or "unknown",
                    confidence=confidence,
                    execution_time=intent_time,
                    additional_metrics={"user_input_length": len(user_input)}
                )
            except Exception as e:
                logger.warning(f"Failed to log intent metrics to Databricks: {str(e)}")
            
            # If confidence is too low, return unknown
            if confidence < 0.3:
                logger.warning(f"Low confidence intent ({confidence}): {intent}")
                result = {
                    "agent": "Unknown",
                    "intent": "unknown",
                    "confidence": confidence,
                    "plan": None,
                    "entities": None,
                    "success": False,
                    "message": "Could not confidently determine user intent",
                    "timing": {
                        "intent": intent_time,
                        "total": time.time() - start_time
                    }
                }
                
                # Log to LangSmith
                try:
                    from utils.langsmith_utils import track_llm_call
                    track_llm_call(
                        model="intent-classifier",
                        prompt=user_input,
                        response="low_confidence",
                        metadata={
                            "intent": intent,
                            "confidence": confidence,
                            "success": False,
                            "execution_time": intent_time
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to track LLM call in LangSmith: {str(e)}")
                
                return result
            
            # Step 2: Extract entities
            entity_start = time.time()
            entities = await self.intent_handler.extract_entities(user_input, intent)
            entity_time = time.time() - entity_start
            
            # Step 3: Create execution plan
            plan_start = time.time()
            plan = await self.intent_handler.create_execution_plan(user_input, intent, entities)
            plan_time = time.time() - plan_start
            
            total_time = time.time() - start_time
            
            # Log planning metrics to Databricks
            try:
                from utils.databricks_utils import log_to_databricks
                
                @log_to_databricks(
                    metrics={
                        "intent_time": intent_time,
                        "entity_extraction_time": entity_time,
                        "plan_creation_time": plan_time,
                        "total_planning_time": total_time,
                        "confidence": confidence
                    },
                    params={
                        "intent": intent,
                        "agent": plan.get("agent", "unknown")
                    },
                    tags={
                        "user_input_length": str(len(user_input)),
                        "entity_count": str(len(entities) if entities else 0)
                    }
                )
                def log_planning_metrics():
                    return "Planning metrics logged"
                
                log_planning_metrics()
            except Exception as e:
                logger.warning(f"Failed to log planning metrics to Databricks: {str(e)}")
            
            # Log to LangSmith
            try:
                from utils.langsmith_utils import track_agent_execution
                track_agent_execution(
                    agent_name="Execution Planner",
                    inputs={"user_input": user_input},
                    outputs={
                        "intent": intent,
                        "confidence": str(confidence),
                        "agent": plan.get("agent"),
                        "entities": str(entities)
                    },
                    metadata={
                        "intent_time": intent_time,
                        "entity_time": entity_time,
                        "plan_time": plan_time,
                        "total_time": total_time,
                        "success": True
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to track planning execution in LangSmith: {str(e)}")
            
            # Return complete planning information
            return {
                "agent": plan.get("agent"),
                "intent": intent,
                "confidence": confidence,
                "plan": plan,
                "entities": entities,
                "success": True,
                "message": f"Successfully created plan for {intent} intent",
                "timing": {
                    "intent": intent_time,
                    "entities": entity_time,
                    "plan": plan_time,
                    "total": total_time
                }
            }
            
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"Error creating execution plan: {str(e)}", exc_info=True)
            
            # Log error to Databricks
            try:
                from utils.databricks_utils import log_to_databricks
                
                @log_to_databricks(
                    metrics={
                        "execution_time": error_time,
                        "success": 0.0
                    },
                    params={
                        "error_type": type(e).__name__,
                        "function": "create_plan"
                    },
                    tags={
                        "error": str(e),
                        "user_input_length": str(len(user_input))
                    }
                )
                def log_error_metrics():
                    return "Error metrics logged"
                
                log_error_metrics()
            except Exception as log_error:
                logger.warning(f"Failed to log error to Databricks: {str(log_error)}")
            
            # Log error to LangSmith
            try:
                from utils.langsmith_utils import track_agent_execution
                track_agent_execution(
                    agent_name="Execution Planner",
                    inputs={"user_input": user_input},
                    outputs={"error": str(e)},
                    metadata={
                        "error_type": type(e).__name__,
                        "execution_time": error_time,
                        "success": False
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to track error in LangSmith: {str(log_error)}")
            
            return {
                "agent": "Unknown",
                "intent": "unknown",
                "confidence": 0.0,
                "plan": None,
                "entities": None,
                "success": False,
                "message": f"Error creating plan: {str(e)}",
                "timing": {
                    "error": error_time,
                    "total": error_time
                }
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