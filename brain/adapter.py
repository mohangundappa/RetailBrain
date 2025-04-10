"""
Adapter module for Staples Brain.

This module provides adapters for transitioning between the original architecture
and the new core services architecture. It helps maintain backward compatibility
while allowing gradual migration to the new architecture.
"""
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from brain.staples_brain import StaplesBrain as OriginalStaplesBrain
from brain.staples_brain_v2 import StaplesBrain as NewStaplesBrain

logger = logging.getLogger(__name__)

class StaplesBrainAdapter:
    """
    Adapter class that provides a unified interface for both brain versions.
    
    This adapter helps maintain backward compatibility for code that uses the
    original StaplesBrain while allowing gradual migration to the new architecture.
    """
    
    def __init__(self, use_new_architecture: bool = False):
        """
        Initialize the adapter with either the original or new brain.
        
        Args:
            use_new_architecture: Whether to use the new core services architecture
        """
        self.use_new_architecture = use_new_architecture
        
        # Initialize the appropriate brain based on configuration
        if use_new_architecture:
            logger.info("Using new core services architecture")
            from brain.staples_brain_v2 import staples_brain
            self.brain = staples_brain
        else:
            logger.info("Using original architecture")
            from brain.staples_brain import staples_brain
            self.brain = staples_brain
    
    async def process_request(self, user_input: str, session_id: Optional[str] = None, 
                            context: Optional[Dict[str, Any]] = None, 
                            source: Optional[str] = None, 
                            raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request through the brain.
        
        Args:
            user_input: User input text
            session_id: Optional session identifier (will generate if None)
            context: Optional context data (for original architecture)
            source: Optional source system identifier
            raw_data: Optional raw data from source system
            
        Returns:
            Response from the brain
        """
        try:
            # Handle the request differently based on architecture
            if self.use_new_architecture:
                # For new architecture
                return await self.brain.process_request(user_input, session_id, source, raw_data)
            else:
                # For original architecture
                # Note: The original architecture doesn't have source/raw_data params
                # so we need to adapt them into context if provided
                if source or raw_data:
                    context = context or {}
                    if source:
                        context["source"] = source
                    if raw_data:
                        context["raw_data"] = raw_data
                
                return await self.brain.process_request(user_input, session_id, context)
                
        except Exception as e:
            logger.error(f"Error in adapter processing request: {str(e)}")
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
        try:
            if self.use_new_architecture:
                # For new architecture
                return self.brain.get_health_status()
            else:
                # For original architecture (less comprehensive)
                return {
                    "healthy": True,  # Simplified assumption
                    "status": "ok",
                    "architecture": "original",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in adapter getting health status: {str(e)}")
            return {
                "healthy": False,
                "status": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# Create a configurable adapter instance
# Read from environment variable to determine which architecture to use
USE_NEW_ARCHITECTURE = os.environ.get("USE_NEW_ARCHITECTURE", "false").lower() in ("true", "1", "yes")
staples_brain_adapter = StaplesBrainAdapter(use_new_architecture=USE_NEW_ARCHITECTURE)