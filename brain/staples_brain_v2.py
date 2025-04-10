"""
Main Staples Brain module using core services architecture.

This module provides the main entry point for external systems to interact
with the Staples AI ecosystem using the new core services architecture.
"""
import os
import logging
import asyncio
import importlib.metadata
import platform
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from brain.core_services.brain_core import brain_core
from utils.observability import record_error

logger = logging.getLogger(__name__)

class StaplesBrain:
    """
    The main Staples Brain class that orchestrates all agents and handles user requests.
    
    This class serves as the main entry point for external systems to interact with 
    the Staples AI ecosystem using the new core services architecture.
    """
    
    def __init__(self):
        """Initialize the Staples Brain with core services architecture."""
        logger.debug("Initializing Staples Brain v2")
        
        # Debug: Log version information
        try:
            openai_version = importlib.metadata.version("openai")
            langchain_openai_version = importlib.metadata.version("langchain-openai")
            python_version = platform.python_version()
            
            logger.info(f"Using OpenAI version: {openai_version}")
            logger.info(f"Using langchain-openai version: {langchain_openai_version}")
            logger.info(f"Python version: {python_version}")
        except Exception as e:
            logger.warning(f"Failed to log version information: {str(e)}")
        
        # Initialize the brain core
        self.initialized = brain_core.initialize()
        
        if self.initialized:
            logger.info("Staples Brain initialized with core services architecture")
        else:
            logger.error("Failed to initialize Staples Brain with core services architecture")
    
    async def process_request(self, user_input: str, session_id: Optional[str] = None, 
                            source: Optional[str] = None, raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request through the brain.
        
        Args:
            user_input: User input text
            session_id: Optional session identifier (will generate if None)
            source: Optional source system identifier
            raw_data: Optional raw data from source system
            
        Returns:
            Response from the brain
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"
        
        try:
            if not self.initialized:
                logger.error("Cannot process request: Staples Brain not initialized")
                return {
                    "error": "Staples Brain not initialized",
                    "response": "I'm sorry, the system is currently unavailable. Please try again later."
                }
            
            # Process the request through the brain core
            response = await brain_core.process_request(user_input, session_id, source, raw_data)
            
            return response
            
        except Exception as e:
            error_message = f"Error processing request: {str(e)}"
            logger.error(error_message)
            record_error("brain_processing", error_message)
            
            return {
                "error": str(e),
                "response": "I'm sorry, an unexpected error occurred while processing your request."
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the brain.
        
        Returns:
            Dictionary containing health status information
        """
        if not self.initialized:
            return {
                "healthy": False,
                "status": "Staples Brain not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Get health status from brain core
            core_health = brain_core.health_check()
            
            return {
                "healthy": core_health.get("healthy", False),
                "status": "ok" if core_health.get("healthy", False) else "degraded",
                "services": core_health.get("details", {}).get("services", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking health status: {str(e)}")
            
            return {
                "healthy": False,
                "status": f"Error checking health: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the brain services.
        
        Returns:
            Dictionary containing service metadata
        """
        if not self.initialized:
            return {
                "name": "staples_brain",
                "version": "2.0.0",
                "initialized": False,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Get service info from brain core
            core_info = brain_core.get_service_info()
            
            return {
                "name": "staples_brain",
                "version": "2.0.0",
                "initialized": self.initialized,
                "core_services": core_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            
            return {
                "name": "staples_brain",
                "version": "2.0.0",
                "initialized": self.initialized,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Create singleton instance
staples_brain = StaplesBrain()