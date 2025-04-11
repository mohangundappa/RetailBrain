"""
Brain Service for Staples Brain.
This service acts as an intermediary between the API layer and the Staples Brain core.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain_service")

class BrainService:
    """
    Service class for interacting with the Staples Brain.
    
    This class:
    1. Handles integration between the API and the brain
    2. Manages conversation state and context
    3. Provides access to agent functionality
    4. Tracks telemetry and observability data
    """
    
    def __init__(self):
        """Initialize the brain service"""
        logger.info("Initializing Brain Service")
        # Initialize the Staples Brain instance
        self._initialize_brain()
        self.initialized = True
        logger.info("Brain Service initialized")
    
    def _initialize_brain(self):
        """Initialize the Staples Brain instance"""
        try:
            # Import the brain module here to avoid circular imports
            from brain.staples_brain import StaplesBrain
            
            # Get OpenAI API key from environment
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            
            # Initialize the brain
            self.brain = StaplesBrain(openai_api_key=openai_api_key)
            logger.info("Staples Brain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Staples Brain: {e}")
            raise
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the Staples Brain
        
        Args:
            message: The user's message
            session_id: The session identifier
            context: Additional context for the request
            
        Returns:
            Processed response with data and metadata
        """
        logger.info(f"Processing message for session {session_id}")
        
        try:
            # Process the message through the brain
            response = await self.brain.process_request(
                user_input=message,
                session_id=session_id,
                context=context or {}
            )
            
            # Format the response for the API
            formatted_response = {
                "data": {
                    "message": response.get("response"),
                    "agent": response.get("selected_agent"),
                    "confidence": response.get("confidence"),
                    "suggested_actions": response.get("suggested_actions", [])
                },
                "metadata": {
                    "processing_time": response.get("processing_time"),
                    "intent": response.get("intent"),
                    "intent_confidence": response.get("intent_confidence")
                }
            }
            
            logger.info(f"Message processed successfully for session {session_id}")
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents
        
        Returns:
            List of agent information dictionaries
        """
        try:
            # For now, return static list
            # Will be replaced with actual agent information from the brain
            built_in_agents = [
                {
                    "id": "package-tracking", 
                    "name": "Package Tracking", 
                    "description": "Track your Staples orders and packages", 
                    "is_built_in": True
                },
                {
                    "id": "reset-password", 
                    "name": "Password Reset", 
                    "description": "Reset your Staples.com or account password", 
                    "is_built_in": True
                },
                {
                    "id": "store-locator", 
                    "name": "Store Locator", 
                    "description": "Find Staples stores near you", 
                    "is_built_in": True
                },
                {
                    "id": "product-info", 
                    "name": "Product Information", 
                    "description": "Get information about Staples products", 
                    "is_built_in": True
                }
            ]
            
            # In the future, get custom agents from the database
            # custom_agents = ...
            
            return built_in_agents
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise
    
    async def get_telemetry_sessions(self) -> List[Dict[str, Any]]:
        """
        Get telemetry sessions
        
        Returns:
            List of telemetry session information
        """
        try:
            # For now, return empty list
            # Will be replaced with actual telemetry data
            return []
        except Exception as e:
            logger.error(f"Error getting telemetry sessions: {e}")
            raise