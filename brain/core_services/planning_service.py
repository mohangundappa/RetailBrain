"""
Planning service for Staples Brain.

This service handles the creation of execution plans based on user intents
and coordinates their execution through the orchestration service.
"""
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from brain.core_services.base_service import CoreService
from brain.core_services.intent_service import IntentService
from utils.observability import record_error

logger = logging.getLogger(__name__)

class PlanningService(CoreService):
    """
    Service for planning and coordinating request execution.
    
    This service bridges intent recognition and agent execution,
    creating structured plans and managing their execution.
    """
    
    def __init__(self, intent_service: Optional[IntentService] = None):
        """
        Initialize the planning service.
        
        Args:
            intent_service: Optional intent service instance
        """
        self.intent_service = intent_service
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the planning service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            if not self.intent_service:
                logger.warning("Intent service not provided. Planning service will have limited functionality.")
                self.health_status["healthy"] = False
                self.health_status["details"] = {"warning": "Intent service not provided"}
                return False
            
            # Check if intent service is initialized
            if not self.intent_service.health_check().get("healthy", False):
                logger.warning("Intent service is not healthy. Planning service may have limited functionality.")
                self.health_status["healthy"] = False
                self.health_status["details"] = {"warning": "Intent service not healthy"}
                return False
            
            logger.info("Planning service initialized")
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"intent_service": "connected"}
            
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize planning service: {str(e)}"
            logger.error(error_message)
            record_error("planning_service_init", error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def set_intent_service(self, intent_service: IntentService) -> None:
        """
        Set or update the intent service.
        
        Args:
            intent_service: Intent service instance
        """
        self.intent_service = intent_service
        logger.info("Intent service updated")
    
    async def create_plan(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """
        Create an execution plan for a user input.
        
        Args:
            user_input: The user's request or query
            session_id: Session identifier
            
        Returns:
            Dict containing the execution plan
        """
        start_time = time.time()
        
        try:
            if not self.intent_service:
                return {
                    "error": "Intent service not available",
                    "intent": "none",
                    "confidence": 0.0,
                    "entities": {},
                    "timestamp": datetime.now().isoformat()
                }
            
            # Step 1: Identify intent
            intent_start = time.time()
            intent_result = await self.intent_service.identify_intent(user_input)
            intent_time = time.time() - intent_start
            
            intent = intent_result.get("intent", "none")
            confidence = intent_result.get("confidence", 0.0)
            
            logger.info(f"Intent identification took {intent_time:.2f}s: {intent} ({confidence:.2f})")
            
            # Step 2: Extract entities based on intent
            entity_start = time.time()
            entities = await self.intent_service.extract_entities(user_input, intent)
            entity_time = time.time() - entity_start
            
            logger.info(f"Entity extraction took {entity_time:.2f}s")
            
            # Step 3: Create execution plan
            plan = {
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
                "session_id": session_id,
                "user_input": user_input,
                "timestamp": datetime.now().isoformat(),
                "planning_time": time.time() - start_time
            }
            
            return plan
            
        except Exception as e:
            error_message = f"Failed to create execution plan: {str(e)}"
            logger.error(error_message)
            record_error("plan_creation", error_message)
            
            return {
                "error": str(e),
                "intent": "none",
                "confidence": 0.0,
                "entities": {},
                "timestamp": datetime.now().isoformat()
            }
    
    async def create_followup_plan(self, 
                                 user_input: str, 
                                 session_id: str, 
                                 previous_intent: str,
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a follow-up plan based on previous interaction.
        
        Args:
            user_input: The user's request or query
            session_id: Session identifier
            previous_intent: Previously identified intent
            context: Context from previous interaction
            
        Returns:
            Dict containing the execution plan
        """
        # Start with regular plan creation
        plan = await self.create_plan(user_input, session_id)
        
        # Enhance with follow-up specific logic
        plan["is_followup"] = True
        plan["previous_intent"] = previous_intent
        
        # Apply context-aware adjustments if confidence is low
        if plan.get("confidence", 0.0) < 0.5 and previous_intent != "none":
            # For follow-ups, we might want to maintain the previous intent if confidence is low
            logger.info(f"Low confidence ({plan.get('confidence', 0.0):.2f}) for follow-up; considering previous intent: {previous_intent}")
            
            # Check if entities were successfully extracted
            if plan.get("entities") and len(plan.get("entities", {})) > 0:
                # If we have entities but low intent confidence, maintain previous intent
                plan["intent"] = previous_intent
                plan["confidence"] = max(plan.get("confidence", 0.0), 0.5)  # Boost confidence for continuity
                plan["intent_adjusted"] = True
                logger.info(f"Adjusted intent to {previous_intent} for continuity")
        
        return plan
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "planning_service",
            "description": "Planning and coordination service",
            "version": "1.0.0",
            "intent_service_connected": self.intent_service is not None,
            "health_status": self.health_status
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Update health check time
            self.health_status["last_check"] = datetime.now().isoformat()
            
            # Check if intent service is available
            if not self.intent_service:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "Intent service not available"}
                return self.health_status
            
            # Check intent service health
            intent_health = self.intent_service.health_check()
            intent_healthy = intent_health.get("healthy", False)
            
            if not intent_healthy:
                self.health_status["healthy"] = False
                self.health_status["details"] = {
                    "error": "Intent service not healthy",
                    "intent_service_details": intent_health.get("details", {})
                }
                return self.health_status
            
            # All checks passed
            self.health_status["healthy"] = True
            self.health_status["details"] = {
                "intent_service": "healthy"
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status