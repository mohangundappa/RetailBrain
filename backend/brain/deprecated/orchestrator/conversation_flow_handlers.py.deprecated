"""
Conversation flow handlers for Staples Brain.

This module provides utility functions for detecting and handling special
conversation flow scenarios like greetings, conversation ends, topic switches,
requests to hold, human transfers, etc.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from backend.utils.memory import ConversationMemory
from backend.utils.semantic_utils import semantic_analyzer
from backend.config.agent_constants import (
    GREETING_CONFIDENCE,
    HUMAN_TRANSFER_CONFIDENCE,
    CONVERSATION_END_CONFIDENCE,
    NEGATIVE_FEEDBACK_PENALTY,
    DEFAULT_CONFIDENCE_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    MAX_CONFIDENCE_THRESHOLD
)

logger = logging.getLogger(__name__)

class ConversationFlowHandler:
    """
    Utility class for handling special conversation flow scenarios.
    
    This class detects and handles special cases in conversations such as:
    - Greetings
    - Conversation ends
    - Human transfer requests
    - Hold requests
    - Negative feedback
    - Topic switches
    """
    
    @staticmethod
    def check_special_cases(user_input: str) -> Tuple[Optional[str], float, Optional[str]]:
        """
        Check for special case scenarios like greetings, conversation ends, and human transfer requests.
        
        Args:
            user_input: The user's message
            
        Returns:
            Tuple of (special_case_type, confidence, response)
        """
        # Check for greeting
        greeting_confidence = semantic_analyzer.detect_greeting(user_input)
        if greeting_confidence >= GREETING_CONFIDENCE:
            logger.debug(f"Detected greeting with confidence {greeting_confidence:.2f}")
            return "greeting", greeting_confidence, "Hello! I'm your Staples virtual assistant. How can I help you today?"
        
        # Check for conversation end
        end_confidence = semantic_analyzer.detect_conversation_end(user_input)
        if end_confidence >= CONVERSATION_END_CONFIDENCE:
            logger.debug(f"Detected conversation end with confidence {end_confidence:.2f}")
            return "conversation_end", end_confidence, "Thank you for contacting Staples! Is there anything else I can help you with?"
        
        # Check for human transfer request
        transfer_confidence = semantic_analyzer.detect_human_transfer_request(user_input)
        if transfer_confidence >= HUMAN_TRANSFER_CONFIDENCE:
            logger.debug(f"Detected human transfer request with confidence {transfer_confidence:.2f}")
            return "human_transfer", transfer_confidence, "I understand you'd like to speak with a human agent. I'll transfer you to a customer service representative who can assist you further."
        
        # Check for hold request
        hold_confidence = ConversationFlowHandler.detect_hold_request(user_input)
        if hold_confidence >= 0.8:  # Using a high threshold for hold requests
            logger.debug(f"Detected hold request with confidence {hold_confidence:.2f}")
            return "hold_request", hold_confidence, "No problem, I'll wait. Let me know when you're ready to continue."
        
        return None, 0.0, None
    
    @staticmethod
    def detect_hold_request(text: str) -> float:
        """
        Detect if the user is asking the assistant to wait or hold.
        
        Args:
            text: Input text
            
        Returns:
            Confidence score that text is a hold request (0-1)
        """
        text = text.lower()
        hold_phrases = [
            "hold on", "wait a moment", "give me a minute", "just a sec",
            "wait a sec", "one moment", "hold up", "hang on", "wait for me",
            "stay there", "don't go away", "be right back", "brb",
            "pause", "wait", "hold", "one second", "1 second", "1 minute"
        ]
        
        # Check for exact hold phrase matches
        for phrase in hold_phrases:
            if phrase in text:
                # Higher confidence for exact matches
                return 0.9
                
        # Calculate similarity with common hold requests
        common_requests = [
            "Can you hold on for a minute?",
            "Wait a second please",
            "Give me a moment to check something",
            "Hold on while I find that information"
        ]
        
        similarities = [semantic_analyzer.calculate_similarity(text, request) for request in common_requests]
        max_similarity = max(similarities) if similarities else 0.0
        
        return max_similarity
    
    @staticmethod
    def check_negative_feedback(user_input: str, memory: ConversationMemory) -> bool:
        """
        Check if the user's input contains negative feedback.
        
        Args:
            user_input: The user's message
            memory: Conversation memory
            
        Returns:
            True if negative feedback detected, False otherwise
        """
        # Detect negative feedback
        negative_feedback_confidence = semantic_analyzer.detect_negative_feedback(user_input)
        if negative_feedback_confidence > 0.7:
            logger.debug(f"Detected negative feedback with confidence {negative_feedback_confidence:.2f}")
            
            # Store negative feedback in memory for threshold adjustment
            memory.update_working_memory('negative_feedback_detected', True)
            memory.update_working_memory('negative_feedback_confidence', negative_feedback_confidence)
            
            return True
        
        return False
    
    @staticmethod
    def get_dynamic_threshold(memory: ConversationMemory) -> float:
        """
        Determine the confidence threshold dynamically based on conversation state.
        
        Args:
            memory: Conversation memory
            
        Returns:
            Dynamic confidence threshold
        """
        # Start with default threshold
        threshold = DEFAULT_CONFIDENCE_THRESHOLD
        
        # Lower threshold if negative feedback was detected in the previous turn
        if memory.get_from_working_memory('negative_feedback_detected', False):
            # Apply penalty to make it easier to switch agents after negative feedback
            threshold -= NEGATIVE_FEEDBACK_PENALTY
            logger.debug(f"Lowering confidence threshold due to negative feedback: {threshold:.2f}")
            
            # Reset negative feedback flag
            memory.update_working_memory('negative_feedback_detected', False)
        
        # Ensure threshold stays within reasonable bounds
        threshold = max(MIN_CONFIDENCE_THRESHOLD, min(MAX_CONFIDENCE_THRESHOLD, threshold))
        
        return threshold
    
    @staticmethod
    def detect_topic_switch(user_input: str, memory: ConversationMemory) -> bool:
        """
        Detect if the current input represents a topic switch.
        
        Args:
            user_input: The user's message
            memory: Conversation memory
            
        Returns:
            True if topic switch detected, False otherwise
        """
        # Get the last topic summary if available
        last_topic = memory.get_from_working_memory('current_topic')
        if not last_topic:
            return False
            
        # Check if current input is semantically different from the last topic
        is_interruption, confidence = semantic_analyzer.detect_conversation_interruption(last_topic, user_input)
        
        if is_interruption and confidence > 0.7:
            logger.debug(f"Detected topic switch with confidence {confidence:.2f}")
            return True
            
        return False
    
    @staticmethod
    def handle_conversation_flow(
        user_input: str,
        memory: ConversationMemory,
        context: Dict[str, Any],
        processing_time_start: float
    ) -> Optional[Dict[str, Any]]:
        """
        Handle special conversation flow cases and prepare appropriate responses.
        
        Args:
            user_input: The user's message
            memory: Conversation memory
            context: The current context dictionary
            processing_time_start: Start time for performance tracking
            
        Returns:
            Response dictionary if special case handled, None otherwise
        """
        import time  # Import here to avoid circular import
        
        # Check if in hold state
        if memory.get_from_working_memory('hold_state', False):
            # User has returned after a hold, reset the hold state
            memory.update_working_memory('hold_state', False)
            # But we'll let normal processing continue, so return None
            logger.info("User returned after hold state")
            return None
        
        # Check for special cases
        special_case, special_confidence, special_response = ConversationFlowHandler.check_special_cases(user_input)
        
        if special_case:
            if special_case == "greeting":
                # For greetings, we store the response and let the orchestrator handle
                # the agent selection normally to blend domain-specific info
                context['greeting_response'] = special_response
                return None
                
            elif special_case == "human_transfer":
                # Store human transfer request in memory
                memory.update_working_memory('human_transfer_requested', True)
                # Return response to be sent to the user
                return {
                    'success': True,
                    'response': special_response,
                    'agent': 'human_transfer',
                    'confidence': special_confidence,
                    'processing_time': time.time() - processing_time_start,
                    'metadata': {
                        'human_transfer': True
                    }
                }
                
            elif special_case == "conversation_end":
                # Return end of conversation response
                return {
                    'success': True,
                    'response': special_response,
                    'agent': 'conversation_end',
                    'confidence': special_confidence,
                    'processing_time': time.time() - processing_time_start
                }
                
            elif special_case == "hold_request":
                # Set the hold state in memory
                memory.update_working_memory('hold_state', True)
                memory.update_working_memory('hold_timestamp', time.time())
                
                # Return acknowledgment response
                return {
                    'success': True,
                    'response': special_response,
                    'agent': 'hold_request',
                    'confidence': special_confidence,
                    'processing_time': time.time() - processing_time_start,
                    'metadata': {
                        'hold_state': True
                    }
                }
        
        # No special case detected or it's a greeting (which should proceed to normal agent selection)
        return None