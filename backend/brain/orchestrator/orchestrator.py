"""
Orchestrator for Staples Brain.
This module provides the main orchestration logic for routing requests to the appropriate agent.
"""
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union

from backend.config.agent_constants import (
    INTENT_AGENT_MAPPING,
    DEFAULT_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    CONTINUITY_BONUS,
    CONTEXT_WINDOW,
    AGENT_TIMEOUTS
)
from backend.utils.memory import ConversationMemory

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Main orchestrator class for the Staples Brain system.
    
    This class coordinates between different specialized agents based on detected intents.
    It implements sophisticated agent selection and routing mechanisms, including:
    - Intent-based routing
    - Confidence scoring with continuity bonus
    - Context-aware conversation handling
    - Agent coordination and fallback mechanisms
    """
    
    def __init__(self, agents=None):
        """
        Initialize the orchestrator.
        
        Args:
            agents: List of agent instances to coordinate
        """
        self.agents = agents or []
        self.memories = {}  # session_id -> ConversationMemory
        # Import telemetry system if available
        try:
            from backend.brain.telemetry import collector
            self.telemetry = collector
        except ImportError:
            self.telemetry = None
            logger.warning("Telemetry system not available, proceeding without telemetry")
        
    def get_memory(self, session_id: str) -> ConversationMemory:
        """
        Get or create conversation memory for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationMemory instance for the session
        """
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory(session_id)
        return self.memories[session_id]
        
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents.
        
        Returns:
            List of agent information dictionaries
        """
        return [
            {
                'id': 'package_tracking',
                'name': 'Package Tracking',
                'description': 'Track packages and order status'
            },
            {
                'id': 'reset_password',
                'name': 'Reset Password',
                'description': 'Help with password reset processes'
            },
            {
                'id': 'store_locator',
                'name': 'Store Locator',
                'description': 'Find nearby Staples stores'
            },
            {
                'id': 'product_info',
                'name': 'Product Information',
                'description': 'Get information about Staples products'
            }
        ]
    
    def _select_agent(self, user_input: str, context: Dict[str, Any]) -> Tuple[Any, float, bool]:
        """
        Select the most appropriate agent for the user input.
        
        Args:
            user_input: The user's message
            context: Context information, including session_id
        
        Returns:
            Tuple of (selected_agent, confidence_score, context_used)
        """
        logger.debug(f"Selecting agent for: '{user_input[:50]}...' if len > 50")
        
        # Get session ID and memory
        session_id = context.get('session_id', 'default_session')
        memory = context.get('conversation_memory') or self.get_memory(session_id)
        
        # Check for explicit intent in context
        intent = context.get('intent')
        intent_confidence = context.get('intent_confidence', 0.0)
        
        # Initialize tracking variables
        best_agent = None
        best_confidence = 0.0
        best_is_continuity = False
        used_context = False
        
        # Apply continuity logic for multi-turn conversations
        continuity_bonus = 0.0
        last_agent_name = memory.get_from_working_memory('last_selected_agent')
        continue_with_same_agent = memory.get_from_working_memory('continue_with_same_agent', False)
        
        if last_agent_name and continue_with_same_agent:
            continuity_bonus = CONTINUITY_BONUS
            logger.debug(f"Applying continuity bonus of {continuity_bonus} for agent {last_agent_name}")
            
            # Track continuity check in telemetry if available
            if self.telemetry:
                self.telemetry.track_continuity_check(
                    session_id=session_id,
                    last_agent=last_agent_name,
                    continue_same_agent=True,
                    reason="explicit_continue_flag"
                )
        
        # First, try intent-based routing if we have a high-confidence intent
        if intent and intent in INTENT_AGENT_MAPPING and intent_confidence >= HIGH_CONFIDENCE_THRESHOLD:
            agent_name = INTENT_AGENT_MAPPING[intent]
            if agent_name:
                # Find the agent with this name
                for agent in self.agents:
                    if agent.name == agent_name:
                        logger.debug(f"Using intent-based routing for high-confidence intent: {intent}")
                        # Track in telemetry if available
                        if self.telemetry:
                            self.telemetry.track_intent_routing(
                                session_id=session_id,
                                intent=intent,
                                agent_name=agent_name,
                                succeeded=True
                            )
                        return agent, intent_confidence, True
                        
        # Otherwise, use confidence-based routing
        for agent in self.agents:
            # Apply continuity bonus if this is the same agent as before
            agent_bonus = 0.0
            is_continuity = False
            
            if agent.name == last_agent_name and continue_with_same_agent:
                agent_bonus = continuity_bonus
                is_continuity = True
            
            # Get base confidence score from agent
            try:
                base_confidence = agent.can_handle(user_input, context)
                adjusted_confidence = base_confidence + agent_bonus
                
                # Track confidence score in telemetry if available
                if self.telemetry:
                    self.telemetry.track_agent_confidence(
                        session_id=session_id,
                        agent_name=agent.name,
                        base_confidence=base_confidence,
                        adjusted_confidence=adjusted_confidence,
                        context_used=bool(context)
                    )
                    
                logger.debug(f"Agent {agent.name}: base={base_confidence:.2f}, adjusted={adjusted_confidence:.2f}")
                
                # Update best agent if this has higher confidence
                if adjusted_confidence > best_confidence:
                    best_agent = agent
                    best_confidence = adjusted_confidence
                    best_is_continuity = is_continuity
                    used_context = bool(context)
            except Exception as e:
                logger.error(f"Error getting confidence from {agent.name}: {str(e)}")
        
        # Reset continuity flag after using it
        if continue_with_same_agent:
            memory.update_working_memory('continue_with_same_agent', False)
        
        # Check if confidence meets the threshold
        if best_confidence < DEFAULT_CONFIDENCE_THRESHOLD:
            logger.debug(f"No agent exceeded confidence threshold. Best was {best_agent.name if best_agent else 'None'} with {best_confidence:.2f}")
            # Fall back to default behavior or general agent
            # For demo purposes, just use the first agent if none hit the threshold
            if not best_agent and self.agents:
                best_agent = self.agents[0]
                best_confidence = DEFAULT_CONFIDENCE_THRESHOLD
                
        # Track final selection in telemetry if available
        if self.telemetry and best_agent:
            selection_method = "continuity_bonus" if best_is_continuity else "confidence_score"
            self.telemetry.track_agent_selection(
                session_id=session_id,
                agent_name=best_agent.name,
                confidence=best_confidence,
                selection_method=selection_method
            )
                
        return best_agent, best_confidence, used_context
    
    async def process_message(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message and route to the appropriate agent.
        
        Args:
            message: User's message text
            session_id: Session identifier
            context: Additional context information
            
        Returns:
            Response dictionary with agent output
        """
        if not context:
            context = {}
            
        context['session_id'] = session_id
        start_time = time.time()
        
        # Track incoming request in telemetry if available
        request_event_id = None
        if self.telemetry:
            request_event_id = self.telemetry.track_request_received(session_id, message)
        
        # Get memory for this session
        memory = self.get_memory(session_id)
        context['conversation_memory'] = memory
        
        try:
            # Select the best agent for this message
            best_agent, confidence, context_used = self._select_agent(message, context)
            
            if not best_agent:
                logger.warning("No suitable agent found for the message")
                return {
                    'success': False,
                    'response': "I'm sorry, but I don't understand how to help with that request. Could you please rephrase or ask about something else?",
                    'agent': 'fallback',
                    'confidence': 0.0,
                    'processing_time': time.time() - start_time
                }
            
            # Update memory with selected agent
            memory.update_working_memory('last_selected_agent', best_agent.name)
            
            # Get agent timeout or use default
            timeout = AGENT_TIMEOUTS.get(best_agent.name, AGENT_TIMEOUTS.get('default', 20))
            
            # Process with timeout protection
            try:
                async with asyncio.timeout(timeout):
                    # Get response from the selected agent
                    response = await best_agent.handle_message(message, context)
            except asyncio.TimeoutError:
                logger.error(f"Agent {best_agent.name} timed out after {timeout}s")
                return {
                    'success': False,
                    'response': "I'm sorry, but it's taking longer than expected to process your request. Please try again or break your question into smaller parts.",
                    'agent': best_agent.name,
                    'confidence': confidence,
                    'processing_time': time.time() - start_time,
                    'error': 'timeout'
                }
            
            # Track successful response generation in telemetry if available
            if self.telemetry:
                processing_time = time.time() - start_time
                self.telemetry.track_response_generation(
                    session_id=session_id,
                    agent_name=best_agent.name,
                    success=True,
                    processing_time=processing_time,
                    parent_id=request_event_id
                )
                
            # Add metadata to response
            return {
                'success': True,
                'response': response,
                'agent': best_agent.name,
                'confidence': confidence,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            processing_time = time.time() - start_time
            
            # Track error in telemetry if available
            if self.telemetry:
                self.telemetry.track_error(
                    session_id=session_id,
                    error_type='orchestration_error',
                    error_message=str(e),
                    recoverable=True,
                    parent_id=request_event_id
                )
                
            return {
                'success': False,
                'response': "I'm sorry, but something went wrong while processing your request. Please try again.",
                'agent': 'error_handler',
                'confidence': 0.0,
                'processing_time': processing_time,
                'error': str(e)
            }
        
    async def process_request(self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request and route it to the appropriate agent.
        This is the main entry point for handling user requests.
        
        Args:
            message: User's message text
            session_id: Session identifier
            context: Additional context information
            
        Returns:
            Response dictionary with agent output and metadata
        """
        if not context:
            context = {}
            
        context['session_id'] = session_id
        
        # Process the message
        result = await self.process_message(message, session_id, context)
        
        # Format for the external API
        return {
            'success': result.get('success', False),
            'response': result.get('response', "Sorry, no response was generated."),
            'selected_agent': result.get('agent', 'unknown'),
            'confidence': result.get('confidence', 0.0),
            'processing_time': result.get('processing_time', 0.0),
            'session_id': session_id,
            'error': result.get('error')
        }
        
    def list_agents(self):
        """
        List all available agents.
        
        Returns:
            List of agent instances
        """
        return self.agents
        
    def register_agent(self, agent):
        """
        Register a new agent with the orchestrator.
        
        Args:
            agent: The agent instance to register
            
        Returns:
            True if registration was successful
        """
        # Check if agent is already registered
        for existing_agent in self.agents:
            if existing_agent.name == agent.name:
                logger.warning(f"Agent {agent.name} is already registered")
                return False
                
        # Add the agent to the list
        self.agents.append(agent)
        logger.info(f"Registered agent: {agent.name}")
        
        # Track in telemetry if available
        if self.telemetry:
            try:
                # Check if the method exists before calling it
                if hasattr(self.telemetry, 'track_agent_registered'):
                    self.telemetry.track_agent_registered(agent.name)
                else:
                    logger.debug(f"Telemetry doesn't have track_agent_registered method, skipping telemetry for agent registration")
            except Exception as e:
                logger.warning(f"Failed to track agent registration in telemetry: {str(e)}")
            
        return True
        
    async def cleanup(self):
        """
        Clean up resources used by the orchestrator.
        
        Should be called before application shutdown.
        """
        # Cleanup sessions that are too old
        sessions_to_remove = []
        
        for session_id, memory in self.memories.items():
            if memory.is_expired():
                sessions_to_remove.append(session_id)
                
        for session_id in sessions_to_remove:
            del self.memories[session_id]
            
        logger.debug(f"Cleaned up {len(sessions_to_remove)} expired session memories")
        
        # Clean up any other resources
        self.memories.clear()