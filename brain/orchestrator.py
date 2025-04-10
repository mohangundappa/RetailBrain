import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import re
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from utils.memory import ConversationMemory
from config.agent_constants import (
    INTENT_AGENT_MAPPING,
    DEFAULT_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    CONTINUITY_BONUS
)

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
        self.confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD
        self.fallback_threshold = DEFAULT_CONFIDENCE_THRESHOLD * 0.7  # 70% of default threshold 
        self.continuity_bonus = CONTINUITY_BONUS
        self.recency_window = 300       # Consider context from the last 5 minutes (in seconds)
        
        # Use intent to agent mapping from central constants
        self.intent_routing = INTENT_AGENT_MAPPING
        
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
                        # Use direct SQL query with proper SQLAlchemy formatting
                        from app import db
                        from sqlalchemy import text
                        result = db.session.execute(text("SELECT id, name, description FROM custom_agent WHERE is_active = TRUE AND wizard_completed = TRUE")).fetchall()
                        
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
                
                # Build a concise response text including all available services
                response_text = "Hi! I can help with:\n\n"
                response_text += "• Package tracking\n"
                response_text += "• Password reset\n"
                response_text += "• Store locations\n"
                response_text += "• Product info"
                
                # Add custom agent capabilities if any exist
                if custom_agents:
                    custom_agents_list = [f"{agent.name}" for agent in custom_agents]
                    response_text += "\n• " + ", ".join(custom_agents_list)
                
                response_text += "\n\nWhat do you need help with?"
                
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
            
            # Check if this is a closing response (thank you, etc.)
            if response.get('is_closing', False):
                logger.info(f"Agent {best_agent.name} has issued a closing response. Ending conversation.")
                memory.update_working_memory('conversation_ended', True)
                memory.update_working_memory('continue_with_same_agent', False)
                # Add a flag to indicate this was a closing message
                response['conversation_ended'] = True
            
            return response
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "Error processing request. Please try again with different wording."
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
            
            # For a simple greeting, don't select a specific agent
            # Instead, present all options
            logger.info("Received a simple greeting, presenting all agent options")
            
            # Return None with very low confidence to trigger the welcome message
            return None, 0.0, False
        
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
        
        if intent and intent_confidence > HIGH_CONFIDENCE_THRESHOLD and intent in self.intent_routing:
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
            if last_agent_name and continue_with_same_agent:
                logger.info(f"continue_with_same_agent flag is set to True for agent: {last_agent_name}")
                # If the flag was specifically set in the context by an agent, prioritize continuity strongly
                # This is especially important for maintaining context during entity collection
                for agent in self.agents:
                    if agent.name == last_agent_name:
                        # Get base confidence from the current agent
                        current_agent_confidence = agent.can_handle(user_input, context)
                        
                        # Check if there's a topic change by comparing with other agents
                        topic_change = self._detect_topic_change(user_input, agent, context)
                        
                        if topic_change:
                            # If topic changed, don't apply continuity bonus - let normal routing work
                            logger.info(f"Detected topic change - not applying continuity bonus")
                            # Reset the continue_with_same_agent flag
                            memory.update_working_memory('continue_with_same_agent', False)
                            # Just use normal routing algorithm
                            break
                        else:
                            # Only if staying on the same topic, apply continuity bonus
                            confidence = max(0.5, current_agent_confidence)  # Reduced from 0.6
                            adjusted_confidence = min(0.95, confidence + CONTINUITY_BONUS)  # Reduced bonus (removed *2)
                            
                            logger.info(f"Prioritizing continuity with agent: {agent.name} "
                                      f"(base confidence: {confidence:.2f}, "
                                      f"with continuity bonus: {adjusted_confidence:.2f})")
                            
                            # Reset the continue_with_same_agent flag unless explicitly set again by the agent
                            memory.update_working_memory('continue_with_same_agent', False)
                            
                            return agent, adjusted_confidence, True
            
            # Fall back to standard time-based continuity if explicit flag not set
            elif last_agent_name and last_timestamp_str:
                try:
                    last_timestamp = datetime.fromisoformat(last_timestamp_str)
                    # Only consider recent conversations (within last 5 minutes)
                    if datetime.now() - last_timestamp < timedelta(seconds=self.recency_window):
                        for agent in self.agents:
                            if agent.name == last_agent_name:
                                # Check if the current agent still has some confidence in handling the new input
                                current_agent_confidence = agent.can_handle(user_input, context)
                                
                                # Check if there's a topic change by comparing with other agents
                                topic_change = self._detect_topic_change(user_input, agent, context)
                                
                                if topic_change:
                                    # If topic changed, don't apply continuity bonus - let normal routing work
                                    logger.info(f"Detected topic change in time-based continuity - not applying bonus")
                                    # Just use normal routing algorithm
                                    break
                                else:
                                    # Apply continuity bonus for the same agent if topic hasn't changed
                                    adjusted_confidence = current_agent_confidence + self.continuity_bonus * 0.5  # Reduced bonus
                                    
                                    if adjusted_confidence > self.fallback_threshold:
                                        logger.info(f"Continuing with same agent: {agent.name} "
                                                f"(base confidence: {current_agent_confidence:.2f}, "
                                                f"with reduced continuity bonus: {adjusted_confidence:.2f})")
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
            
            # Check if we have a tie or very close scores at the top
            if len(agent_scores) >= 2:
                top_agent, top_confidence, top_base, top_used_context = agent_scores[0]
                second_agent, second_confidence, second_base, second_used_context = agent_scores[1]
                
                # If the top two scores are very close (within 0.1) and one is the Store Locator
                # and the input contains location patterns, prioritize the Store Locator
                if abs(top_confidence - second_confidence) <= 0.1:
                    logger.info(f"Close agent scores: {top_agent.name} ({top_confidence:.2f}) vs {second_agent.name} ({second_confidence:.2f})")
                    
                    # Check for city names, zip codes or location-related keywords
                    location_keywords = ["store", "location", "find", "nearest", "close", "near me", "nearby", "directions"]
                    location_pattern = re.search(r'\b\d{5}(-\d{4})?\b', user_input) # Zip code
                    has_location_keyword = any(kw in user_input.lower() for kw in location_keywords)
                    
                    city_names = ["natick", "boston", "new york", "chicago", "philadelphia", "los angeles", "san francisco"]
                    has_city_name = any(city in user_input.lower() for city in city_names)
                    
                    # If input has location indicators, prioritize Store Locator
                    if (location_pattern or has_location_keyword or has_city_name):
                        if top_agent.name == "Store Locator Agent":
                            # Store Locator already on top, just increase confidence slightly
                            best_agent = top_agent
                            best_adjusted_confidence = min(top_confidence + 0.05, 0.99)
                            context_used = top_used_context
                            logger.info(f"Prioritizing Store Locator Agent for location-related query")
                        elif second_agent.name == "Store Locator Agent":
                            # Promote Store Locator to the top for location queries
                            best_agent = second_agent
                            best_adjusted_confidence = min(second_confidence + 0.1, 0.99)
                            context_used = second_used_context
                            logger.info(f"Promoting Store Locator Agent for location-related query")
                        else:
                            # No Store Locator in top 2, proceed with highest score
                            best_agent, best_adjusted_confidence, base_confidence, used_context = agent_scores[0]
                            context_used = used_context
                    else:
                        # No location indicators, use highest confidence
                        best_agent, best_adjusted_confidence, base_confidence, used_context = agent_scores[0]
                        context_used = used_context
                else:
                    # Clear winner, use highest confidence
                    best_agent, best_adjusted_confidence, base_confidence, used_context = agent_scores[0]
                    context_used = used_context
            else:
                # Only one agent, use it
                best_agent, best_adjusted_confidence, base_confidence, used_context = agent_scores[0]
                context_used = used_context
            
            if best_adjusted_confidence >= self.confidence_threshold:
                return best_agent, best_adjusted_confidence, context_used
        
        # No agent reached the confidence threshold
        logger.warning(f"No agent reached the confidence threshold ({self.confidence_threshold:.2f})")
        return None, 0.0, False
    
    def _detect_topic_change(self, user_input: str, current_agent: BaseAgent, context: Dict[str, Any] = None) -> bool:
        """
        Detect if there's a topic change in the conversation that should trigger agent switching.
        
        Args:
            user_input: The user's request or query
            current_agent: The current agent handling the conversation
            context: Additional context information
            
        Returns:
            True if a topic change is detected, False otherwise
        """
        # If the user input is very short, it's likely a clarification or simple response, not a topic change
        if len(user_input.split()) <= 2:
            return False
            
        # Get confidence score from current agent
        current_agent_confidence = current_agent.can_handle(user_input, context)
        
        # Check if any other agent has significantly higher confidence
        for agent in self.agents:
            # Skip the current agent
            if agent.name == current_agent.name:
                continue
                
            try:
                # Get confidence from this agent
                other_agent_confidence = agent.can_handle(user_input, context)
                
                # Compare confidence levels
                confidence_diff = other_agent_confidence - current_agent_confidence
                
                # If another agent has significantly higher confidence, it's a topic change
                if confidence_diff > 0.3:  # Threshold for topic change detection
                    logger.info(f"Topic change detected: {current_agent.name} ({current_agent_confidence:.2f}) -> "
                              f"{agent.name} ({other_agent_confidence:.2f}), diff: {confidence_diff:.2f}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error comparing confidence with agent '{agent.name}': {str(e)}")
                
        # Look for intent change if intent classification is available
        if context and 'intent' in context:
            current_intent = context.get('intent')
            if current_intent:
                # Check if the intent maps to current agent
                if current_intent in self.intent_routing:
                    mapped_agent = self.intent_routing[current_intent]
                    if mapped_agent.lower() != current_agent.name.lower():
                        logger.info(f"Intent change detected: intent '{current_intent}' maps to {mapped_agent}, "
                                  f"not current agent {current_agent.name}")
                        return True
                        
        # Check for specific agent keywords
        if current_agent.name == "Reset Password Agent" and any(kw in user_input.lower() for kw in 
                                                          ['store', 'location', 'nearby', 'closest']):
            logger.info("Topic change detected through keywords: Reset Password -> Store Locator")
            return True
            
        if current_agent.name == "Package Tracking Agent" and any(kw in user_input.lower() for kw in 
                                                           ['password', 'login', 'account', 'sign in']):
            logger.info("Topic change detected through keywords: Package Tracking -> Reset Password")
            return True
            
        if current_agent.name == "Store Locator Agent" and any(kw in user_input.lower() for kw in 
                                                        ['order', 'tracking', 'package', 'shipped']):
            logger.info("Topic change detected through keywords: Store Locator -> Package Tracking")
            return True
                
        # No clear topic change detected
        return False
    
    def get_routing_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the agent routing history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of routing decisions for the session
        """
        return self.agent_routing_history.get(session_id, [])
