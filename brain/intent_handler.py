import os
import logging
import json
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class IntentHandler:
    """
    Handles the identification of user intents and planning execution with LLMs.
    
    This class provides functionality to:
    1. Identify the intent behind user queries
    2. Create execution plans for handling intents
    3. Extract relevant entities from user queries
    """
    
    def __init__(self):
        """Initialize the intent handler with OpenAI models."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found. Intent handler will use fallback mode.")
            self._setup_fallback()
            return
            
        # Initialize LLM for intent classification
        self.llm = ChatOpenAI(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            openai_api_key=self.api_key,
            temperature=0.1
        )
        
        # Create templates for different tasks
        self._create_templates()
        logger.info("Intent handler initialized with OpenAI LLM")
        
    def _setup_fallback(self):
        """Set up fallback mode for when no API key is available."""
        logger.warning("Using rule-based fallback for intent handling")
        self.fallback_mode = True
        
    def _create_templates(self):
        """Create prompt templates for different tasks."""
        # Intent identification template
        self.intent_template = ChatPromptTemplate.from_template("""
        You are an intent classifier for the Staples Brain system. Your job is to identify the intent
        behind the user's query and return it in a structured format.
        
        Current available intents:
        - package_tracking: User wants to track a package or get shipping information
        - password_reset: User wants to reset password or recover account
        - unknown: The user's query doesn't match any known intent
        
        User query: {query}
        
        Return a JSON object with the following fields:
        - intent: The identified intent (package_tracking, password_reset, or unknown)
        - confidence: A confidence score between 0 and 1
        - explanation: A brief explanation of why this intent was chosen
        
        Format your response as a valid JSON object only, with no additional text.
        """)
        
        # Entity extraction template
        self.entity_template = ChatPromptTemplate.from_template("""
        You are an entity extractor for the Staples Brain system. Extract structured information
        from the user's query based on the identified intent.
        
        User query: {query}
        Identified intent: {intent}
        
        For package_tracking intent, extract:
        - tracking_number: Package tracking number if present
        - shipping_carrier: Shipping carrier name if mentioned (UPS, FedEx, USPS, etc.)
        - order_number: Order number if mentioned
        - time_frame: Any time frame mentioned (e.g., "last week", "yesterday")
        
        For password_reset intent, extract:
        - email: User's email address if provided
        - username: User's username if provided
        - account_type: Type of account mentioned (e.g., Staples.com, Rewards)
        - issue: Specific issue mentioned (forgot password, account locked, etc.)
        
        Return a JSON object with only the relevant fields for the identified intent.
        If information is not available, use null.
        
        Format your response as a valid JSON object only, with no additional text.
        """)
        
        # Execution planning template
        self.planning_template = ChatPromptTemplate.from_template("""
        You are an execution planner for the Staples Brain system. Create a plan for handling the
        user's request based on the identified intent and extracted entities.
        
        User query: {query}
        Identified intent: {intent}
        Extracted entities: {entities}
        
        Create a step-by-step plan for addressing this user request, including:
        - which agent should handle this request
        - what specific functions or APIs should be called
        - what data should be retrieved or processed
        - what response should be generated
        
        Return a JSON object with the following fields:
        - agent: The name of the agent that should handle this request
        - actions: A list of action steps to take
        - expected_output: What the final output should include
        
        Format your response as a valid JSON object only, with no additional text.
        """)
        
    async def identify_intent(self, query: str) -> Dict[str, Any]:
        """
        Identify the intent behind a user query.
        
        Args:
            query: The user's query
            
        Returns:
            Dict containing intent classification
        """
        if not hasattr(self, 'api_key') or not self.api_key:
            return self._fallback_intent_classification(query)
            
        try:
            chain = self.intent_template | self.llm
            response = await chain.ainvoke({"query": query})
            content = response.content
            
            # Parse JSON response
            result = json.loads(content)
            logger.info(f"Identified intent: {result['intent']} with confidence {result['confidence']}")
            return result
        except Exception as e:
            logger.error(f"Error identifying intent: {str(e)}", exc_info=True)
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "explanation": f"Error in intent identification: {str(e)}"
            }
    
    async def extract_entities(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Extract relevant entities from a user query based on intent.
        
        Args:
            query: The user's query
            intent: The identified intent
            
        Returns:
            Dict containing extracted entities
        """
        if not hasattr(self, 'api_key') or not self.api_key:
            return self._fallback_entity_extraction(query, intent)
            
        try:
            chain = self.entity_template | self.llm
            response = await chain.ainvoke({"query": query, "intent": intent})
            content = response.content
            
            # Parse JSON response
            result = json.loads(content)
            logger.info(f"Extracted entities for {intent}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}", exc_info=True)
            return {
                "error": f"Failed to extract entities: {str(e)}"
            }
    
    async def create_execution_plan(self, query: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a plan for executing the user's request.
        
        Args:
            query: The user's query
            intent: The identified intent
            entities: The extracted entities
            
        Returns:
            Dict containing execution plan
        """
        if not hasattr(self, 'api_key') or not self.api_key:
            return self._fallback_execution_plan(intent)
            
        try:
            chain = self.planning_template | self.llm
            response = await chain.ainvoke({
                "query": query,
                "intent": intent,
                "entities": json.dumps(entities)
            })
            content = response.content
            
            # Parse JSON response
            result = json.loads(content)
            logger.info(f"Created execution plan for {intent}")
            return result
        except Exception as e:
            logger.error(f"Error creating execution plan: {str(e)}", exc_info=True)
            return {
                "agent": self._get_agent_for_intent(intent),
                "actions": ["default_processing"],
                "expected_output": "Basic response based on intent"
            }
    
    def _fallback_intent_classification(self, query: str) -> Dict[str, Any]:
        """
        Simple rule-based intent classification as fallback.
        
        Args:
            query: The user's query
            
        Returns:
            Dict containing intent classification
        """
        query_lower = query.lower()
        
        # Check for package tracking intent
        if any(keyword in query_lower for keyword in ["track", "package", "shipping", "delivery", "order status"]):
            return {
                "intent": "package_tracking",
                "confidence": 0.8,
                "explanation": "Query contains package tracking related keywords"
            }
        
        # Check for password reset intent
        elif any(keyword in query_lower for keyword in ["password", "reset", "forgot", "login", "sign in", "account"]):
            return {
                "intent": "password_reset",
                "confidence": 0.8,
                "explanation": "Query contains password reset related keywords"
            }
        
        # Default to unknown
        else:
            return {
                "intent": "unknown",
                "confidence": 0.6,
                "explanation": "Query doesn't match any known intent patterns"
            }
    
    def _fallback_entity_extraction(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Simple rule-based entity extraction as fallback.
        
        Args:
            query: The user's query
            intent: The identified intent
            
        Returns:
            Dict containing extracted entities
        """
        query_lower = query.lower()
        
        if intent == "package_tracking":
            # Very basic extraction - in real cases would use regex patterns
            tracking_number = None
            words = query.split()
            for word in words:
                if word.upper().startswith("TRACK") or word.isdigit() or (len(word) > 8 and any(c.isdigit() for c in word)):
                    tracking_number = word
                    break
                    
            return {
                "tracking_number": tracking_number,
                "shipping_carrier": "UPS" if "ups" in query_lower else "FedEx" if "fedex" in query_lower else None,
                "order_number": None,
                "time_frame": None
            }
        
        elif intent == "password_reset":
            # Look for email pattern (very simplistic)
            email = None
            words = query.split()
            for word in words:
                if "@" in word and "." in word:
                    email = word
                    break
                    
            return {
                "email": email,
                "username": None,
                "account_type": "Staples.com",
                "issue": "forgot password"
            }
        
        else:
            return {}
    
    def _fallback_execution_plan(self, intent: str) -> Dict[str, Any]:
        """
        Create a basic execution plan based on intent.
        
        Args:
            intent: The identified intent
            
        Returns:
            Dict containing execution plan
        """
        agent = self._get_agent_for_intent(intent)
        
        if intent == "package_tracking":
            return {
                "agent": agent,
                "actions": [
                    "extract_tracking_info",
                    "get_package_status",
                    "format_response"
                ],
                "expected_output": "Package status information"
            }
        elif intent == "password_reset":
            return {
                "agent": agent,
                "actions": [
                    "extract_account_info",
                    "generate_reset_instructions",
                    "format_response"
                ],
                "expected_output": "Password reset instructions"
            }
        else:
            return {
                "agent": "unknown",
                "actions": ["default_processing"],
                "expected_output": "Basic response"
            }
    
    def _get_agent_for_intent(self, intent: str) -> str:
        """Map intent to agent name."""
        intent_to_agent = {
            "package_tracking": "Package Tracking Agent",
            "password_reset": "Reset Password Agent",
            "unknown": "Default Agent"
        }
        return intent_to_agent.get(intent, "Default Agent")