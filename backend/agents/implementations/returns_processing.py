"""
Returns Processing Agent module for handling return and refund requests.
This agent helps customers process returns for their Staples orders.
"""
import logging
from typing import Dict, Any, Optional, List

from backend.agents.framework.base import BaseAgent
from backend.config.agent_constants import RETURNS_PROCESSING_AGENT

logger = logging.getLogger(__name__)

class ReturnsProcessingAgent(BaseAgent):
    """
    Returns Processing Agent for handling customer return requests.
    Assists customers with initiating returns, providing return status information,
    and answering questions about return policies.
    """
    
    def __init__(self, llm):
        """
        Initialize the Returns Processing Agent.
        
        Args:
            llm: The language model to use for generating responses
        """
        super().__init__(
            name=RETURNS_PROCESSING_AGENT,
            description="Process returns for Staples orders and purchases",
            llm=llm
        )
        
        # Create the returns policy template
        template = """You are the Returns Processing Agent for Staples, specializing in handling customer returns and refunds. 
Your primary responsibilities include:

1. Helping customers initiate returns for products purchased from Staples
2. Providing information about Staples' return policies
3. Explaining refund timelines and processes
4. Guiding customers on how to return items (in-store vs. shipping)
5. Offering exchange options when appropriate

Use these Staples return policy guidelines:
- Most items can be returned within 30 days of purchase with receipt
- Electronics and furniture have a 14-day return period
- Custom-made items cannot be returned
- Items must be in original packaging and unopened/unused for full refund
- Returns without receipt may receive store credit at current selling price
- Online orders can be returned via mail or in-store
- Shipping costs are non-refundable unless item was damaged or incorrect

When processing returns, collect this information (as available):
- Order number or receipt
- Purchase date
- Item details (name, quantity, price)
- Reason for return
- Customer preference for refund method (credit card, store credit, exchange)

Remain helpful, empathetic, and solution-oriented. Guide the customer through the return process step by step.

Customer message: {input}

Your response:
"""
        
        # Set up the chain using the base class method
        self.chain = self._create_chain(template, ["input"])
        
        logger.debug("Returns Processing Agent initialized")
        
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a return request from a user.
        
        Args:
            user_input: The user's request or query
            context: Additional context information (optional)
            
        Returns:
            A dictionary containing the response and any extracted return information
        """
        if context is None:
            context = {}
            
        # Extract any return-related information from the input
        extracted_info = self._extract_return_info(user_input)
        
        # Process the request through the LLM chain
        response = await self.chain.ainvoke({"input": user_input})
        
        # Format the response for the caller
        result = {
            "response": response,
            "return_info": extracted_info
        }
        
        return result
        
    def can_handle(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given user input.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A confidence score between 0 and 1 indicating how well this agent can handle the input
        """
        # Define return-related keywords and phrases to match
        return_keywords = [
            "return", "refund", "exchange", "send back", "money back", 
            "broken item", "damaged", "defective", "wrong item", 
            "incorrect order", "return policy", "return window"
        ]
        
        # Simple matching based on keywords
        user_input_lower = user_input.lower()
        
        # Check if any of the keywords are present in the user input
        for keyword in return_keywords:
            if keyword in user_input_lower:
                # Different confidence levels based on context
                if "staples" in user_input_lower and "return" in user_input_lower:
                    return 0.9  # High confidence for direct mentions of Staples returns
                return 0.7  # Medium-high confidence for general return keywords
        
        # Lower confidence if only indirectly related to returns
        if any(word in user_input_lower for word in ["policy", "days", "receipt", "store credit"]):
            return 0.4
            
        # Default to low confidence
        return 0.1
    
    def _extract_return_info(self, user_input: str) -> Dict[str, Any]:
        """
        Extract return-related information from user input.
        
        Args:
            user_input: The user's request or query
            
        Returns:
            A dictionary containing extracted return information
        """
        # This could be enhanced with regex patterns or entity extraction
        # For now, return an empty dict as a placeholder
        return {}