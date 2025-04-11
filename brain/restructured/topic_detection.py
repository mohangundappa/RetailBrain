"""
Topic change detection for the orchestration system.
This module detects when a conversation shifts to a new topic to improve agent selection.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class TopicChangeDetector(ABC):
    """Base class for topic change detection strategies."""
    
    @abstractmethod
    def detect_topic_change(self, user_input: str, current_agent_name: str, 
                          context: Dict[str, Any], agents: List) -> bool:
        """
        Detect if there's a topic change in the conversation.
        
        Args:
            user_input: The user's request or query
            current_agent_name: The current agent handling the conversation
            context: Additional context information
            agents: List of all available agents
            
        Returns:
            True if a topic change is detected, False otherwise
        """
        pass


class CompositeTopicDetector(TopicChangeDetector):
    """Combines multiple topic change detection strategies."""
    
    def __init__(self, detectors: List[TopicChangeDetector]):
        """
        Initialize with a list of detector instances.
        
        Args:
            detectors: List of TopicChangeDetector instances
        """
        self.detectors = detectors
        
    def detect_topic_change(self, user_input: str, current_agent_name: str, 
                          context: Dict[str, Any], agents: List) -> bool:
        """
        Run all detectors and return True if any detect a topic change.
        
        Args:
            user_input: The user's request or query
            current_agent_name: The current agent handling the conversation
            context: Additional context information
            agents: List of all available agents
            
        Returns:
            True if any detector finds a topic change
        """
        # Skip very short inputs as they're likely clarifications, not topic changes
        if len(user_input.split()) <= 2:
            return False
            
        for detector in self.detectors:
            if detector.detect_topic_change(user_input, current_agent_name, context, agents):
                return True
                
        return False


class ConfidenceBasedTopicDetector(TopicChangeDetector):
    """Detects topic changes by comparing agent confidence scores."""
    
    def __init__(self, confidence_diff_threshold: float = 0.3):
        """
        Initialize with a confidence difference threshold.
        
        Args:
            confidence_diff_threshold: Minimum confidence difference to trigger a topic change
        """
        self.confidence_diff_threshold = confidence_diff_threshold
        
    def detect_topic_change(self, user_input: str, current_agent_name: str, 
                          context: Dict[str, Any], agents: List) -> bool:
        """
        Compare confidence scores between current and other agents.
        
        Args:
            user_input: The user's request or query
            current_agent_name: The current agent handling the conversation
            context: Additional context information
            agents: List of all available agents
            
        Returns:
            True if another agent has significantly higher confidence
        """
        # Find current agent
        current_agent = None
        for agent in agents:
            if agent.name == current_agent_name:
                current_agent = agent
                break
                
        if not current_agent:
            logger.warning(f"Current agent '{current_agent_name}' not found in agent list")
            return False
            
        # Get confidence score from current agent
        try:
            current_agent_confidence = current_agent.can_handle(user_input, context)
            
            # Check if any other agent has significantly higher confidence
            for agent in agents:
                # Skip the current agent
                if agent.name == current_agent_name:
                    continue
                    
                try:
                    # Get confidence from this agent
                    other_agent_confidence = agent.can_handle(user_input, context)
                    
                    # Compare confidence levels
                    confidence_diff = other_agent_confidence - current_agent_confidence
                    
                    # If another agent has significantly higher confidence, it's a topic change
                    if confidence_diff > self.confidence_diff_threshold:
                        logger.info(f"Topic change detected by confidence: {current_agent.name} ({current_agent_confidence:.2f}) -> "
                                  f"{agent.name} ({other_agent_confidence:.2f}), diff: {confidence_diff:.2f}")
                        return True
                        
                except Exception as e:
                    logger.error(f"Error comparing confidence with agent '{agent.name}': {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error getting confidence from current agent '{current_agent.name}': {str(e)}")
            
        return False


class IntentBasedTopicDetector(TopicChangeDetector):
    """Detects topic changes based on intent mapping."""
    
    def __init__(self, intent_mapping: Dict[str, str]):
        """
        Initialize with an intent mapping.
        
        Args:
            intent_mapping: Dictionary mapping intents to agent names
        """
        self.intent_mapping = intent_mapping
        
    def detect_topic_change(self, user_input: str, current_agent_name: str, 
                          context: Dict[str, Any], agents: List) -> bool:
        """
        Check if the current intent maps to a different agent.
        
        Args:
            user_input: The user's request or query
            current_agent_name: The current agent handling the conversation
            context: Additional context information
            agents: List of all available agents
            
        Returns:
            True if intent maps to a different agent
        """
        if 'intent' not in context:
            return False
            
        current_intent = context.get('intent')
        if not current_intent or current_intent not in self.intent_mapping:
            return False
            
        mapped_agent = self.intent_mapping[current_intent]
        if mapped_agent.lower() != current_agent_name.lower():
            logger.info(f"Intent change detected: intent '{current_intent}' maps to {mapped_agent}, "
                      f"not current agent {current_agent_name}")
            return True
            
        return False


class KeywordBasedTopicDetector(TopicChangeDetector):
    """Detects topic changes based on domain-specific keywords."""
    
    def __init__(self):
        """Initialize with predefined keyword mappings."""
        self.keyword_mappings = {
            "Reset Password Agent": {
                "keywords": ['store', 'location', 'nearby', 'closest', 'find'],
                "target": "Store Locator Agent"
            },
            "Package Tracking Agent": {
                "keywords": ['password', 'login', 'account', 'sign in', 'forgot'],
                "target": "Reset Password Agent"
            },
            "Store Locator Agent": {
                "keywords": ['order', 'tracking', 'package', 'shipped', 'delivery'],
                "target": "Package Tracking Agent"
            }
        }
        
    def detect_topic_change(self, user_input: str, current_agent_name: str, 
                          context: Dict[str, Any], agents: List) -> bool:
        """
        Check for domain-specific keywords indicating topic change.
        
        Args:
            user_input: The user's request or query
            current_agent_name: The current agent handling the conversation
            context: Additional context information
            agents: List of all available agents
            
        Returns:
            True if keywords indicate a topic change
        """
        if current_agent_name not in self.keyword_mappings:
            return False
            
        mapping = self.keyword_mappings[current_agent_name]
        user_input_lower = user_input.lower()
        
        for keyword in mapping["keywords"]:
            if keyword in user_input_lower:
                logger.info(f"Topic change detected through keywords: {current_agent_name} -> {mapping['target']}")
                return True
                
        return False


def create_default_topic_detector(intent_mapping: Dict[str, str]) -> TopicChangeDetector:
    """
    Create a default topic detector with standard detection strategies.
    
    Args:
        intent_mapping: Dictionary mapping intents to agent names
        
    Returns:
        CompositeTopicDetector with standard detectors
    """
    confidence_detector = ConfidenceBasedTopicDetector()
    intent_detector = IntentBasedTopicDetector(intent_mapping)
    keyword_detector = KeywordBasedTopicDetector()
    
    return CompositeTopicDetector([
        confidence_detector,
        intent_detector,
        keyword_detector
    ])