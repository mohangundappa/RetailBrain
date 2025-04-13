"""
Context-Enhanced Chat Service for Staples Brain.
This service extends the standard chat service with context awareness.
"""
import uuid
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union

from pydantic import BaseModel

from backend.services.customer_service import CustomerDataService
from backend.endpoints.chat.models import (
    ChatContext, ChatRequest, IdentityContext, CustomerProfile
)

# Set up logging
logger = logging.getLogger(__name__)


class ContextEnhancedChatService:
    """
    Chat service that incorporates context for personalized responses.
    This service provides a chat interface with context-aware processing.
    """
    
    def __init__(self):
        """Initialize the context-enhanced chat service"""
        self.customer_service = CustomerDataService()
        self.conversations = {}
        self.observability_data = {}
        logger.info("ContextEnhancedChatService initialized")
    
    async def process_chat(self, request: ChatRequest) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process a chat request with context awareness.
        
        Args:
            request: The chat request containing message and optional context
            
        Returns:
            Tuple containing (response_data, observability_data)
        """
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:10]}"
        logger.info(f"Processing chat request for conversation {conversation_id}")
        
        # Enrich context with customer data if available
        enriched_context = await self._enrich_context(request.context)
        
        # Process the message (in a real implementation, this would use the brain service)
        response_data, obs_data = await self._generate_response(
            request.message,
            conversation_id,
            enriched_context
        )
        
        # Store observability data
        self.observability_data[conversation_id] = obs_data
        
        # Store conversation if it's new
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "id": conversation_id,
                "messages": [],
                "context": enriched_context.dict() if enriched_context else None,
                "created_at": datetime.now().isoformat()
            }
        
        # Add messages to conversation history
        timestamp = datetime.now().isoformat()
        
        self.conversations[conversation_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": timestamp
        })
        
        self.conversations[conversation_id]["messages"].append({
            "role": "assistant",
            "content": response_data["message"],
            "timestamp": timestamp
        })
        
        # Update the title if it's the first message
        if len(self.conversations[conversation_id]["messages"]) == 2:  # We just added 2 messages
            title = request.message[:30]
            if len(request.message) > 30:
                title += "..."
            self.conversations[conversation_id]["title"] = title
        
        # Add conversation ID to response
        response_data["conversation_id"] = conversation_id
        response_data["timestamp"] = timestamp
        
        return response_data, obs_data
    
    async def _enrich_context(self, context: Optional[ChatContext]) -> Optional[ChatContext]:
        """
        Enrich the provided context with additional customer data.
        
        Args:
            context: The original context from the request
            
        Returns:
            Enriched context with additional customer data
        """
        if not context:
            logger.debug("No context provided for enrichment")
            return None
        
        logger.debug("Enriching context with customer data")
        
        # If we have customer_id but no customer_profile, try to fetch it
        if (context.identity and context.identity.customer_id and not context.customer_profile):
            logger.debug(f"Looking up customer by ID: {context.identity.customer_id}")
            customer_data = await self.customer_service.get_customer_by_id(context.identity.customer_id)
            if customer_data:
                logger.debug(f"Found customer data for ID: {context.identity.customer_id}")
                context.customer_profile = CustomerProfile(
                    customer_id=customer_data["customer_id"],
                    email=customer_data["email"],
                    phone=customer_data.get("phone"),
                    type=customer_data["type"],
                    tier=customer_data["tier"],
                    preferred_store_id=customer_data.get("preferred_store_id")
                )
        
        # If we have customer_profile with email but missing data, try to enrich
        elif (context.customer_profile and context.customer_profile.email and 
              not context.customer_profile.preferred_store_id):
            logger.debug(f"Looking up customer by email: {context.customer_profile.email}")
            customer_data = await self.customer_service.get_customer_by_email(context.customer_profile.email)
            if customer_data:
                logger.debug(f"Found customer data for email: {context.customer_profile.email}")
                # Update the existing profile with additional data
                context.customer_profile.customer_id = customer_data["customer_id"]
                context.customer_profile.phone = customer_data.get("phone")
                context.customer_profile.type = customer_data["type"]
                context.customer_profile.tier = customer_data["tier"]
                context.customer_profile.preferred_store_id = customer_data.get("preferred_store_id")
        
        return context
    
    async def _generate_response(
        self,
        message: str,
        conversation_id: str,
        context: Optional[ChatContext]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate a response to the user message.
        
        Args:
            message: The user's message
            conversation_id: The current conversation ID
            context: Enriched context information
            
        Returns:
            Tuple of (response data, observability data)
        """
        # Initialize response and observability data
        personalized = False
        selected_agent = "general_assistant"
        customer_name = "there"
        
        logger.debug(f"Generating response for message: {message[:50]}{'...' if len(message) > 50 else ''}")
        
        # Extract lowercase message for easier matching
        msg_lower = message.lower()
        
        # Detect intent based on keywords in message
        intents = []
        if any(word in msg_lower for word in ["store", "location", "shop", "near"]):
            intents.append({"intent": "store_locator", "confidence": 0.78})
            intents.append({"intent": "general_query", "confidence": 0.12})
            intents.append({"intent": "product_info", "confidence": 0.10})
            selected_agent = "store_locator"
        elif any(word in msg_lower for word in ["order", "package", "delivery", "shipping", "track"]):
            intents.append({"intent": "order_tracking", "confidence": 0.82})
            intents.append({"intent": "returns", "confidence": 0.09})
            intents.append({"intent": "product_info", "confidence": 0.09})
            selected_agent = "order_tracking"
        elif any(word in msg_lower for word in ["password", "login", "account", "sign in", "forgot"]):
            intents.append({"intent": "password_reset", "confidence": 0.88})
            intents.append({"intent": "account_info", "confidence": 0.09})
            intents.append({"intent": "general_query", "confidence": 0.03})
            selected_agent = "password_reset"
        else:
            intents.append({"intent": "general_query", "confidence": 0.65})
            intents.append({"intent": "product_info", "confidence": 0.20})
            intents.append({"intent": "store_locator", "confidence": 0.15})
        
        logger.debug(f"Selected agent: {selected_agent}")
        
        # Extract entities
        entities = []
        if "boston" in msg_lower:
            entities.append({"type": "location", "value": "Boston", "confidence": 0.95})
        elif "new york" in msg_lower:
            entities.append({"type": "location", "value": "New York", "confidence": 0.95})
        
        if "order" in msg_lower and any(c.isdigit() for c in message):
            # Extract numbers that might be order numbers
            import re
            numbers = re.findall(r'\d+', message)
            if numbers:
                entities.append({"type": "order_number", "value": numbers[0], "confidence": 0.93})
        
        # Use context for personalization if available
        context_influence = {}
        if context and context.customer_profile:
            personalized = True
            logger.debug(f"Using customer context for personalization: {context.customer_profile.customer_id}")
            
            # Extract name from email as a simple personalization
            if '@' in context.customer_profile.email:
                customer_name = context.customer_profile.email.split('@')[0].replace('.', ' ').title()
            
            if context.customer_profile.type == "business":
                context_influence["business_account_factor"] = 0.8
            
            if context.customer_profile.tier in ["premier", "plus"]:
                context_influence["loyalty_tier_factor"] = 0.7
            
            if context.customer_profile.preferred_store_id:
                if "store" in msg_lower or "location" in msg_lower:
                    entities.append({
                        "type": "preferred_store", 
                        "value": context.customer_profile.preferred_store_id,
                        "confidence": 0.9,
                        "source": "customer_profile"
                    })
                    context_influence["preferred_store_factor"] = 0.9
        
        # Generate response based on selected agent
        agent_reasoning = "Keyword-based intent detection"
        response_message = ""
        
        # Timestamps for observability
        timestamps = {
            "intent": {
                "start": (datetime.now().timestamp() - 0.3),
                "end": (datetime.now().timestamp() - 0.25)
            },
            "entity": {
                "start": (datetime.now().timestamp() - 0.24),
                "end": (datetime.now().timestamp() - 0.18)
            },
            "agent": {
                "start": (datetime.now().timestamp() - 0.17),
                "end": (datetime.now().timestamp() - 0.1)
            },
            "response": {
                "start": (datetime.now().timestamp() - 0.09),
                "end": datetime.now().timestamp()
            }
        }
        
        if selected_agent == "store_locator":
            if personalized and context.customer_profile.preferred_store_id:
                response_message = f"Hi {customer_name}, I can help you find a Staples store. I see you have a preferred store already. The closest Staples to your preferred location is at 401 Park Drive, Boston, MA 02215. It's open from 8 AM to 9 PM Monday through Saturday, and 10 AM to 6 PM on Sunday. Would you like directions or information about another store?"
            else:
                response_message = "I found several Staples stores near you. The closest one is at 401 Park Drive, Boston, MA 02215. It's open from 8 AM to 9 PM Monday through Saturday, and 10 AM to 6 PM on Sunday. Would you like directions or information about another store?"
        
        elif selected_agent == "order_tracking":
            if personalized:
                response_message = f"Hi {customer_name}, I've found your recent orders. Your most recent order #ORD-987654 was delivered on April 1st, and you have another order #ORD-876543 that's currently processing. Which one would you like more information about?"
            else:
                response_message = "I can help you track your order. Could you provide your order number or the email address used for the purchase?"
        
        elif selected_agent == "password_reset":
            if personalized:
                response_message = f"Hi {customer_name}, I can help you reset your password. I'll need to send a verification code to your email address ending in {context.customer_profile.email.split('@')[1]}. Would you like me to do that now?"
            else:
                response_message = "I can help you reset your password. I'll need to send a verification code to the email address associated with your account. Could you provide your email address?"
        
        else:  # general_assistant
            if personalized:
                if context.customer_profile.type == "business":
                    response_message = f"Hello {customer_name}, welcome back to Staples Business Solutions. I'm here to help with your business needs. How can I assist you today with your {context.customer_profile.tier} business account?"
                else:
                    response_message = f"Hello {customer_name}, welcome back to Staples. I'm here to help with your {context.customer_profile.tier} account. How can I assist you today?"
            else:
                response_message = "I'm here to help with various Staples-related questions. I can assist with finding store locations, tracking orders, resetting passwords, and providing product information. How can I help you today?"
        
        logger.debug(f"Generated response using {selected_agent} agent")
        
        # Create observability data
        obs_data = {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "request": {
                "message": message,
                "conversation_id": conversation_id,
                "has_context": bool(context)
            },
            "processing": {
                "intent_detection": {
                    "intents": intents,
                    "selected_intent": selected_agent,
                    "context_influence": context_influence if context_influence else {}
                },
                "entity_extraction": {
                    "entities": entities
                },
                "agent_selection": {
                    "selected_agent": selected_agent,
                    "version": "1.0",
                    "reasoning": agent_reasoning,
                    "personalization_applied": personalized
                },
                "execution_graph": {
                    "nodes": ["intent", "entity", "agent", "response"],
                    "current_node": "response",
                    "execution_path": [
                        {
                            "node": "intent", 
                            "start_time": datetime.fromtimestamp(timestamps["intent"]["start"]).isoformat(),
                            "end_time": datetime.fromtimestamp(timestamps["intent"]["end"]).isoformat()
                        },
                        {
                            "node": "entity",
                            "start_time": datetime.fromtimestamp(timestamps["entity"]["start"]).isoformat(), 
                            "end_time": datetime.fromtimestamp(timestamps["entity"]["end"]).isoformat()
                        },
                        {
                            "node": "agent", 
                            "start_time": datetime.fromtimestamp(timestamps["agent"]["start"]).isoformat(),
                            "end_time": datetime.fromtimestamp(timestamps["agent"]["end"]).isoformat()
                        },
                        {
                            "node": "response", 
                            "start_time": datetime.fromtimestamp(timestamps["response"]["start"]).isoformat(),
                            "end_time": datetime.fromtimestamp(timestamps["response"]["end"]).isoformat()
                        }
                    ]
                }
            }
        }
        
        return {"message": response_message}, obs_data
    
    async def get_observability_data(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get observability data for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Observability data for the conversation
        """
        obs_data = self.observability_data.get(conversation_id)
        if not obs_data:
            logger.warning(f"Observability data not found for conversation: {conversation_id}")
            return {"error": "Observability data not found for this conversation"}
        
        return obs_data
    
    async def get_conversations(self) -> List[Dict[str, Any]]:
        """
        Get a list of all conversations.
        
        Returns:
            List of conversation summaries
        """
        result = []
        for conv_id, conv_data in self.conversations.items():
            # Get conversation title
            title = conv_data.get("title", "New Conversation")
            
            # Get creation timestamp
            timestamp = conv_data.get("created_at", datetime.now().isoformat())
            
            # Count message exchanges (user+assistant pairs)
            message_count = len(conv_data.get("messages", [])) // 2
            
            result.append({
                "id": conv_id,
                "title": title,
                "timestamp": timestamp,
                "message_count": message_count
            })
        
        # Sort by timestamp (newest first)
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return result
    
    async def get_conversation_history(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get the full history for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Conversation data including messages
        """
        conv_data = self.conversations.get(conversation_id)
        if not conv_data:
            logger.warning(f"Conversation not found: {conversation_id}")
            return {"error": "Conversation not found"}
        
        return conv_data