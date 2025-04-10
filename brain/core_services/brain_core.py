"""
Brain Core for Staples Brain.

This module implements the core service that coordinates all other services
and provides the main interface for the application to interact with the brain.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from brain.core_services.base_service import CoreService, service_registry
from brain.core_services.intent_service import IntentService
from brain.core_services.orchestration_service import OrchestrationService
from brain.core_services.planning_service import PlanningService
from brain.core_services.integration_service import IntegrationService

# Import agent classes for factory method access
from agents.base_agent import BaseAgent
from agents.package_tracking import PackageTrackingAgent
from agents.reset_password import ResetPasswordAgent
from agents.store_locator import StoreLocatorAgent
from agents.product_info import ProductInfoAgent
from agents.returns_processing import ReturnsProcessingAgent

from utils.observability import record_error

logger = logging.getLogger(__name__)

class BrainCore(CoreService):
    """
    Core service that coordinates all other brain services.
    
    This service provides the main interface for the application to interact
    with the brain and coordinates the flow between different services.
    """
    
    def __init__(self):
        """Initialize the brain core."""
        self.intent_service = None
        self.orchestration_service = None
        self.planning_service = None
        self.integration_service = None
        self.agents = []
        self.initialized = False
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the brain core and all required services.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing Staples Brain Core")
            
            # Initialize services
            self.intent_service = IntentService()
            intent_success = self.intent_service.initialize()
            
            # Create and initialize agents
            self._initialize_agents()
            
            # Initialize orchestration service with agents
            self.orchestration_service = OrchestrationService(self.agents)
            orchestration_success = self.orchestration_service.initialize()
            
            # Initialize planning service with intent service
            self.planning_service = PlanningService(self.intent_service)
            planning_success = self.planning_service.initialize()
            
            # Initialize integration service
            self.integration_service = IntegrationService()
            integration_success = self.integration_service.initialize()
            
            # Register services in registry
            service_registry.register("intent_service", self.intent_service, {"type": "core"})
            service_registry.register("orchestration_service", self.orchestration_service, {"type": "core"})
            service_registry.register("planning_service", self.planning_service, {"type": "core"})
            service_registry.register("integration_service", self.integration_service, {"type": "core"})
            service_registry.register("brain_core", self, {"type": "core"})
            
            # Check initialization status
            initialization_status = {
                "intent_service": intent_success,
                "orchestration_service": orchestration_success,
                "planning_service": planning_success,
                "integration_service": integration_success,
                "agents": len(self.agents) > 0
            }
            
            self.initialized = all(initialization_status.values())
            
            if self.initialized:
                logger.info("Staples Brain Core initialized successfully")
                self.health_status["healthy"] = True
                self.health_status["last_check"] = datetime.now().isoformat()
                self.health_status["details"] = {
                    "services": initialization_status,
                    "agent_count": len(self.agents)
                }
            else:
                failed_services = [name for name, status in initialization_status.items() if not status]
                logger.warning(f"Staples Brain Core initialization incomplete. Failed services: {failed_services}")
                self.health_status["healthy"] = False
                self.health_status["last_check"] = datetime.now().isoformat()
                self.health_status["details"] = {
                    "error": f"Initialization incomplete. Failed services: {failed_services}",
                    "services": initialization_status
                }
            
            return self.initialized
            
        except Exception as e:
            error_message = f"Failed to initialize brain core: {str(e)}"
            logger.error(error_message)
            record_error("brain_core_init", error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def _initialize_agents(self) -> None:
        """Initialize all available agents."""
        try:
            # Initialize package tracking agent
            package_tracking_agent = PackageTrackingAgent()
            self.agents.append(package_tracking_agent)
            logger.info("Package Tracking Agent initialized")
            
            # Initialize reset password agent
            reset_password_agent = ResetPasswordAgent()
            self.agents.append(reset_password_agent)
            logger.info("Reset Password Agent initialized")
            
            # Initialize store locator agent
            store_locator_agent = StoreLocatorAgent()
            self.agents.append(store_locator_agent)
            logger.info("Store Locator Agent initialized")
            
            # Initialize product info agent
            product_info_agent = ProductInfoAgent()
            self.agents.append(product_info_agent)
            logger.info("Product Info Agent initialized")
            
            # Initialize returns processing agent
            returns_processing_agent = ReturnsProcessingAgent()
            self.agents.append(returns_processing_agent)
            logger.info("Returns Processing Agent initialized")
            
        except Exception as e:
            logger.error(f"Error initializing agents: {str(e)}")
            record_error("agent_initialization", str(e))
    
    async def process_request(self, user_input: str, session_id: str, source: Optional[str] = None, 
                            raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request through the brain services.
        
        Args:
            user_input: User input text
            session_id: Session identifier
            source: Optional source system identifier
            raw_data: Optional raw data from source system
            
        Returns:
            Response from the brain
        """
        if not self.initialized:
            logger.error("Brain core not initialized. Cannot process request.")
            return {
                "error": "Brain core not initialized",
                "response": "I'm sorry, the system is currently unavailable. Please try again later."
            }
        
        try:
            # Transform incoming data if coming from external system
            if source and raw_data and self.integration_service:
                transformed_data = self.integration_service.transform_incoming(source, raw_data)
                if "error" in transformed_data:
                    logger.error(f"Error transforming incoming data: {transformed_data['error']}")
                    return {
                        "error": transformed_data["error"],
                        "response": "I'm sorry, there was an error processing your request."
                    }
                
                # Update with transformed data
                user_input = transformed_data.get("user_input", user_input)
                session_id = transformed_data.get("session_id", session_id)
            
            # Step 1: Create execution plan using planning service
            plan = await self.planning_service.create_plan(user_input, session_id)
            
            if "error" in plan:
                logger.error(f"Error creating execution plan: {plan['error']}")
                return {
                    "error": plan["error"],
                    "response": "I'm sorry, there was an error processing your request."
                }
            
            intent = plan.get("intent", "none")
            confidence = plan.get("confidence", 0.0)
            
            # Step 2: Route to appropriate agent using orchestration service
            agent, adjusted_confidence = await self.orchestration_service.route_request(
                session_id, user_input, {"intent": intent, "confidence": confidence}
            )
            
            if not agent:
                logger.warning(f"No suitable agent found for intent: {intent}")
                return {
                    "error": "No suitable agent found",
                    "response": "I'm sorry, I don't understand your request. Could you please rephrase or provide more details?"
                }
            
            # Step 3: Process request with selected agent
            context = {"plan": plan, "confidence": adjusted_confidence}
            response = await self.orchestration_service.process_with_agent(
                agent, session_id, user_input, context
            )
            
            # Step 4: Transform outgoing data if needed
            if source and self.integration_service:
                transformed_response = self.integration_service.transform_outgoing(source, response)
                if "error" in transformed_response and "error" not in response:
                    logger.error(f"Error transforming outgoing data: {transformed_response['error']}")
                    # Keep original response, just log the transformation error
                else:
                    response = transformed_response
            
            return response
            
        except Exception as e:
            error_message = f"Error processing request: {str(e)}"
            logger.error(error_message)
            record_error("request_processing", error_message)
            
            return {
                "error": str(e),
                "response": "I'm sorry, an unexpected error occurred while processing your request."
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "brain_core",
            "description": "Main coordination service for Staples Brain",
            "version": "1.0.0",
            "initialized": self.initialized,
            "services": {
                "intent_service": self.intent_service is not None,
                "orchestration_service": self.orchestration_service is not None,
                "planning_service": self.planning_service is not None,
                "integration_service": self.integration_service is not None
            },
            "agent_count": len(self.agents),
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
            
            # Check initialization status
            if not self.initialized:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "Brain core not initialized"}
                return self.health_status
            
            # Check service health
            service_health = {}
            
            if self.intent_service:
                service_health["intent_service"] = self.intent_service.health_check()
            else:
                service_health["intent_service"] = {"healthy": False, "error": "Not initialized"}
            
            if self.orchestration_service:
                service_health["orchestration_service"] = self.orchestration_service.health_check()
            else:
                service_health["orchestration_service"] = {"healthy": False, "error": "Not initialized"}
            
            if self.planning_service:
                service_health["planning_service"] = self.planning_service.health_check()
            else:
                service_health["planning_service"] = {"healthy": False, "error": "Not initialized"}
            
            if self.integration_service:
                service_health["integration_service"] = self.integration_service.health_check()
            else:
                service_health["integration_service"] = {"healthy": False, "error": "Not initialized"}
            
            # Check overall health
            all_healthy = all(service.get("healthy", False) for service in service_health.values())
            
            self.health_status["healthy"] = all_healthy
            self.health_status["details"] = {
                "services": service_health,
                "agent_count": len(self.agents)
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status


# Create a singleton instance
brain_core = BrainCore()