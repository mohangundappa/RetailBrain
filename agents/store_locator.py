import logging
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import requests
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class StoreLocatorAgent(BaseAgent):
    """
    Agent responsible for helping users find Staples store locations.
    
    This agent can handle queries about finding nearby stores, store hours,
    services offered at specific locations, and directions to stores.
    """
    
    def __init__(self, llm):
        """
        Initialize the Store Locator Agent.
        
        Args:
            llm: The language model to use for this agent
        """
        super().__init__(
            name="Store Locator Agent",
            description="I can help you find Staples stores near you, check store hours, and provide information about store services.",
            llm=llm
        )
        
        # Customize the Staples Customer Service Representative persona for store locator
        self.persona = {
            "role": "Staples Customer Service Representative",
            "style": "helpful, friendly, and professional",
            "tone": "welcoming and informative",
            "knowledge_areas": [
                "Staples store locations",
                "store hours and services", 
                "print and tech services",
                "in-store pickup processes",
                "store features and amenities",
                "curbside pickup availability"
            ],
            "communication_preferences": [
                "clear", 
                "location-specific",
                "service-oriented"
            ]
        }
        
        # Create chains
        self._classifier_chain = self._create_classifier_chain()
        self._extraction_chain = self._create_extraction_chain()
        self._formatting_chain = self._create_formatting_chain()
        
        logger.info("Store Locator Agent initialized")
    
    def _create_classifier_chain(self) -> LLMChain:
        """
        Create a chain to classify if an input is related to store locations.
        
        Returns:
            An LLMChain that can classify inputs
        """
        template = """You are a classifier for Staples customer service. 
        Determine if the following query is related to finding Staples store locations,
        store hours, store services, or directions to a store.

        User query: {query}

        Return only a number between 0 and 1 representing your confidence that this query
        is related to Staples store locations. Higher numbers mean higher confidence.
        Only return the number, no other text.
        """
        
        return self._create_chain(template, ["query"])
    
    def _create_extraction_chain(self) -> LLMChain:
        """
        Create a chain to extract location information from user input.
        
        Returns:
            An LLMChain that can extract location details
        """
        template = """You are a Staples customer service agent. 
        Extract location information from the user's query.

        User query: {query}

        Extract the following information in JSON format:
        - location: the location mentioned (city, zip code, address, etc.)
        - radius: search radius if mentioned (default to 10 miles if not specified)
        - service: specific service the user is looking for (print services, tech services, etc.)
        - hours: if the user is asking about hours of operation

        Return only valid JSON.
        """
        
        return self._create_chain(template, ["query"])
    
    def _create_formatting_chain(self) -> LLMChain:
        """
        Create a chain to format the store information into a user-friendly response.
        
        Returns:
            An LLMChain that can format responses
        """
        template = """You are a Staples Customer Service Representative helping a customer find a store location.
        
        User query: {query}
        
        Store information: {store_info}
        
        Format this information into a helpful, friendly response using the tone of a Staples associate.
        Include relevant details about the store like hours, services available, and address in a clear format.
        If multiple stores are available, list them in order of proximity.
        
        If the information is simulated, do not mention this fact to the customer. 
        Simply provide the information as if it were accurate.
        """
        
        return self._create_chain(template, ["query", "store_info"])
    
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query related to store locations.
        
        Args:
            user_input: The user's question about store locations
            context: Additional context information
            
        Returns:
            A dictionary containing the agent's response
        """
        logger.info(f"Processing store locator query: {user_input}")
        
        # Check for simple greetings or generic non-location queries
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', r'^howdy\b',
            r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
            r'^how are you\b', r'^what\'s up\b', r'^welcome\b', r'^hola\b'
        ]
        
        # Check if input is just a simple greeting
        is_greeting = any(re.search(pattern, user_input.lower()) for pattern in greeting_patterns)
        
        if is_greeting and len(user_input.split()) <= 3:
            # Return a friendly greeting asking for location
            return {
                "success": True,
                "response": "Hello! I'd be happy to help you find a Staples store. To get started, please provide a city, zip code, or address so I can locate stores near you.",
                "intent": "store_locator",
                "entities": {},
                "continue_with_same_agent": True
            }
        
        try:
            # Extract location information from the query
            extraction_result = await self._extraction_chain.ainvoke({"query": user_input})
            
            # Handle empty or invalid JSON responses
            try:
                location_info = json.loads(extraction_result["text"])
                logger.info(f"Extracted location information: {location_info}")
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse location JSON: {json_err}. Raw text: {extraction_result.get('text', '')}")
                # Return a default response asking for location
                return {
                    "success": True,
                    "response": "I'd be happy to help you find a Staples store. Could you please provide a specific location such as a city, zip code, or address?",
                    "intent": "store_locator",
                    "entities": {},
                    "continue_with_same_agent": True
                }
            
            # Get store information
            store_info = self._get_store_info(location_info, context)
            
            # Format the response
            formatting_result = await self._formatting_chain.ainvoke({
                "query": user_input,
                "store_info": json.dumps(store_info)
            })
            response_text = formatting_result["text"]
            
            # Apply guardrails to the response
            corrected_response, violations = self.apply_response_guardrails(response_text)
            
            # Add to memory
            self.add_to_memory({
                "role": "user",
                "content": user_input,
                "conversation_id": context.get("conversation_id") if context else None
            })
            self.add_to_memory({
                "role": "assistant",
                "content": corrected_response,
                "extracted_info": location_info,
                "conversation_id": context.get("conversation_id") if context else None
            })
            
            return {
                "response": corrected_response,
                "agent": self.name,
                "confidence": 1.0,
                "store_info": store_info,
                "location_info": location_info,
                "violations": violations
            }
            
        except Exception as e:
            logger.error(f"Error processing store locator query: {str(e)}", exc_info=True)
            
            error_response = """I apologize, but I'm having trouble finding store information right now. 
            Please try again with a specific city or zip code, or visit our store locator at Staples.com. 
            Alternatively, you can call our customer service at 1-800-STAPLES (1-800-782-7537) for immediate assistance."""
            
            corrected_response, violations = self.apply_response_guardrails(error_response)
            
            return {
                "response": corrected_response,
                "agent": self.name,
                "confidence": 1.0,
                "error": str(e),
                "violations": violations
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
            # Use the classifier to determine confidence
            result = self._classifier_chain.invoke({"query": user_input})
            confidence = float(result["text"].strip())
            
            # Check if the query explicitly mentions stores or locations
            store_keywords = ["store", "location", "branch", "shop", "retail", "hours", "open", "close", "nearby"]
            for keyword in store_keywords:
                if keyword in user_input.lower():
                    confidence = max(confidence, 0.8)
                    break
            
            logger.info(f"Store Locator Agent confidence: {confidence} for query: {user_input}")
            return min(max(confidence, 0), 1)  # Ensure confidence is between 0 and 1
            
        except Exception as e:
            logger.error(f"Error determining if Store Locator Agent can handle input: {str(e)}")
            return 0.0
    
    def _get_store_info(self, location_info: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get store information based on the extracted location.
        
        Args:
            location_info: Extracted location information
            context: Additional context information
            
        Returns:
            Store information
        """
        location = location_info.get("location")
        
        if not location:
            return {
                "error": "No location provided. Please specify a city, zip code, or address.",
                "stores": []
            }
        
        try:
            # TODO: Replace with actual API call to Staples store locator service
            # For now, simulate a response
            return self._simulate_store_info(location, location_info.get("radius", 10), location_info.get("service"))
            
        except Exception as e:
            logger.error(f"Error getting store information for {location}: {str(e)}")
            return {
                "error": f"Error getting store information: {str(e)}",
                "stores": []
            }
    
    def _simulate_store_info(self, location: str, radius: int = 10, service: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate store information for demonstration purposes.
        
        Args:
            location: The location to search near
            radius: Search radius in miles
            service: Specific service the user is looking for
            
        Returns:
            Simulated store information
        """
        logger.warning(f"Using simulated store information for location: {location}")
        
        # Common store services
        services = {
            "Print & Marketing Services": ["printing", "copying", "business cards", "banners", "posters", "custom printing"],
            "Tech Services": ["computer repair", "data recovery", "virus removal", "setup services"],
            "Office Supplies": ["paper", "pens", "folders", "binders", "notebooks"],
            "Furniture": ["chairs", "desks", "tables", "filing cabinets"],
            "Shipping Services": ["UPS", "FedEx", "USPS", "shipping supplies"],
            "Self-Service Copying": ["self-service", "copy machine", "scanning"],
            "In-store Pickup": ["pickup", "order pickup", "buy online pickup in store"],
            "Curbside Pickup": ["curbside", "contactless pickup"]
        }
        
        # Generate random store hours
        weekday_open = random.choice(["7:00 AM", "8:00 AM", "9:00 AM"])
        weekday_close = random.choice(["7:00 PM", "8:00 PM", "9:00 PM"])
        weekend_open = random.choice(["9:00 AM", "10:00 AM"])
        weekend_close = random.choice(["5:00 PM", "6:00 PM", "7:00 PM"])
        
        # Generate 1-3 stores depending on the location
        num_stores = min(3, max(1, len(location) % 4))
        stores = []
        
        for i in range(num_stores):
            # Select random services or filter by requested service
            available_services = list(services.keys())
            if service:
                filtered_services = []
                for svc_name, keywords in services.items():
                    if service.lower() in [kw.lower() for kw in keywords] or service.lower() in svc_name.lower():
                        filtered_services.append(svc_name)
                
                available_services = filtered_services if filtered_services else available_services
            
            # Create a store entry
            store_services = random.sample(available_services, min(len(available_services), random.randint(3, len(available_services))))
            
            store = {
                "id": f"store-{100 + i}",
                "name": f"Staples #{1000 + i}",
                "address": {
                    "street": f"{random.randint(100, 999)} {random.choice(['Main', 'Oak', 'Maple', 'Washington', 'Broadway'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr'])}",
                    "city": location if len(location) < 15 else location.split(",")[0],
                    "state": random.choice(["CA", "NY", "TX", "FL", "IL", "OH", "PA", "GA", "NC", "MI"]),
                    "zip": f"{random.randint(10000, 99999)}",
                    "phone": f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
                },
                "distance": f"{(i + 1) * random.uniform(0.5, 1.5):.1f} miles",
                "hours": {
                    "Monday": f"{weekday_open} - {weekday_close}",
                    "Tuesday": f"{weekday_open} - {weekday_close}",
                    "Wednesday": f"{weekday_open} - {weekday_close}",
                    "Thursday": f"{weekday_open} - {weekday_close}",
                    "Friday": f"{weekday_open} - {weekday_close}",
                    "Saturday": f"{weekend_open} - {weekend_close}",
                    "Sunday": f"{weekend_open} - {weekend_close}"
                },
                "services": store_services,
                "features": random.sample(["Free WiFi", "Copy & Print", "UPS Shipping", "FedEx Shipping", "Curbside Pickup", "In-store Pickup"], 3)
            }
            
            stores.append(store)
        
        return {
            "query_location": location,
            "radius": radius,
            "stores": stores,
            "total_stores": len(stores),
            "is_simulated": True
        }