import logging
import json
import os
from typing import Dict, Any, Optional, List
import requests
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from agents.base_agent import BaseAgent
from config import PACKAGE_TRACKING_ENDPOINT

logger = logging.getLogger(__name__)

class PackageTrackingAgent(BaseAgent):
    """
    Agent responsible for tracking packages.
    
    This agent can handle queries about package status, estimated delivery date,
    and other shipping-related inquiries.
    """
    
    def __init__(self, llm):
        """
        Initialize the Package Tracking Agent.
        
        Args:
            llm: The language model to use for this agent
        """
        super().__init__(
            name="Package Tracking Agent",
            description="I can help track your packages and provide shipping information.",
            llm=llm
        )
        
        # Create specialized chains
        self.classifier_chain = self._create_classifier_chain()
        self.tracking_chain = self._create_tracking_chain()
        self.formatting_chain = self._create_formatting_chain()
    
    def _create_classifier_chain(self) -> LLMChain:
        """
        Create a chain to classify if an input is related to package tracking.
        
        Returns:
            An LLMChain that can classify inputs
        """
        template = """
        You are an AI assistant that determines if a user's query is related to package tracking.
        
        User Query: {user_input}
        
        Is this query related to tracking a package, checking delivery status, or inquiring about shipment? 
        Please answer with a confidence score between 0 and 1, where:
        - 0 means definitely not related to package tracking
        - 1 means definitely related to package tracking
        
        Output only the confidence score as a float between 0 and 1.
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_tracking_chain(self) -> LLMChain:
        """
        Create a chain to extract tracking information from user input.
        
        Returns:
            An LLMChain that can extract tracking details
        """
        template = """
        You are an AI assistant that extracts package tracking information from user queries.
        
        User Query: {user_input}
        
        Extract the following information if present:
        1. Tracking number
        2. Order number
        3. Shipping carrier (e.g., UPS, FedEx, USPS)
        4. Time frame mentioned
        
        Return your answer as a JSON object with these fields. If information is not available, use null.
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_formatting_chain(self) -> LLMChain:
        """
        Create a chain to format the tracking information into a user-friendly response.
        
        Returns:
            An LLMChain that can format responses
        """
        template = """
        You are an AI assistant that provides helpful package tracking information.
        
        Tracking Information:
        {tracking_info}
        
        Package Status:
        {package_status}
        
        User Query:
        {user_input}
        
        Based on this information, provide a helpful, conversational response to the user.
        Make sure to include the most important details about their package.
        If there are any issues or the status is unclear, acknowledge that and offer alternative help.
        """
        
        return self._create_chain(template, ["tracking_info", "package_status", "user_input"])
    
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query related to package tracking.
        
        Args:
            user_input: The user's question about package tracking
            context: Additional context information
            
        Returns:
            A dictionary containing the agent's response
        """
        logger.debug(f"Processing package tracking request: {user_input}")
        
        try:
            # Extract tracking information from user input
            tracking_result = await self.tracking_chain.arun(user_input=user_input)
            tracking_info = json.loads(tracking_result)
            
            # Get package status from external API
            package_status = self._get_package_status(tracking_info, context)
            
            # Format the response
            formatted_response = await self.formatting_chain.arun(
                tracking_info=json.dumps(tracking_info, indent=2),
                package_status=json.dumps(package_status, indent=2),
                user_input=user_input
            )
            
            # Create response object
            response = {
                "agent": self.name,
                "response": formatted_response,
                "tracking_info": tracking_info,
                "package_status": package_status,
                "success": True
            }
            
            # Add to memory
            self.add_to_memory({
                "user_input": user_input,
                "tracking_info": tracking_info,
                "response": formatted_response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing package tracking request: {str(e)}", exc_info=True)
            return {
                "agent": self.name,
                "response": f"I'm sorry, I encountered an error while trying to track your package: {str(e)}. Please try again or provide more details about your package.",
                "success": False,
                "error": str(e)
            }
    
    def can_handle(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given user input.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A confidence score between 0 and 1
        """
        try:
            # Use the classifier chain to determine confidence
            confidence_str = self.classifier_chain.run(user_input=user_input).strip()
            confidence = float(confidence_str)
            logger.debug(f"Package tracking confidence: {confidence} for input: {user_input}")
            return min(max(confidence, 0.0), 1.0)  # Ensure confidence is between 0 and 1
        except Exception as e:
            logger.error(f"Error determining confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def _get_package_status(self, tracking_info: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the status of a package from an external API.
        
        Args:
            tracking_info: Extracted tracking information
            context: Additional context information
            
        Returns:
            Package status information
        """
        try:
            tracking_number = tracking_info.get("tracking_number")
            
            if not tracking_number:
                return {
                    "status": "unknown",
                    "message": "No tracking number provided",
                    "estimated_delivery": None
                }
            
            # In a real implementation, this would call an actual tracking API
            # For this example, we're simulating a response
            headers = {"Content-Type": "application/json"}
            api_key = os.environ.get("TRACKING_API_KEY")
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "tracking_number": tracking_number,
                "carrier": tracking_info.get("shipping_carrier")
            }
            
            # Make API request to package tracking service
            try:
                response = requests.post(
                    PACKAGE_TRACKING_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"Could not connect to tracking API: {str(e)}")
                # Fallback to simulated response
                return self._simulate_package_status(tracking_number)
                
        except Exception as e:
            logger.error(f"Error getting package status: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error retrieving package status: {str(e)}",
                "estimated_delivery": None
            }
    
    def _simulate_package_status(self, tracking_number: str) -> Dict[str, Any]:
        """
        Simulate a package status response for demonstration purposes.
        
        Args:
            tracking_number: The tracking number to simulate
            
        Returns:
            A simulated package status
        """
        import random
        from datetime import datetime, timedelta
        
        # Generate a consistent but random status based on the tracking number
        # This ensures the same tracking number gets the same status
        random.seed(tracking_number)
        
        statuses = ["in_transit", "delivered", "out_for_delivery", "processing"]
        status = random.choice(statuses)
        
        # Generate a delivery date (1-5 days from now)
        delivery_days = random.randint(1, 5)
        delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
        
        locations = ["Chicago, IL", "New York, NY", "Los Angeles, CA", "Dallas, TX", "Atlanta, GA"]
        current_location = random.choice(locations)
        
        logger.warning(f"Using simulated package status for tracking number: {tracking_number}")
        
        return {
            "tracking_number": tracking_number,
            "status": status,
            "estimated_delivery": delivery_date if status != "delivered" else None,
            "delivery_date": delivery_date if status == "delivered" else None,
            "current_location": current_location if status != "delivered" else None,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Package is currently {status.replace('_', ' ')}",
            "is_simulated": True
        }
