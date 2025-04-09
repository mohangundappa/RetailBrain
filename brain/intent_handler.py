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
        - order_status: User wants to check the status of an order
        - shipping_inquiry: User has questions about shipping methods, costs, or timelines
        - delivery_status: User wants to know when their order will be delivered
        - package_location: User wants to know where their package is currently located
        - password_reset: User wants to reset password or recover account
        - account_access: User is having trouble accessing their account
        - login_issue: User can't log in to their account
        - forgot_password: User specifically mentions forgetting their password
        - unknown: The user's query doesn't match any known intent
        
        User query: {query}
        
        Return a JSON object with the following fields:
        - intent: The identified intent from the list above
        - confidence: A confidence score between 0 and 1
        - explanation: A brief explanation of why this intent was chosen
        - primary_category: Either "package_tracking" or "password_reset" (the high-level category)
        - is_follow_up: Boolean indicating if this appears to be a follow-up to a previous conversation
        
        Format your response as a valid JSON object only, with no additional text.
        """)
        
        # Entity extraction template
        self.entity_template = ChatPromptTemplate.from_template("""
        You are an entity extractor for the Staples Brain system. Extract structured information
        from the user's query based on the identified intent.
        
        User query: {query}
        Identified intent: {intent}
        
        For any shipping or package-related intents (package_tracking, order_status, shipping_inquiry, delivery_status, package_location), extract:
        - tracking_number: Package tracking number if present (alphanumeric string, usually 10-30 characters)
        - shipping_carrier: Shipping carrier name if mentioned (UPS, FedEx, USPS, DHL, etc.)
        - order_number: Order number if mentioned (usually starts with an alphabetic character)
        - time_frame: Any time frame mentioned (e.g., "last week", "yesterday", "two days ago")
        - urgency: Level of urgency expressed by the user (high, medium, low, or null if not indicated)
        - delivery_address: Any partial or full address mentioned for delivery
        - product_info: Any product information mentioned in the query
        
        For any account-related intents (password_reset, account_access, login_issue, forgot_password), extract:
        - email: User's email address if provided
        - username: User's username if provided
        - account_type: Type of account mentioned (e.g., Staples.com, Rewards, Business, Premium)
        - issue: Specific issue mentioned (forgot password, account locked, incorrect password, etc.)
        - last_login_attempt: Any information about when they last tried to login
        - device_info: Any device information mentioned (mobile, desktop, app, etc.)
        - browser_info: Any browser information mentioned (Chrome, Firefox, etc.)
        
        For all intents, also extract:
        - sentiment: The user's apparent sentiment (frustrated, neutral, positive)
        - follow_up: Whether this is a follow-up to a previous conversation (true/false)
        - user_name: The user's name if they introduced themselves
        - temporal_references: Any time-related references that might indicate context
        
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
        
        AVAILABLE AGENTS:
        1. Package Tracking Agent
           - Handles all shipping, tracking, and delivery related inquiries
           - Can retrieve package status, estimated delivery dates, and shipping details
           - Works best with tracking numbers, order numbers, or shipping carriers
           
        2. Reset Password Agent
           - Handles all account access and password reset related inquiries
           - Can generate password reset instructions and troubleshoot login issues
           - Works best with email addresses, usernames, or account types
        
        Create a detailed execution plan addressing this user request, including:
        - Which agent should handle this request and why
        - What specific functions or APIs should be called
        - What data is required and how it should be retrieved or processed
        - What the response should include and how it should be formatted
        - Whether additional context or memory from previous interactions might be helpful
        - Whether this interaction will likely need follow-up
        
        Return a JSON object with the following fields:
        - agent: The name of the agent that should handle this request (one of the available agents)
        - confidence: A score from 0-1 indicating how confident you are in this agent selection
        - reasoning: Brief explanation of why this agent is appropriate
        - actions: A list of action steps to take in sequence
        - required_entities: List of entity keys that are essential for processing this request
        - optional_entities: List of entity keys that would be helpful but aren't required
        - expected_output: Detailed description of what the final output should include
        - continue_with_same_agent: Boolean indicating if subsequent related queries should use this same agent
        - fallback_response: What to tell the user if we cannot process their request with the available information
        
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
        
        # Package tracking related intents
        if "track" in query_lower and ("package" in query_lower or "order" in query_lower):
            return {
                "intent": "package_tracking",
                "confidence": 0.85,
                "explanation": "Query specifically mentions tracking a package",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        elif "order status" in query_lower or "my order" in query_lower:
            return {
                "intent": "order_status",
                "confidence": 0.8,
                "explanation": "Query is about order status",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        elif "shipping" in query_lower and any(word in query_lower for word in ["cost", "price", "methods", "options"]):
            return {
                "intent": "shipping_inquiry",
                "confidence": 0.8,
                "explanation": "Query is about shipping methods or costs",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        elif any(phrase in query_lower for phrase in ["when will", "deliver", "arrival", "when is", "expected"]) and any(word in query_lower for word in ["package", "order", "item", "product"]):
            return {
                "intent": "delivery_status",
                "confidence": 0.8,
                "explanation": "Query is about delivery timing",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        elif "where" in query_lower and any(word in query_lower for word in ["package", "order", "delivery"]):
            return {
                "intent": "package_location",
                "confidence": 0.8,
                "explanation": "Query is about package location",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        
        # Account and password related intents
        elif any(phrase in query_lower for phrase in ["reset password", "change password"]):
            return {
                "intent": "password_reset",
                "confidence": 0.85,
                "explanation": "Query specifically mentions password reset",
                "primary_category": "password_reset",
                "is_follow_up": False
            }
        elif "forgot" in query_lower and any(word in query_lower for word in ["password", "login", "credentials"]):
            return {
                "intent": "forgot_password",
                "confidence": 0.85,
                "explanation": "User has forgotten their password",
                "primary_category": "password_reset",
                "is_follow_up": False
            }
        elif any(phrase in query_lower for phrase in ["can't log in", "cannot log in", "login problem", "trouble logging"]):
            return {
                "intent": "login_issue",
                "confidence": 0.8,
                "explanation": "User is having trouble logging in",
                "primary_category": "password_reset",
                "is_follow_up": False
            }
        elif "access" in query_lower and "account" in query_lower:
            return {
                "intent": "account_access",
                "confidence": 0.8,
                "explanation": "User is having account access issues",
                "primary_category": "password_reset",
                "is_follow_up": False
            }
        
        # General catch-all for broader categories
        elif any(keyword in query_lower for keyword in ["tracking", "package", "shipping", "delivery", "order"]):
            return {
                "intent": "package_tracking",
                "confidence": 0.7,
                "explanation": "Query contains package tracking related keywords",
                "primary_category": "package_tracking",
                "is_follow_up": False
            }
        elif any(keyword in query_lower for keyword in ["password", "reset", "forgot", "login", "sign in", "account"]):
            return {
                "intent": "password_reset",
                "confidence": 0.7,
                "explanation": "Query contains password reset related keywords",
                "primary_category": "password_reset",
                "is_follow_up": False
            }
        
        # Follow-up detection (very basic)
        elif any(phrase in query_lower for phrase in ["what about", "how about", "and also", "one more thing"]):
            # This is overly simplistic - in a real system we'd use context
            return {
                "intent": "unknown",
                "confidence": 0.5,
                "explanation": "Appears to be a follow-up question",
                "primary_category": None,
                "is_follow_up": True
            }
        
        # Default to unknown
        else:
            return {
                "intent": "unknown",
                "confidence": 0.3,
                "explanation": "Query doesn't match any known intent patterns",
                "primary_category": None,
                "is_follow_up": False
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
        words = query.split()
        
        # Common entities for all intents
        entities = {
            "sentiment": "frustrated" if any(word in query_lower for word in ["urgent", "frustrated", "angry", "upset", "annoyed"]) else 
                        "positive" if any(word in query_lower for word in ["please", "thank", "appreciate", "grateful"]) else "neutral",
            "follow_up": any(phrase in query_lower for phrase in ["what about", "how about", "and also", "additionally", "one more thing"]),
            "user_name": self._extract_name(query),
            "temporal_references": self._extract_time_reference(query_lower)
        }
        
        # Package tracking related intents
        if intent in ["package_tracking", "order_status", "shipping_inquiry", "delivery_status", "package_location"]:
            # Extract tracking number (simplistic)
            tracking_number = None
            for word in words:
                # Look for alphanumeric strings that could be tracking numbers
                if (len(word) >= 8 and any(c.isdigit() for c in word) and 
                    (word.isalnum() or any(c in word for c in "-_#"))):
                    tracking_number = word.strip('.,;:!?')
                    break
            
            # Extract shipping carrier
            shipping_carrier = None
            carriers = {
                "ups": "UPS", 
                "fedex": "FedEx", 
                "usps": "USPS", 
                "dhl": "DHL", 
                "purolator": "Purolator"
            }
            for carrier_key, carrier_name in carriers.items():
                if carrier_key in query_lower:
                    shipping_carrier = carrier_name
                    break
            
            # Extract order number (simplistic)
            order_number = None
            order_indicators = ["order", "purchase", "confirmation"]
            for i, word in enumerate(words):
                if i < len(words) - 1 and any(indicator in word.lower() for indicator in order_indicators):
                    next_word = words[i+1].strip('.,;:!?#')
                    if next_word.isalnum() and (next_word[0].isalpha() or next_word.isdigit()):
                        order_number = next_word
                        break
            
            # Extract time frame
            time_frame = self._extract_time_reference(query_lower)
            
            # Extract urgency
            urgency_words = {
                "high": ["urgent", "immediately", "asap", "emergency", "right now", "right away"],
                "medium": ["soon", "quickly", "fast", "expedite", "hurry"],
                "low": ["whenever", "at your convenience", "no rush"]
            }
            
            urgency = None
            for level, words_list in urgency_words.items():
                if any(word in query_lower for word in words_list):
                    urgency = level
                    break
            
            return {
                "tracking_number": tracking_number,
                "shipping_carrier": shipping_carrier,
                "order_number": order_number,
                "time_frame": time_frame,
                "urgency": urgency,
                "delivery_address": None,  # Would need more sophisticated extraction
                "product_info": None,      # Would need more sophisticated extraction
                **entities
            }
        
        # Account and password related intents
        elif intent in ["password_reset", "account_access", "login_issue", "forgot_password"]:
            # Extract email
            email = None
            for word in words:
                word = word.strip('.,;:!?')
                if "@" in word and "." in word and len(word) > 5:
                    email = word
                    break
            
            # Extract username (simplistic)
            username = None
            username_indicators = ["username", "user", "login", "name"]
            for i, word in enumerate(words):
                if i < len(words) - 1 and any(indicator in word.lower() for indicator in username_indicators):
                    next_word = words[i+1].strip('.,;:!?')
                    if "is" in next_word or ":" in next_word:
                        if i+2 < len(words):
                            username = words[i+2].strip('.,;:!?')
                    else:
                        username = next_word
                    break
            
            # Extract account type
            account_type = None
            account_types = {
                "staples.com": ["staples.com", "website", "online", "web", "site"],
                "rewards": ["rewards", "points", "loyalty"],
                "business": ["business", "corporate", "company", "office"],
                "premium": ["premium", "plus", "membership", "paid"]
            }
            
            for type_key, indicators in account_types.items():
                if any(indicator in query_lower for indicator in indicators):
                    account_type = type_key
                    break
                    
            if not account_type:
                account_type = "staples.com"  # Default
            
            # Extract issue type
            issue = None
            issue_types = {
                "forgot_password": ["forgot", "don't remember", "can't remember", "lost"],
                "account_locked": ["locked", "blocked", "disabled", "suspended"],
                "incorrect_password": ["wrong", "incorrect", "doesn't work", "not working", "fails"],
                "password_reset": ["reset", "change", "update", "new"],
                "login_failed": ["can't log in", "cannot login", "won't let me", "unable to"]
            }
            
            for issue_key, indicators in issue_types.items():
                if any(indicator in query_lower for indicator in indicators):
                    issue = issue_key
                    break
                    
            if not issue and "password" in query_lower:
                issue = "password_reset"
            elif not issue:
                issue = "account_access"
            
            # Device and browser info
            device_info = None
            browser_info = None
            
            device_types = ["mobile", "phone", "desktop", "laptop", "tablet", "ipad", "iphone", "android"]
            browser_types = ["chrome", "firefox", "safari", "edge", "explorer", "ie", "opera"]
            
            for device in device_types:
                if device in query_lower:
                    device_info = device
                    break
                    
            for browser in browser_types:
                if browser in query_lower:
                    browser_info = browser
                    break
            
            return {
                "email": email,
                "username": username,
                "account_type": account_type,
                "issue": issue,
                "last_login_attempt": None,  # Would need more sophisticated extraction
                "device_info": device_info,
                "browser_info": browser_info,
                **entities
            }
        
        else:
            return entities
    
    def _extract_name(self, query: str) -> Optional[str]:
        """Extract a potential name from the query."""
        words = query.split()
        
        # Very basic name extraction - look for "I am" or "my name is" patterns
        for i, word in enumerate(words):
            if i < len(words) - 2:
                if word.lower() == "i" and words[i+1].lower() == "am":
                    return words[i+2].strip('.,;:!?')
                elif word.lower() == "my" and words[i+1].lower() == "name" and words[i+2].lower() == "is":
                    if i+3 < len(words):
                        return words[i+3].strip('.,;:!?')
        
        return None
    
    def _extract_time_reference(self, query: str) -> Optional[str]:
        """Extract time references from the query."""
        time_references = [
            "today", "yesterday", "tomorrow", "last week", "next week", 
            "last month", "this month", "next month", "few days ago",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
        
        for ref in time_references:
            if ref in query:
                return ref
                
        # Check for "X days ago" pattern
        import re
        days_ago_match = re.search(r'(\d+)\s+days?\s+ago', query)
        if days_ago_match:
            return f"{days_ago_match.group(1)} days ago"
            
        return None
    
    def _fallback_execution_plan(self, intent: str) -> Dict[str, Any]:
        """
        Create a basic execution plan based on intent.
        
        Args:
            intent: The identified intent
            
        Returns:
            Dict containing execution plan
        """
        agent = self._get_agent_for_intent(intent)
        confidence = 0.7  # Default confidence
        
        # Package related intents
        if intent == "package_tracking":
            return {
                "agent": agent,
                "confidence": 0.8,
                "reasoning": "This is clearly a package tracking request requiring the Package Tracking Agent",
                "actions": [
                    "extract_tracking_info",
                    "get_package_status",
                    "format_tracking_response"
                ],
                "required_entities": ["tracking_number"],
                "optional_entities": ["shipping_carrier", "order_number", "time_frame"],
                "expected_output": "Status and location of the package with estimated delivery date",
                "continue_with_same_agent": True,
                "fallback_response": "I'll need your tracking number to check your package status."
            }
        elif intent == "order_status":
            return {
                "agent": agent,
                "confidence": 0.75,
                "reasoning": "This is an order status request that the Package Tracking Agent can handle",
                "actions": [
                    "extract_order_info",
                    "get_order_status",
                    "check_shipping_status", 
                    "format_order_response"
                ],
                "required_entities": ["order_number"],
                "optional_entities": ["tracking_number", "shipping_carrier"],
                "expected_output": "Order status with shipping information if available",
                "continue_with_same_agent": True,
                "fallback_response": "I'll need your order number to check the status."
            }
        elif intent == "shipping_inquiry":
            return {
                "agent": agent,
                "confidence": 0.7,
                "reasoning": "This is a general shipping inquiry for the Package Tracking Agent",
                "actions": [
                    "identify_shipping_question_type",
                    "retrieve_shipping_information",
                    "format_shipping_response"
                ],
                "required_entities": [],
                "optional_entities": ["shipping_carrier", "delivery_address", "product_info"],
                "expected_output": "Information about shipping methods, costs, or policies",
                "continue_with_same_agent": True,
                "fallback_response": "I can help with shipping questions. What specific information do you need?"
            }
        elif intent == "delivery_status" or intent == "package_location":
            return {
                "agent": agent,
                "confidence": 0.75,
                "reasoning": "This is a delivery status or location request for the Package Tracking Agent",
                "actions": [
                    "extract_tracking_info",
                    "get_package_location",
                    "check_delivery_estimate",
                    "format_delivery_response"
                ],
                "required_entities": ["tracking_number"],
                "optional_entities": ["shipping_carrier", "order_number", "time_frame"],
                "expected_output": "Current location of the package and estimated delivery time",
                "continue_with_same_agent": True,
                "fallback_response": "I'll need your tracking number to check where your package is."
            }
            
        # Password/account related intents
        elif intent == "password_reset":
            return {
                "agent": agent,
                "confidence": 0.8,
                "reasoning": "This is a password reset request requiring the Reset Password Agent",
                "actions": [
                    "extract_account_info",
                    "validate_identity",
                    "generate_reset_instructions",
                    "format_reset_response"
                ],
                "required_entities": ["email"],
                "optional_entities": ["username", "account_type", "issue"],
                "expected_output": "Instructions for resetting password with appropriate links or steps",
                "continue_with_same_agent": True,
                "fallback_response": "I'll need your email address to help reset your password."
            }
        elif intent == "account_access" or intent == "login_issue":
            return {
                "agent": agent,
                "confidence": 0.75,
                "reasoning": "This is an account access or login issue for the Reset Password Agent",
                "actions": [
                    "identify_login_issue",
                    "extract_account_info",
                    "check_account_status",
                    "provide_access_instructions"
                ],
                "required_entities": ["email"],
                "optional_entities": ["username", "account_type", "device_info", "browser_info"],
                "expected_output": "Troubleshooting steps or instructions for regaining account access",
                "continue_with_same_agent": True,
                "fallback_response": "I can help with your account access issue. Could you please share the email address associated with your account?"
            }
        elif intent == "forgot_password":
            return {
                "agent": agent,
                "confidence": 0.8,
                "reasoning": "User explicitly mentioned forgetting their password, requiring Reset Password Agent",
                "actions": [
                    "extract_account_info",
                    "generate_recovery_link",
                    "provide_recovery_instructions"
                ],
                "required_entities": ["email"],
                "optional_entities": ["username", "account_type"],
                "expected_output": "Steps to recover password with appropriate recovery link or method",
                "continue_with_same_agent": True,
                "fallback_response": "I can help you recover your password. What email address did you use for your account?"
            }
            
        # Fallback for unknown intents
        else:
            return {
                "agent": "Default Agent",
                "confidence": 0.3,
                "reasoning": "No specific agent matches this intent type",
                "actions": [
                    "identify_general_request_type",
                    "provide_general_assistance",
                    "suggest_specific_help_options" 
                ],
                "required_entities": [],
                "optional_entities": ["user_name"],
                "expected_output": "General assistance or redirection to appropriate help resources",
                "continue_with_same_agent": False,
                "fallback_response": "I'm not sure I understand your request. Could you please provide more details about what you need help with?"
            }
    
    def _get_agent_for_intent(self, intent: str) -> str:
        """Map intent to agent name."""
        # Package-related intents
        package_intents = [
            "package_tracking", 
            "order_status", 
            "shipping_inquiry", 
            "delivery_status", 
            "package_location"
        ]
        
        # Account-related intents
        account_intents = [
            "password_reset", 
            "account_access", 
            "login_issue", 
            "forgot_password"
        ]
        
        if intent in package_intents:
            return "Package Tracking Agent"
        elif intent in account_intents:
            return "Reset Password Agent"
        else:
            return "Default Agent"