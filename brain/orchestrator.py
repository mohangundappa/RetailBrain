import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import re
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from utils.memory import ConversationMemory

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates multiple agents to handle user requests.
    
    This class determines which agent is best suited to handle a specific user request
    and routes the request accordingly. It maintains conversation memory and context
    between agent interactions.
    """
    
    def __init__(self, agents: List[BaseAgent]):
        """
        Initialize the orchestrator with a list of agents.
        
        Args:
            agents: List of agent instances to orchestrate
        """
        self.agents = agents
        self.memories = {}  # Dictionary of session_id -> ConversationMemory
        self.agent_routing_history = {}  # Track routing history per session
        self.confidence_threshold = 0.3  # Minimum confidence to select an agent
        self.fallback_threshold = 0.2   # Fallback threshold for continuing with same agent
        self.continuity_bonus = 0.15    # Bonus for same agent continuity
        self.recency_window = 300       # Consider context from the last 5 minutes (in seconds)
        
        # Mapping of intents to preferred agents
        self.intent_routing = {
            "package_tracking": "Package Tracking Agent",
            "order_status": "Package Tracking Agent",
            "shipping_inquiry": "Package Tracking Agent",
            "delivery_status": "Package Tracking Agent",
            "package_location": "Package Tracking Agent",
            "password_reset": "Reset Password Agent",
            "account_access": "Reset Password Agent",
            "login_issue": "Reset Password Agent",
            "forgot_password": "Reset Password Agent"
        }
        
        logger.info(f"Initialized orchestrator with {len(agents)} agents")
    
    def _get_memory(self, session_id: str) -> ConversationMemory:
        """
        Get or create a conversation memory for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The conversation memory instance
        """
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory(session_id)
            self.agent_routing_history[session_id] = []
        return self.memories[session_id]
    
    def _record_agent_selection(self, session_id: str, agent_name: str, 
                             confidence: float, intent: str = None,
                             context_used: bool = False) -> None:
        """
        Record which agent was selected for a given request.
        
        Args:
            session_id: The user's session ID
            agent_name: The name of the selected agent
            confidence: The confidence score for this selection
            intent: The detected intent (if any)
            context_used: Whether context contributed to this selection
        """
        if session_id not in self.agent_routing_history:
            self.agent_routing_history[session_id] = []
            
        self.agent_routing_history[session_id].append({
            "agent": agent_name,
            "confidence": confidence,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "context_used": context_used
        })
        
        # Trim history to last 20 entries
        if len(self.agent_routing_history[session_id]) > 20:
            self.agent_routing_history[session_id].pop(0)
            
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request by selecting the most appropriate agent.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            Response from the most appropriate agent
        """
        if not context:
            context = {}
            
        logger.debug(f"Orchestrator processing request: {user_input}")
        request_start_time = datetime.now()
        
        try:
            # Get session ID from context, default to 'default' if not present
            session_id = context.get('session_id', 'default')
            
            # Get or create memory for this session
            memory = self._get_memory(session_id)
            
            # Add memory to context for agents to use
            context['conversation_memory'] = memory
            
            # Add request metadata to context
            intent = context.get('intent')
            intent_confidence = context.get('intent_confidence', 0.0)
            
            # Update working memory with user input and metadata
            memory.update_working_memory('last_user_input', user_input)
            memory.update_working_memory('timestamp', datetime.now().isoformat())
            memory.update_working_memory('intent', intent)
            memory.update_working_memory('intent_confidence', intent_confidence)
            
            # Check for context continuation flag
            continue_conversation = context.get('continue_conversation', False)
            if continue_conversation:
                memory.update_working_memory('continue_with_same_agent', True)
            
            # Extract entities from context if available
            if 'entities' in context and context['entities']:
                memory.update_working_memory('entities', context['entities'])
                # Add specific entities to memory for easier access
                for entity_type, value in context['entities'].items():
                    if value:  # Only store non-empty values
                        memory.update_working_memory(f'entity_{entity_type}', value)
            
            # Determine which agent can best handle this request
            best_agent, confidence, context_used = self._select_agent(user_input, context)
            
            if best_agent is None:
                logger.warning("No suitable agent found to handle the request")
                
                # Get any custom agents from the database
                custom_agents = []
                try:
                    # This import is inside the try block to avoid circular imports
                    from models import CustomAgent
                    from flask import current_app
                    
                    # Check if we're in an application context
                    if current_app:
                        # Use direct SQL query to ensure it works
                        from db import db
                        result = db.session.execute("SELECT id, name, description FROM custom_agent WHERE is_active = TRUE AND wizard_completed = TRUE").fetchall()
                        
                        # Convert the raw SQL results to a format we can use
                        for row in result:
                            custom_agent = type('CustomAgent', (object,), {
                                'id': row[0],
                                'name': row[1],
                                'description': row[2]
                            })
                            custom_agents.append(custom_agent)
                        
                        logger.info(f"Found {len(custom_agents)} custom agents in the database")
                except Exception as e:
                    logger.warning(f"Could not fetch custom agents: {str(e)}")
                    # Print the full stack trace for debugging
                    import traceback
                    logger.warning(traceback.format_exc())
                
                # Create the default suggested actions for built-in agents
                suggested_actions = [
                    {"id": "package-tracking", "name": "Track my package", "description": "Check the status of your order or package"},
                    {"id": "reset-password", "name": "Reset my password", "description": "Get help with account access or password reset"},
                    {"id": "store-locator", "name": "Find a store", "description": "Locate Staples stores near you"},
                    {"id": "product-info", "name": "Product information", "description": "Get details about Staples products"}
                ]
                
                # Add custom agents to the suggested actions
                for agent in custom_agents:
                    suggested_actions.append({
                        "id": f"custom-{agent.id}", 
                        "name": agent.name,
                        "description": agent.description or f"Custom agent: {agent.name}"
                    })
                
                # Build the response text including custom agents if available
                response_text = "Hello! I'm Staples Brain, here to assist you with various Staples-related services. I can help you with:\n\n" + \
                              "• Tracking your packages and orders\n" + \
                              "• Resetting your password or account access\n" + \
                              "• Finding Staples stores near you\n" + \
                              "• Getting information about Staples products"
                
                # Add custom agent capabilities if any exist
                if custom_agents:
                    response_text += "\n• Working with custom agents: "
                    response_text += ", ".join([agent.name for agent in custom_agents])
                
                response_text += "\n\nHow can I assist you today?"
                
                # Create a more friendly response with suggestions including custom agents
                return {
                    "success": True,  # Not treating this as an error, just a redirection
                    "intent": "welcome",  # Mark this as a welcome/introduction 
                    "response": response_text,
                    "suggested_actions": suggested_actions,
                    "agent": None  # Explicitly show there's no agent selected yet
                }
            
            logger.info(f"Selected agent '{best_agent.name}' with confidence {confidence:.2f}")
            
            # Record the agent selection
            self._record_agent_selection(
                session_id=session_id,
                agent_name=best_agent.name,
                confidence=confidence,
                intent=intent,
                context_used=context_used
            )
            
            # Update memory with agent selection
            memory.update_working_memory('last_selected_agent', best_agent.name)
            memory.update_working_memory('last_confidence', confidence)
            memory.update_working_memory('last_intent', intent)
            
            # Process the request with the selected agent
            response = await best_agent.process(user_input, context)
            
            # Calculate processing time
            processing_time = (datetime.now() - request_start_time).total_seconds()
            
            # Add orchestrator metadata to response
            response.update({
                "selected_agent": best_agent.name,
                "confidence": confidence,
                "intent": intent,
                "intent_confidence": intent_confidence,
                "processing_time": processing_time,
                "context_used": context_used
            })
            
            # Extract and store any entities that the agent may have identified
            if 'extracted_entities' in response:
                memory.update_working_memory('extracted_entities', response['extracted_entities'])
            
            # Store conversation continuity flag for next interaction
            memory.update_working_memory('continue_with_same_agent', 
                                        response.get('continue_with_same_agent', False))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error while processing your request. Please try again or rephrase your question."
            }
    
    def _select_agent(self, user_input: str, context: Dict[str, Any] = None) -> Tuple[BaseAgent, float, bool]:
        """
        Select the most appropriate agent to handle a user request.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A tuple containing (best_agent, confidence_score, context_used)
        """
        if not self.agents:
            logger.warning("No agents available to select from")
            return None, 0.0, False
        
        best_agent = None
        best_confidence = 0.0
        context_used = False
        
        # 0. Check for generic greetings and welcome messages
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', r'^howdy\b',
            r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
            r'^how are you\b', r'^what\'s up\b', r'^welcome\b', r'^hola\b'
        ]
        
        # Calculate the length of the user input (in terms of words)
        # Short inputs are more likely to be greetings
        word_count = len(user_input.split())
        
        # Check if the input appears to be a greeting
        is_greeting = False
        for pattern in greeting_patterns:
            if re.search(pattern, user_input.lower()):
                is_greeting = True
                break
                
        # If it's a short greeting with no specific request, return our custom welcome agent
        if is_greeting and word_count <= 5:
            # Check if we have a previous agent in context - if so, continue that conversation
            if (context and 'conversation_memory' in context):
                memory = context['conversation_memory']
                last_agent_name = memory.get_working_memory('last_selected_agent')
                
                if last_agent_name:
                    for agent in self.agents:
                        if agent.name == last_agent_name:
                            logger.info(f"Responding to greeting for an ongoing conversation with agent: {agent.name}")
                            return agent, 0.8, True
            
            # Return the most appropriate agent for handling generic welcome messages
            # We'll choose the agent dynamically based on the client's role
            for agent in self.agents:
                if agent.name == "Store Locator Agent":  # This agent handles general inquiries best
                    logger.info("Responding to welcome greeting with the Store Locator Agent")
                    return agent, 0.9, False
        
        # 1. Check if a specific agent is explicitly requested
        if context and "agent_name" in context:
            requested_agent_name = context["agent_name"].lower()
            for agent in self.agents:
                if agent.name.lower() == requested_agent_name:
                    logger.info(f"Using explicitly requested agent: {agent.name}")
                    return agent, 1.0, True
        
        # 2. Check if there's an intent-based routing possibility
        intent = context.get('intent') if context else None
        intent_confidence = context.get('intent_confidence', 0.0) if context else 0.0
        
        if intent and intent_confidence > 0.6 and intent in self.intent_routing:
            preferred_agent_name = self.intent_routing[intent]
            for agent in self.agents:
                if agent.name.lower() == preferred_agent_name.lower():
                    # Still check if the agent can handle it
                    confidence = agent.can_handle(user_input, context)
                    logger.info(f"Using intent-based routing for '{intent}' to agent: {agent.name} (confidence: {confidence:.2f})")
                    if confidence >= self.confidence_threshold:
                        return agent, confidence, True
        
        # 3. Check if we should continue with the same agent from recent interaction
        if (context and 'conversation_memory' in context):
            memory = context['conversation_memory']
            continue_with_same_agent = memory.get_working_memory('continue_with_same_agent', False)
            last_agent_name = memory.get_working_memory('last_selected_agent')
            last_timestamp_str = memory.get_working_memory('timestamp')
            
            # Check if we have a recent conversation to continue
            if last_agent_name and continue_with_same_agent and last_timestamp_str:
                try:
                    last_timestamp = datetime.fromisoformat(last_timestamp_str)
                    # Only consider recent conversations (within last 5 minutes)
                    if datetime.now() - last_timestamp < timedelta(seconds=self.recency_window):
                        for agent in self.agents:
                            if agent.name == last_agent_name:
                                # Check if this agent still has some confidence in handling the new input
                                confidence = agent.can_handle(user_input, context)
                                # Apply continuity bonus for the same agent
                                adjusted_confidence = confidence + self.continuity_bonus
                                
                                if adjusted_confidence > self.fallback_threshold:
                                    logger.info(f"Continuing with same agent: {agent.name} "
                                            f"(base confidence: {confidence:.2f}, "
                                            f"with continuity bonus: {adjusted_confidence:.2f})")
                                    return agent, adjusted_confidence, True
                except (ValueError, TypeError):
                    # If timestamp parsing fails, continue with normal agent selection
                    pass
        
        # 4. Check conversation context for relevant entities
        entities = {}
        if context and 'conversation_memory' in context:
            memory = context['conversation_memory']
            # Check for context entities from previous interactions
            stored_entities = memory.get_working_memory('entities', {})
            if stored_entities and isinstance(stored_entities, dict):
                entities.update(stored_entities)
            
            # Add entities from current request if available
            if context.get('entities'):
                entities.update(context['entities'])
        
        # 5. Standard confidence-based routing with context boost
        agent_scores = []
        for agent in self.agents:
            try:
                # Get base confidence from agent
                confidence = agent.can_handle(user_input, context)
                
                # Apply context-based boosts if applicable
                boost = 0.0
                
                # Look for intent-agent alignment (smaller boost than direct routing)
                if intent in self.intent_routing and self.intent_routing[intent].lower() == agent.name.lower():
                    boost += 0.1
                    context_used = True
                
                # Check if we have relevant entities for this agent
                if agent.name == "Package Tracking Agent" and any(entity in entities for entity in 
                                                        ['tracking_number', 'order_number', 'shipping_carrier']):
                    boost += 0.15
                    context_used = True
                elif agent.name == "Reset Password Agent" and any(entity in entities for entity in 
                                                           ['email', 'username', 'account_type']):
                    boost += 0.15
                    context_used = True
                    
                # Apply the boost and record the score
                adjusted_confidence = min(confidence + boost, 1.0)  # Cap at 1.0
                
                logger.debug(f"Agent '{agent.name}' base confidence: {confidence:.2f}, "
                           f"with context boost: {adjusted_confidence:.2f}")
                
                agent_scores.append((agent, adjusted_confidence, confidence, boost > 0))
                
            except Exception as e:
                logger.error(f"Error getting confidence from agent '{agent.name}': {str(e)}")
        
        # Select the agent with the highest adjusted confidence
        if agent_scores:
            agent_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by adjusted confidence
            best_agent, best_adjusted_confidence, base_confidence, used_context = agent_scores[0]
            
            if best_adjusted_confidence >= self.confidence_threshold:
                context_used = used_context
                return best_agent, best_adjusted_confidence, context_used
        
        # No agent reached the confidence threshold
        logger.warning(f"No agent reached the confidence threshold ({self.confidence_threshold:.2f})")
        return None, 0.0, False
    
    def get_routing_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the agent routing history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of routing decisions for the session
        """
        return self.agent_routing_history.get(session_id, [])
