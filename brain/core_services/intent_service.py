"""
Intent service for Staples Brain.

This service provides intent recognition and entity extraction functionality,
encapsulating the NLU (Natural Language Understanding) capabilities of the system.
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from brain.core_services.base_service import CoreService
from utils.observability import record_llm_request, record_error

logger = logging.getLogger(__name__)

class IntentService(CoreService):
    """
    Service for handling intent recognition and entity extraction.
    
    This service encapsulates the NLU capabilities of the system, providing
    a clean interface for intent recognition and related operations.
    """
    
    def __init__(self):
        """Initialize the intent service."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model_name = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.llm = None
        self.fallback_mode = False
        self.intent_template = None
        self.entity_extraction_template = None
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the intent service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            if not self.api_key:
                logger.warning("OPENAI_API_KEY not found. Intent service will use fallback mode.")
                self._setup_fallback()
                return False
                
            # Initialize LLM for intent classification
            self.llm = ChatOpenAI(
                model=self.model_name,
                openai_api_key=self.api_key,
                temperature=0.1
            )
            
            # Create templates for different tasks
            self._create_templates()
            
            logger.info(f"Intent service initialized with model: {self.model_name}")
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"model": self.model_name, "fallback_mode": self.fallback_mode}
            
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize intent service: {str(e)}"
            logger.error(error_message)
            record_error("intent_service_init", error_message)
            
            self._setup_fallback()
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def _setup_fallback(self):
        """Set up fallback mode for when no API key is available."""
        logger.warning("Using rule-based fallback for intent handling")
        self.fallback_mode = True
    
    def _create_templates(self):
        """Create prompt templates for different tasks."""
        # Zero-shot intent identification template
        self.intent_template = ChatPromptTemplate.from_template("""
        You are performing zero-shot intent classification for the Staples Brain system. Without any training data,
        you need to classify the user's query into the most appropriate intent category based on semantic understanding.
        
        Here are the possible intents:
        - package_tracking: Questions about tracking packages, deliveries, or shipping status
        - reset_password: Requests to reset or recover password or account access
        - store_locator: Questions about store locations, hours, or directions
        - product_info: Questions about product details, availability, or specifications
        - returns: Questions about returns policy or initiating a return
        - none: None of the above intents match
        
        User query: {query}
        
        Respond with a JSON object containing:
        - intent: The identified intent (must be one from the list above)
        - confidence: A confidence score between 0 and 1 (where 1 is highest confidence)
        - explanation: A brief explanation of why this intent was selected
        
        JSON Response:
        """)
        
        # Entity extraction template
        self.entity_extraction_template = ChatPromptTemplate.from_template("""
        You are extracting relevant entities from a user query for the Staples Brain system.
        Based on the detected intent, identify and extract important entities.
        
        User query: {query}
        Detected intent: {intent}
        
        Based on the intent, extract relevant entities as a JSON object.
        
        For package_tracking intent, extract:
        - tracking_number: Any package tracking numbers (if present)
        - order_number: Any order numbers (if present)
        - timeframe: Any mentioned timeframes (e.g., "yesterday", "last week")
        
        For reset_password intent, extract:
        - username: Any mentioned usernames or emails
        - account_type: Type of account (e.g., "customer", "business")
        
        For store_locator intent, extract:
        - location: Any mentioned locations (city, zip code, etc.)
        - service: Any specific services mentioned (e.g., "printing", "tech support")
        
        For product_info intent, extract:
        - product_name: Product names or descriptions
        - category: Product category if mentioned
        - attributes: Specific attributes asked about (e.g., "price", "availability")
        
        For returns intent, extract:
        - order_number: Any order numbers
        - product_name: Product names or descriptions
        - reason: Reason for return if mentioned
        
        JSON Response:
        """)
    
    async def identify_intent(self, query: str) -> Dict[str, Any]:
        """
        Identify the intent behind a user query.
        
        Args:
            query: User query text
            
        Returns:
            Dictionary containing intent information
        """
        if self.fallback_mode:
            return self._fallback_intent_recognition(query)
        
        try:
            # Use the LLM to classify intent
            start_time = datetime.now()
            chain = self.intent_template | self.llm
            result = await chain.ainvoke({"query": query})
            
            # Parse the result
            content = result.content
            try:
                # Try to parse as JSON
                if isinstance(content, str):
                    intent_data = json.loads(content)
                else:
                    intent_data = content
                    
                # Validate the response
                if "intent" not in intent_data or "confidence" not in intent_data:
                    logger.warning(f"Invalid intent response: {content}")
                    intent_data = {
                        "intent": "none",
                        "confidence": 0.0,
                        "explanation": "Failed to parse LLM response"
                    }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse intent result as JSON: {content}")
                # Extract intent using regex as fallback
                intent_data = self._extract_intent_from_text(content)
            
            # Log token usage
            prompt_tokens = getattr(result, "prompt_tokens", 0)
            completion_tokens = getattr(result, "completion_tokens", 0)
            record_llm_request(self.model_name, "intent_recognition", prompt_tokens, completion_tokens)
            
            # Enhance with metadata
            intent_data["processing_time"] = (datetime.now() - start_time).total_seconds()
            intent_data["timestamp"] = datetime.now().isoformat()
            
            return intent_data
            
        except Exception as e:
            error_message = f"Intent recognition failed: {str(e)}"
            logger.error(error_message)
            record_error("intent_recognition", error_message)
            
            return {
                "intent": "none",
                "confidence": 0.0,
                "explanation": f"Error during processing: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def extract_entities(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Extract relevant entities from a user query based on intent.
        
        Args:
            query: User query text
            intent: Identified intent
            
        Returns:
            Dictionary containing extracted entities
        """
        if self.fallback_mode:
            return self._fallback_entity_extraction(query, intent)
        
        try:
            # Use the LLM to extract entities
            start_time = datetime.now()
            chain = self.entity_extraction_template | self.llm
            result = await chain.ainvoke({"query": query, "intent": intent})
            
            # Parse the result
            content = result.content
            try:
                # Try to parse as JSON
                if isinstance(content, str):
                    entities = json.loads(content)
                else:
                    entities = content
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse entity extraction result as JSON: {content}")
                entities = self._extract_entities_from_text(content, intent)
            
            # Log token usage
            prompt_tokens = getattr(result, "prompt_tokens", 0)
            completion_tokens = getattr(result, "completion_tokens", 0)
            record_llm_request(self.model_name, "entity_extraction", prompt_tokens, completion_tokens)
            
            # Enhance with metadata
            entities["processing_time"] = (datetime.now() - start_time).total_seconds()
            entities["timestamp"] = datetime.now().isoformat()
            
            return entities
            
        except Exception as e:
            error_message = f"Entity extraction failed: {str(e)}"
            logger.error(error_message)
            record_error("entity_extraction", error_message)
            
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _fallback_intent_recognition(self, query: str) -> Dict[str, Any]:
        """
        Perform rule-based intent recognition as a fallback.
        
        Args:
            query: User query text
            
        Returns:
            Dictionary containing intent information
        """
        query_lower = query.lower()
        
        # Simple keyword-based classification
        if any(keyword in query_lower for keyword in ["track", "package", "shipping", "delivery", "shipped", "arrive"]):
            return {
                "intent": "package_tracking",
                "confidence": 0.7,
                "explanation": "Contains package tracking keywords",
                "timestamp": datetime.now().isoformat()
            }
        elif any(keyword in query_lower for keyword in ["password", "reset", "forgot", "can't login", "account access"]):
            return {
                "intent": "reset_password",
                "confidence": 0.7,
                "explanation": "Contains password reset keywords",
                "timestamp": datetime.now().isoformat()
            }
        elif any(keyword in query_lower for keyword in ["store", "location", "near me", "hours", "directions"]):
            return {
                "intent": "store_locator",
                "confidence": 0.7,
                "explanation": "Contains store locator keywords",
                "timestamp": datetime.now().isoformat()
            }
        elif any(keyword in query_lower for keyword in ["product", "item", "price", "available", "in stock"]):
            return {
                "intent": "product_info",
                "confidence": 0.7,
                "explanation": "Contains product info keywords",
                "timestamp": datetime.now().isoformat()
            }
        elif any(keyword in query_lower for keyword in ["return", "refund", "take back", "exchange"]):
            return {
                "intent": "returns",
                "confidence": 0.7,
                "explanation": "Contains returns keywords",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "intent": "none",
                "confidence": 0.5,
                "explanation": "No clear intent detected",
                "timestamp": datetime.now().isoformat()
            }
    
    def _fallback_entity_extraction(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Perform rule-based entity extraction as a fallback.
        
        Args:
            query: User query text
            intent: Identified intent
            
        Returns:
            Dictionary containing extracted entities
        """
        # Simple regex-based entity extraction
        entities = {}
        
        if intent == "package_tracking":
            # Look for possible tracking numbers (alphanumeric strings of certain length)
            import re
            tracking_pattern = r'\b[A-Z0-9]{9,30}\b'
            potential_numbers = re.findall(tracking_pattern, query.upper())
            if potential_numbers:
                entities["tracking_number"] = potential_numbers[0]
            
            # Look for order numbers
            order_pattern = r'\border\s*(?:number|#|num|id)?\s*[:# ]?\s*([A-Z0-9-]{5,15})\b'
            order_matches = re.findall(order_pattern, query.upper())
            if order_matches:
                entities["order_number"] = order_matches[0]
        
        # Add more entity extraction rules for other intents as needed
        
        entities["timestamp"] = datetime.now().isoformat()
        return entities
    
    def _extract_intent_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract intent information from unstructured text.
        
        Args:
            text: Unstructured text from LLM
            
        Returns:
            Structured intent information
        """
        text_lower = text.lower()
        intents = ["package_tracking", "reset_password", "store_locator", 
                  "product_info", "returns", "none"]
        
        # Look for intent mentions in the text
        detected_intent = "none"
        for intent in intents:
            if intent in text_lower:
                detected_intent = intent
                break
        
        # Extract confidence if mentioned
        confidence = 0.5  # Default
        import re
        confidence_matches = re.findall(r'confidence[:\s]+([0-9.]+)', text_lower)
        if confidence_matches:
            try:
                confidence = float(confidence_matches[0])
            except ValueError:
                pass
        
        return {
            "intent": detected_intent,
            "confidence": confidence,
            "explanation": "Extracted from unstructured response",
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_entities_from_text(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract entity information from unstructured text.
        
        Args:
            text: Unstructured text from LLM
            intent: Identified intent
            
        Returns:
            Structured entity information
        """
        # Simple regex-based extraction from the LLM output
        entities = {}
        
        # Generic patterns for common entity types
        import re
        
        # Extract key-value pairs from the text
        pair_pattern = r'[\"\']?(\w+)[\"\']?\s*:\s*[\"\']([^\"\']+)[\"\']'
        pairs = re.findall(pair_pattern, text)
        for key, value in pairs:
            entities[key.lower()] = value
        
        return entities
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "intent_service",
            "description": "Intent recognition and entity extraction service",
            "version": "1.0.0",
            "model": self.model_name,
            "fallback_mode": self.fallback_mode,
            "health_status": self.health_status
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Update health check status
            self.health_status["last_check"] = datetime.now().isoformat()
            
            if self.fallback_mode:
                self.health_status["healthy"] = True
                self.health_status["details"] = {
                    "mode": "fallback",
                    "message": "Operating in fallback mode"
                }
                return self.health_status
            
            # Check if LLM is initialized
            if self.llm is None:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "LLM not initialized"}
                return self.health_status
            
            # Could perform a simple LLM call to verify it's working
            # For now, we just verify it's initialized
            self.health_status["healthy"] = True
            self.health_status["details"] = {
                "model": self.model_name,
                "templates_initialized": self.intent_template is not None and self.entity_extraction_template is not None
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status