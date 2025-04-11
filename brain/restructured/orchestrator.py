"""
Agent orchestration for the Staples Brain system.
This module provides the core orchestration logic for selecting and routing to agents.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from brain.restructured.config import OrchestratorConfig, IntentMappingConfig
from brain.restructured.memory import OrchestrationMemory
from brain.restructured.confidence import ConfidenceScorer
from brain.restructured.registry import AgentRegistry
from brain.restructured.topic_detection import TopicChangeDetector, create_default_topic_detector
from brain.restructured.logging_utils import OrchestrationLogger
from brain.restructured.telemetry import collector as telemetry_collector

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates agent selection and request processing.
    
    This class determines which agent is best suited to handle a specific user request
    and routes the request accordingly. It uses confidence scoring, context preservation,
    and conversation continuity to provide a seamless user experience.
    """
    
    def __init__(self,
                agent_registry: AgentRegistry,
                config: Optional[OrchestratorConfig] = None,
                intent_mapping: Optional[IntentMappingConfig] = None,
                topic_detector: Optional[TopicChangeDetector] = None,
                logger: Optional[OrchestrationLogger] = None):
        """
        Initialize the orchestrator with the necessary components.
        
        Args:
            agent_registry: Registry of available agents
            config: Orchestrator configuration (or defaults if None)
            intent_mapping: Intent to agent mapping (or empty if None)
            topic_detector: Topic change detector (or default if None)
            logger: Enhanced logger (or default if None)
        """
        self.registry = agent_registry
        self.config = config or OrchestratorConfig()
        self.intent_mapping = intent_mapping or IntentMappingConfig({})
        self.logger = logger or OrchestrationLogger()
        
        # Initialize confidence scorer with config
        self.scorer = ConfidenceScorer(
            confidence_threshold=self.config.confidence_threshold,
            high_confidence=self.config.high_confidence_threshold,
            continuity_bonus=self.config.continuity_bonus
        )
        
        # Initialize topic detector if none provided
        self.topic_detector = topic_detector or create_default_topic_detector(
            self.intent_mapping.intent_mapping
        )
        
        # Initialize memory storage
        self.memories = {}  # session_id -> OrchestrationMemory
        
        agents_count = len(self.registry.get_all())
        logger.info(f"Initialized orchestrator with {agents_count} agents")
        
    def _get_memory(self, session_id: str) -> OrchestrationMemory:
        """
        Get or create memory for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Memory instance for this session
        """
        if session_id not in self.memories:
            self.memories[session_id] = OrchestrationMemory(
                session_id=session_id,
                max_history=self.config.max_history
            )
        return self.memories[session_id]
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request by selecting and routing to the most appropriate agent.
        
        Args:
            user_input: User's request or query
            context: Additional context information
            
        Returns:
            Response from the selected agent
        """
        if not context:
            context = {}
            
        # Start timing the processing
        request_start_time = datetime.now()
        
        try:
            # Get session ID from context
            session_id = context.get('session_id', 'default')
            self.logger.log_request(user_input, session_id)
            
            # Track request in telemetry
            request_event_id = telemetry_collector.track_request_received(session_id, user_input)
            
            # Get or create memory for this session
            memory = self._get_memory(session_id)
            
            # Update memory with this request
            memory.update_working_memory('last_user_input', user_input)
            memory.update_working_memory('timestamp', datetime.now().isoformat())
            
            # Update memory with intent if available
            intent = context.get('intent')
            intent_confidence = context.get('intent_confidence', 0.0)
            if intent:
                memory.update_working_memory('intent', intent)
                memory.update_working_memory('intent_confidence', intent_confidence)
                
                # Log the identified intent
                self.logger.log_intent(intent, intent_confidence, user_input)
            
            # Add memory and intent mapping to context for agent selection
            enriched_context = dict(context)
            enriched_context['memory'] = memory
            enriched_context['intent_mapping'] = self.intent_mapping.intent_mapping
            
            # Extract entities from context if available
            if 'entities' in context and context['entities']:
                memory.add_entities(context['entities'])
            
            # Check for out-of-scope queries
            # Note: In a real implementation, out-of-scope detection would be more sophisticated
            is_out_of_scope, topic_category = self._check_out_of_scope(user_input, enriched_context)
            
            if is_out_of_scope:
                return self._handle_out_of_scope(topic_category)
            
            # Select the most appropriate agent
            agent, confidence, context_used = self._select_agent(user_input, enriched_context)
            
            if agent is None:
                self.logger.log_no_suitable_agent(user_input)
                return self._handle_no_agent_found()
            
            # Record the agent selection
            memory.record_agent_selection(
                agent_name=agent.name,
                confidence=confidence,
                intent=intent,
                context_used=context_used
            )
            
            # Log the selected agent
            self.logger.log_agent_selection(agent.name, confidence, context_used, intent)
            
            # Process the request with the selected agent
            response = await agent.process(user_input, enriched_context)
            
            # Update memory with conversation continuity flag if present
            if 'continue_with_same_agent' in response:
                memory.mark_continue_with_same_agent(response['continue_with_same_agent'])
            
            # Calculate processing time
            processing_time = (datetime.now() - request_start_time).total_seconds()
            
            # Add orchestrator metadata to response
            response.update({
                "selected_agent": agent.name,
                "confidence": confidence,
                "intent": intent,
                "intent_confidence": intent_confidence,
                "processing_time": processing_time,
                "context_used": context_used
            })
            
            # Extract and store any entities that the agent may have identified
            if 'extracted_entities' in response:
                memory.add_entities(response['extracted_entities'])
            
            # Check if this is a closing response
            if response.get('is_closing', False):
                logger.info(f"Agent {agent.name} has issued a closing response. Ending conversation.")
                memory.update_working_memory('conversation_ended', True)
                memory.mark_continue_with_same_agent(False)
                response['conversation_ended'] = True
            
            # Track response generation in telemetry
            telemetry_collector.track_response_generation(
                session_id,
                agent.name,
                True,
                response.get('is_closing', False) and 'closing' or 'standard',
                processing_time,
                request_event_id
            )
            
            return response
            
        except Exception as e:
            # Get session ID for telemetry
            session_id = context.get('session_id', 'default')
            
            # Log the error
            self.logger.log_error(e, context)
            
            # Track error in telemetry
            telemetry_collector.track_error(
                session_id,
                "process_request_error",
                f"Error processing request: {str(e)}",
                False,
                request_event_id
            )
            
            return {
                "success": False,
                "error": str(e),
                "response": "Error processing request. Please try again with different wording."
            }
    
    def _select_agent(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Select the most appropriate agent using a multi-step approach.
        
        Args:
            user_input: User's request or query
            context: Context information including memory
            
        Returns:
            Tuple of (selected_agent, confidence_score, context_used)
        """
        # Get session ID from context for telemetry
        session_id = context.get('session_id', 'default')
        
        # Get all registered agents
        agents = self.registry.get_all()
        
        if not agents:
            logger.warning("No agents available to select from")
            # Track the error in telemetry
            telemetry_collector.track_error(session_id, "no_agents", "No agents available to select from")
            return None, 0.0, False
        
        # Extract memory from context
        memory = context.get('memory')
        
        # 1. Check for simple greetings or special cases
        special_cases_event_id = telemetry_collector.track_special_case_check(session_id, False)
        agent, confidence, context_used = self._check_special_cases(user_input, context)
        if agent is not None:
            # Update telemetry for special case
            telemetry_collector.track_special_case_check(
                session_id, 
                True, 
                "greeting" if self._is_simple_greeting(user_input)[0] else "explicit_agent", 
                special_cases_event_id
            )
            # Track agent selection
            telemetry_collector.track_agent_selection(
                session_id, 
                agent.name if agent else None, 
                confidence,
                "special_case"
            )
            return agent, confidence, context_used
        
        # 2. Try intent-based routing for high-confidence intents
        intent = context.get('intent')
        intent_event_id = None
        if intent:
            intent_event_id = telemetry_collector.track_intent_identification(
                session_id,
                intent,
                context.get('intent_confidence', 0.0)
            )
        
        intent_routing_event_id = telemetry_collector.track_intent_routing(
            session_id, 
            intent or "unknown",
            None,
            False
        )
        
        agent, confidence, context_used = self._try_intent_routing(user_input, context)
        if agent is not None:
            # Update telemetry for successful intent routing
            telemetry_collector.track_intent_routing(
                session_id,
                intent,
                agent.name,
                True,
                intent_routing_event_id
            )
            # Track agent selection
            telemetry_collector.track_agent_selection(
                session_id, 
                agent.name, 
                confidence,
                "intent_routing"
            )
            return agent, confidence, context_used
        
        # 3. Check for conversation continuity
        continuity_event_id = None
        if memory:
            last_agent = memory.get_working_memory('last_selected_agent')
            continuity_event_id = telemetry_collector.track_continuity_check(
                session_id,
                last_agent,
                False,
                False
            )
            
            agent, confidence, context_used = self._try_conversation_continuity(user_input, context)
            if agent is not None:
                # Update telemetry for continuity
                telemetry_collector.track_continuity_check(
                    session_id,
                    agent.name,
                    True,
                    True,
                    "explicit_flag" if memory.should_continue_with_same_agent() else "recent_interaction",
                    continuity_event_id
                )
                # Track agent selection
                telemetry_collector.track_agent_selection(
                    session_id, 
                    agent.name, 
                    confidence,
                    "conversation_continuity"
                )
                return agent, confidence, context_used
        
        # 4. Standard confidence-based selection with context boosts
        agent, confidence, context_used = self._evaluate_all_agents(user_input, context)
        
        # Track final agent selection
        if agent:
            telemetry_collector.track_agent_selection(
                session_id, 
                agent.name, 
                confidence,
                "confidence_scoring"
            )
        else:
            telemetry_collector.track_agent_selection(
                session_id, 
                None, 
                0.0,
                "no_agent_found"
            )
            
        return agent, confidence, context_used
    
    def _check_special_cases(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Check for special cases like greetings or explicit agent requests.
        
        Args:
            user_input: User's request or query
            context: Context information
            
        Returns:
            Tuple of (agent, confidence, context_used) or (None, 0.0, False)
        """
        # Check for explicit agent request in the context
        if "agent_name" in context:
            requested_agent_name = context["agent_name"]
            agent = self.registry.get_by_name(requested_agent_name)
            if agent:
                logger.info(f"Using explicitly requested agent: {agent.name}")
                return agent, 1.0, True
        
        # Check for simple greetings
        is_greeting, word_count = self._is_simple_greeting(user_input)
        if is_greeting and word_count <= 5:
            # For a simple greeting with an ongoing conversation, continue with same agent
            memory = context.get('memory')
            if memory:
                last_agent_name = memory.get_working_memory('last_selected_agent')
                if last_agent_name:
                    agent = self.registry.get_by_name(last_agent_name)
                    if agent:
                        logger.info(f"Responding to greeting for an ongoing conversation with agent: {agent.name}")
                        return agent, 0.8, True
            
            # For a simple greeting without context, don't select an agent
            logger.info("Received a simple greeting, will present all agent options")
            return None, 0.0, False
        
        return None, 0.0, False
    
    def _is_simple_greeting(self, user_input: str) -> Tuple[bool, int]:
        """
        Check if a user input is a simple greeting.
        
        Args:
            user_input: User's request or query
            
        Returns:
            Tuple of (is_greeting, word_count)
        """
        import re
        
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', r'^howdy\b',
            r'^good morning\b', r'^good afternoon\b', r'^good evening\b',
            r'^how are you\b', r'^what\'s up\b', r'^welcome\b', r'^hola\b'
        ]
        
        # Calculate word count
        word_count = len(user_input.split())
        
        # Check for greeting patterns
        for pattern in greeting_patterns:
            if re.search(pattern, user_input.lower()):
                return True, word_count
        
        return False, word_count
    
    def _try_intent_routing(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Try to route based on intent classification.
        
        Args:
            user_input: User's request or query
            context: Context information
            
        Returns:
            Tuple of (agent, confidence, context_used) or (None, 0.0, False)
        """
        intent = context.get('intent')
        intent_confidence = context.get('intent_confidence', 0.0) 
        
        # Only use intent routing for high-confidence intents
        if intent and intent_confidence > self.config.high_confidence_threshold:
            # Get the preferred agent for this intent
            agent_name = self.intent_mapping.get_agent_for_intent(intent)
            if agent_name:
                agent = self.registry.get_by_name(agent_name)
                if agent:
                    # Double-check if the agent can handle this input
                    confidence = agent.can_handle(user_input, context)
                    logger.info(f"Intent-based routing for '{intent}' to agent: {agent.name} "
                              f"(confidence: {confidence:.2f})")
                    
                    # Only use if confidence is still reasonable
                    if confidence >= self.config.confidence_threshold:
                        return agent, confidence, True
        
        return None, 0.0, False
    
    def _try_conversation_continuity(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Try to continue the conversation with the same agent if appropriate.
        
        Args:
            user_input: User's request or query
            context: Context information including memory
            
        Returns:
            Tuple of (agent, confidence, context_used) or (None, 0.0, False)
        """
        memory = context.get('memory')
        if not memory:
            return None, 0.0, False
        
        # Check if we should continue with the same agent
        continue_with_same_agent = memory.should_continue_with_same_agent()
        last_agent_name = memory.get_working_memory('last_selected_agent')
        
        if not last_agent_name:
            return None, 0.0, False
        
        # Get the last agent
        last_agent = self.registry.get_by_name(last_agent_name)
        if not last_agent:
            return None, 0.0, False
        
        # Check for explicit continuity flag
        if continue_with_same_agent:
            logger.info(f"continue_with_same_agent flag is set to True for agent: {last_agent_name}")
            
            # Get base confidence from the agent
            current_agent_confidence = last_agent.can_handle(user_input, context)
            
            # Check for topic change
            is_topic_change = self.topic_detector.detect_topic_change(
                user_input, last_agent_name, context, self.registry.get_all()
            )
            
            if is_topic_change:
                # Don't apply continuity bonus if topic changed
                logger.info(f"Detected topic change - not applying continuity bonus")
                memory.mark_continue_with_same_agent(False)
                return None, 0.0, False
            else:
                # Apply continuity bonus for explicit continuity requests
                adjusted_confidence = self.scorer.apply_continuity_bonus(
                    last_agent_name, current_agent_confidence, False, True
                )
                
                # Reset the flag unless set again by the agent
                memory.mark_continue_with_same_agent(False)
                
                return last_agent, adjusted_confidence, True
        
        # Check for time-based continuity (recent conversation)
        last_timestamp_str = memory.get_working_memory('timestamp')
        if last_timestamp_str:
            try:
                last_timestamp = datetime.fromisoformat(last_timestamp_str)
                # Only consider recent conversations (within recency window)
                if datetime.now() - last_timestamp < timedelta(seconds=self.config.recency_window):
                    # Check if the agent still has some confidence
                    current_agent_confidence = last_agent.can_handle(user_input, context)
                    
                    # Check for topic change
                    is_topic_change = self.topic_detector.detect_topic_change(
                        user_input, last_agent_name, context, self.registry.get_all()
                    )
                    
                    if is_topic_change:
                        logger.info(f"Detected topic change in time-based continuity - not applying bonus")
                        return None, 0.0, False
                    else:
                        # Apply a reduced continuity bonus
                        adjusted_confidence = self.scorer.apply_continuity_bonus(
                            last_agent_name, current_agent_confidence, False, False
                        )
                        
                        # Only use if it meets the fallback threshold
                        if self.scorer.is_above_fallback_threshold(
                            adjusted_confidence, self.config.fallback_threshold
                        ):
                            return last_agent, adjusted_confidence, True
            except (ValueError, TypeError):
                # If timestamp parsing fails, ignore and continue with standard selection
                pass
        
        return None, 0.0, False
    
    def _evaluate_all_agents(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Evaluate all agents and select the best one.
        
        Args:
            user_input: User's request or query
            context: Context information
            
        Returns:
            Tuple of (agent, confidence, context_used) or (None, 0.0, False)
        """
        # Get session ID from context for telemetry
        session_id = context.get('session_id', 'default')
        
        agents = self.registry.get_all()
        agent_scores = []
        
        # Get confidence scores from all agents
        for agent in agents:
            try:
                # Get base confidence from agent
                base_confidence = agent.can_handle(user_input, context)
                
                # Apply contextual boosts based on entities and intent
                adjusted_confidence, context_used = self.scorer.apply_contextual_boost(
                    agent.name, base_confidence, context
                )
                
                # Track agent confidence in telemetry
                telemetry_collector.track_agent_confidence(
                    session_id,
                    agent.name,
                    base_confidence,
                    adjusted_confidence,
                    context_used
                )
                
                agent_scores.append((agent, adjusted_confidence, base_confidence, context_used))
                
            except Exception as e:
                logger.error(f"Error getting confidence from agent '{agent.name}': {str(e)}")
                # Track error in telemetry
                telemetry_collector.track_error(
                    session_id,
                    "agent_confidence_error",
                    f"Error getting confidence from agent '{agent.name}': {str(e)}"
                )
        
        # Log all agent scores
        if agent_scores:
            self.logger.log_agent_scores([(a.name, score) for a, score, _, _ in agent_scores])
        
        # No agents to evaluate
        if not agent_scores:
            return None, 0.0, False
        
        # Rank agents by adjusted confidence
        ranked_agents = self.scorer.rank_agents(agent_scores)
        
        # Handle tie-breaking for close scores
        if len(ranked_agents) >= 2:
            top_agent, top_confidence, _, top_context_used = ranked_agents[0]
            second_agent, second_confidence, _, second_context_used = ranked_agents[1]
            
            # If scores are very close, apply tie-breaking logic
            if abs(top_confidence - second_confidence) <= 0.1:
                logger.info(f"Close agent scores: {top_agent.name} ({top_confidence:.2f}) vs "
                          f"{second_agent.name} ({second_confidence:.2f})")
                
                # Prioritize Store Locator for location-related queries
                if self._is_location_query(user_input):
                    if top_agent.name == "Store Locator Agent":
                        # Already on top, just boost slightly
                        adjusted_confidence = min(top_confidence + 0.05, 0.99)
                        logger.info(f"Prioritizing Store Locator Agent for location-related query")
                        return top_agent, adjusted_confidence, top_context_used
                    elif second_agent.name == "Store Locator Agent":
                        # Promote Store Locator to the top
                        adjusted_confidence = min(second_confidence + 0.1, 0.99)
                        logger.info(f"Promoting Store Locator Agent for location-related query")
                        return second_agent, adjusted_confidence, second_context_used
        
        # Select the highest-scoring agent if it meets the threshold
        if ranked_agents:
            best_agent, best_confidence, _, context_used = ranked_agents[0]
            if self.scorer.is_above_threshold(best_confidence):
                return best_agent, best_confidence, context_used
        
        # No agent reached the confidence threshold
        return None, 0.0, False
    
    def _is_location_query(self, user_input: str) -> bool:
        """
        Check if a query is location-related.
        
        Args:
            user_input: User's request or query
            
        Returns:
            True if this is a location-related query
        """
        import re
        
        # Check for zip codes
        zip_pattern = re.search(r'\b\d{5}(-\d{4})?\b', user_input)
        
        # Check for location keywords
        location_keywords = ["store", "location", "find", "nearest", "close", "near me", "nearby", "directions"]
        has_location_keyword = any(kw in user_input.lower() for kw in location_keywords)
        
        # Check for city names (simplified example - in a real system, this would use a more comprehensive approach)
        city_names = ["natick", "boston", "new york", "chicago", "philadelphia", "los angeles", "san francisco"]
        has_city_name = any(city in user_input.lower() for city in city_names)
        
        return bool(zip_pattern or has_location_keyword or has_city_name)
    
    def _check_out_of_scope(self, user_input: str, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if a query is out of scope for our virtual agents.
        
        Args:
            user_input: User's request or query
            context: Context information
            
        Returns:
            Tuple of (is_out_of_scope, topic_category)
        """
        # In a full implementation, this would contain proper guardrails logic
        # For now, we'll assume all queries are in scope
        return False, None
    
    def _handle_out_of_scope(self, topic_category: Optional[str]) -> Dict[str, Any]:
        """
        Generate a response for out-of-scope queries.
        
        Args:
            topic_category: The detected topic category
            
        Returns:
            Response dictionary
        """
        # Define helpful responses for out-of-scope topics
        out_of_scope_responses = {
            "hiring": "I'm not able to assist with job applications or the hiring process. Please visit our careers page for current job openings and application information.",
            "hr_policies": "I don't have access to information about HR policies or employee benefits. Please contact the HR department directly for assistance.",
            "legal": "I'm not authorized to discuss legal matters or provide legal advice. Please contact Customer Service for assistance with your concern.",
            "unrelated": "I'm designed to help with customer service matters like tracking orders, finding stores, or resetting passwords. For this topic, you might want to reach out to a different service."
        }
        
        # Get appropriate response or use generic one
        response_text = out_of_scope_responses.get(
            topic_category, 
            "I'm designed to help with specific customer service tasks like tracking orders, resetting passwords, or finding store locations. This question is outside my area of expertise. Please contact Customer Service for further assistance."
        )
        
        return {
            "success": True,
            "response": response_text,
            "agent": "Out of Scope Handler",
            "confidence": 1.0,
            "is_out_of_scope": True,
            "topic_category": topic_category
        }
    
    def _handle_no_agent_found(self) -> Dict[str, Any]:
        """
        Generate a response when no suitable agent is found.
        
        Returns:
            Response dictionary with suggested actions
        """
        # Create the standard suggested actions
        suggested_actions = [
            {"id": "package-tracking", "name": "Track my package", "description": "Check the status of your order or package"},
            {"id": "reset-password", "name": "Reset my password", "description": "Get help with account access or password reset"},
            {"id": "store-locator", "name": "Find a store", "description": "Locate stores near you"}
        ]
        
        # Build a welcoming response
        response_text = "Hi! I can help with:\n\n"
        response_text += "• Package tracking\n"
        response_text += "• Password reset\n"
        response_text += "• Store locations\n"
        
        # Add any registered custom agents
        custom_agents = [agent for agent in self.registry.get_all() 
                      if agent.name not in ["Package Tracking Agent", "Reset Password Agent", "Store Locator Agent"]]
        
        if custom_agents:
            custom_agent_names = [agent.name.replace(" Agent", "") for agent in custom_agents]
            response_text += "• " + "\n• ".join(custom_agent_names)
            
            # Add custom agents to suggested actions
            for agent in custom_agents:
                suggested_actions.append({
                    "id": f"custom-{agent.id}", 
                    "name": agent.name.replace(" Agent", ""),
                    "description": getattr(agent, "description", f"Use the {agent.name}")
                })
        
        response_text += "\n\nWhat do you need help with?"
        
        return {
            "success": True,
            "intent": "welcome",
            "response": response_text,
            "suggested_actions": suggested_actions,
            "agent": None
        }