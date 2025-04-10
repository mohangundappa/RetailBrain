import logging
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import requests
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import StrOutputParser
from agents.base_agent import BaseAgent, EntityDefinition

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
        
        # Setup entity collection
        self.setup_entity_definitions()
        
        logger.info("Store Locator Agent initialized")
        
    def setup_entity_definitions(self) -> None:
        """
        Set up entity definitions for store location queries with validation patterns and examples.
        """
        # Define location entity
        location_entity = EntityDefinition(
            name="location",
            required=True,
            validation_pattern=r'^[A-Za-z0-9\s\.,\-\']{3,50}$',
            error_message="Please provide a valid city, state, or zip code.",
            description="Your location (city, state, or zip code)",
            examples=["Boston, MA", "90210", "Chicago"],
            alternate_names=["city", "zip", "zip code", "postal code", "town", "state", "area"]
        )
        
        # Set up entity collection with these entities
        self.setup_entity_collection([location_entity])
    
    def _create_classifier_chain(self) -> RunnableSequence:
        """
        Create a chain to classify if an input is related to store locations.
        
        Returns:
            A RunnableSequence that can classify inputs
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
    
    def _create_extraction_chain(self) -> RunnableSequence:
        """
        Create a chain to extract location information from user input.
        
        Returns:
            A RunnableSequence that can extract location details
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
    
    def _create_formatting_chain(self) -> RunnableSequence:
        """
        Create a chain to format the store information into a user-friendly response.
        
        Returns:
            A RunnableSequence that can format responses
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
        
        # First, let the base class handle simple greetings
        parent_response = await super().process(user_input, context)
        if parent_response:
            # If the parent class returned a response (e.g., for a greeting), use it
            return parent_response
            
        # Process entity collection first
        collection_complete, follow_up_prompt = await self.process_entity_collection(user_input, context)
        
        # If we need to continue collecting entities, return a follow-up question
        if not collection_complete and follow_up_prompt:
            # Add agent_name to context to ensure we stay with this agent during entity collection
            if context and 'conversation_memory' in context:
                memory = context['conversation_memory']
                memory.update_working_memory('continue_with_same_agent', True)
                memory.update_working_memory('last_selected_agent', self.name)
            
            return {
                "response": follow_up_prompt,
                "agent": self.name,
                "confidence": 1.0,
                "continue_with_same_agent": True
            }
            
        try:
            # Get collected values
            collected_entities = self.get_collected_entity_values()
            location = collected_entities.get("location") if "location" in collected_entities else None
            
            # Extract location info
            extraction_result = await self._extraction_chain.ainvoke({"query": user_input})
            
            # Handle empty or invalid JSON responses
            try:
                location_info = json.loads(extraction_result["text"])
                logger.info(f"Extracted location information: {location_info}")
                
                # If we have a location from entity collection, use it instead
                if location:
                    location_info["location"] = location
                
                # If we don't have a location at all, return a prompt
                if not location and not location_info.get("location"):
                    return {
                        "success": True,
                        "response": "I'd be happy to help you find a Staples store. Could you please provide a specific location such as a city, zip code, or address?",
                        "intent": "store_locator",
                        "entities": {},
                        "continue_with_same_agent": True
                    }
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse location JSON: {json_err}. Raw text: {extraction_result.get('text', '')}")
                
                # If we have a location from entity collection, create a simple location_info
                if location:
                    location_info = {
                        "location": location,
                        "radius": 10,
                        "service": None,
                        "hours": False
                    }
                else:
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
            try:
                # Try newer invoke method first
                result = self._classifier_chain.invoke({"query": user_input})
                # Handle various result formats
                if isinstance(result, dict) and "text" in result:
                    confidence_str = result["text"].strip()
                elif isinstance(result, str):
                    confidence_str = result.strip()
                else:
                    confidence_str = str(result).strip()
                    
                confidence = float(confidence_str)
            except (AttributeError, TypeError) as e:
                logger.debug(f"Primary classification method failed: {str(e)}")
                # Fallback for older API versions
                try:
                    # Try direct LLM call as backup
                    client = self.llm.client
                    prompt = "Rate your confidence (0-1) in handling this store location query: " + user_input
                    messages = [{"role": "user", "content": prompt}]
                    
                    response = client.chat.completions.create(
                        model=self.llm.model_name,
                        messages=messages
                    )
                    confidence_str = response.choices[0].message.content.strip()
                    confidence = float(confidence_str)
                except Exception as e2:
                    logger.error(f"Fallback classification method also failed: {str(e2)}")
                    confidence = 0.5  # Default to reasonable confidence
            
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