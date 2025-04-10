"""
Integration service for Staples Brain.

This service handles the integration with external systems like Kore.ai, 
Salesforce, Slack, and other communication channels. It provides adapters
for transforming data between the brain and external systems.
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

from brain.core_services.base_service import CoreService
from utils.observability import record_error

logger = logging.getLogger(__name__)

class IntegrationAdapter(ABC):
    """Base interface for integration adapters."""
    
    @abstractmethod
    def transform_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform incoming data from external system to brain format.
        
        Args:
            data: Data from external system
            
        Returns:
            Transformed data in brain format
        """
        pass
    
    @abstractmethod
    def transform_outgoing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform outgoing data from brain to external system format.
        
        Args:
            data: Data from brain
            
        Returns:
            Transformed data in external system format
        """
        pass


class KoreAdapter(IntegrationAdapter):
    """Adapter for Kore.ai integration."""
    
    def transform_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform incoming data from Kore.ai to brain format.
        
        Args:
            data: Data from Kore.ai
            
        Returns:
            Transformed data in brain format
        """
        try:
            # Extract relevant fields from Kore.ai format
            user_input = data.get("message", {}).get("text", "")
            session_id = data.get("session", {}).get("id", "")
            user_id = data.get("user", {}).get("id", "")
            
            return {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": user_id,
                "source": "kore",
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Error transforming incoming Kore.ai data: {str(e)}")
            return {"error": str(e), "source": "kore", "raw_data": data}
    
    def transform_outgoing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform outgoing data from brain to Kore.ai format.
        
        Args:
            data: Data from brain
            
        Returns:
            Transformed data in Kore.ai format
        """
        try:
            response_text = data.get("response", "")
            session_id = data.get("session_id", "")
            
            # Construct Kore.ai response format
            kore_response = {
                "message": {
                    "text": response_text
                },
                "session": {
                    "id": session_id
                }
            }
            
            # Handle rich responses if present
            if "cards" in data:
                kore_response["message"]["cards"] = data["cards"]
            
            # Handle actions if present
            if "actions" in data:
                kore_response["message"]["actions"] = data["actions"]
            
            return kore_response
        except Exception as e:
            logger.error(f"Error transforming outgoing data for Kore.ai: {str(e)}")
            return {
                "message": {
                    "text": "Sorry, there was an error processing your request."
                }
            }


class SlackAdapter(IntegrationAdapter):
    """Adapter for Slack integration."""
    
    def transform_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform incoming data from Slack to brain format.
        
        Args:
            data: Data from Slack
            
        Returns:
            Transformed data in brain format
        """
        try:
            # Extract relevant fields from Slack format
            user_input = data.get("event", {}).get("text", "")
            session_id = data.get("event", {}).get("channel", "")
            user_id = data.get("event", {}).get("user", "")
            
            return {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": user_id,
                "source": "slack",
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Error transforming incoming Slack data: {str(e)}")
            return {"error": str(e), "source": "slack", "raw_data": data}
    
    def transform_outgoing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform outgoing data from brain to Slack format.
        
        Args:
            data: Data from brain
            
        Returns:
            Transformed data in Slack format
        """
        try:
            response_text = data.get("response", "")
            session_id = data.get("session_id", "")
            
            # Construct Slack response format
            slack_response = {
                "channel": session_id,
                "text": response_text
            }
            
            # Handle rich responses if present
            if "blocks" in data:
                slack_response["blocks"] = data["blocks"]
            
            return slack_response
        except Exception as e:
            logger.error(f"Error transforming outgoing data for Slack: {str(e)}")
            return {
                "channel": data.get("session_id", ""),
                "text": "Sorry, there was an error processing your request."
            }


class SalesforceAdapter(IntegrationAdapter):
    """Adapter for Salesforce integration."""
    
    def transform_incoming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform incoming data from Salesforce to brain format.
        
        Args:
            data: Data from Salesforce
            
        Returns:
            Transformed data in brain format
        """
        try:
            # Extract relevant fields from Salesforce format
            user_input = data.get("message", {}).get("content", "")
            session_id = data.get("conversationId", "")
            user_id = data.get("senderId", "")
            
            return {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": user_id,
                "source": "salesforce",
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Error transforming incoming Salesforce data: {str(e)}")
            return {"error": str(e), "source": "salesforce", "raw_data": data}
    
    def transform_outgoing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform outgoing data from brain to Salesforce format.
        
        Args:
            data: Data from brain
            
        Returns:
            Transformed data in Salesforce format
        """
        try:
            response_text = data.get("response", "")
            session_id = data.get("session_id", "")
            
            # Construct Salesforce response format
            sf_response = {
                "conversationId": session_id,
                "message": {
                    "content": response_text,
                    "type": "text"
                }
            }
            
            # Handle rich responses if present
            if "attachments" in data:
                sf_response["message"]["attachments"] = data["attachments"]
            
            return sf_response
        except Exception as e:
            logger.error(f"Error transforming outgoing data for Salesforce: {str(e)}")
            return {
                "conversationId": data.get("session_id", ""),
                "message": {
                    "content": "Sorry, there was an error processing your request.",
                    "type": "text"
                }
            }


class IntegrationService(CoreService):
    """
    Service for handling integrations with external systems.
    
    This service provides a unified interface for integrating with external
    systems, managing the transformation of data between formats.
    """
    
    def __init__(self):
        """Initialize the integration service."""
        self.adapters = {}
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the integration service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Register built-in adapters
            self.register_adapter("kore", KoreAdapter())
            self.register_adapter("slack", SlackAdapter())
            self.register_adapter("salesforce", SalesforceAdapter())
            
            logger.info(f"Integration service initialized with {len(self.adapters)} adapters")
            
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {
                "adapters": list(self.adapters.keys())
            }
            
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize integration service: {str(e)}"
            logger.error(error_message)
            record_error("integration_service_init", error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def register_adapter(self, source: str, adapter: IntegrationAdapter) -> None:
        """
        Register an integration adapter.
        
        Args:
            source: Source system identifier
            adapter: Adapter instance
        """
        self.adapters[source] = adapter
        logger.info(f"Registered adapter for source: {source}")
    
    def transform_incoming(self, source: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform incoming data from an external system.
        
        Args:
            source: Source system identifier
            data: Data from external system
            
        Returns:
            Transformed data in brain format
        """
        if source not in self.adapters:
            error_message = f"No adapter registered for source: {source}"
            logger.error(error_message)
            return {"error": error_message, "source": source}
        
        try:
            return self.adapters[source].transform_incoming(data)
        except Exception as e:
            error_message = f"Error transforming incoming data from {source}: {str(e)}"
            logger.error(error_message)
            record_error("integration_transform_incoming", error_message)
            return {"error": str(e), "source": source}
    
    def transform_outgoing(self, source: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform outgoing data to an external system format.
        
        Args:
            source: Target system identifier
            data: Data from brain
            
        Returns:
            Transformed data in external system format
        """
        if source not in self.adapters:
            error_message = f"No adapter registered for source: {source}"
            logger.error(error_message)
            return {"error": error_message}
        
        try:
            return self.adapters[source].transform_outgoing(data)
        except Exception as e:
            error_message = f"Error transforming outgoing data for {source}: {str(e)}"
            logger.error(error_message)
            record_error("integration_transform_outgoing", error_message)
            return {
                "error": str(e),
                "message": "Sorry, there was an error processing your request."
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "integration_service",
            "description": "External system integration service",
            "version": "1.0.0",
            "registered_adapters": list(self.adapters.keys()),
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
            
            # Check if adapters are registered
            if not self.adapters:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "No adapters registered"}
                return self.health_status
            
            self.health_status["healthy"] = True
            self.health_status["details"] = {
                "adapter_count": len(self.adapters),
                "adapters": list(self.adapters.keys())
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status