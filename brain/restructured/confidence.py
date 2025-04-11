"""
Confidence scoring system for the orchestration engine.
This module handles the calculation and adjustment of confidence scores for agent selection.
"""
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Manages confidence scoring for agent selection."""
    
    def __init__(self, confidence_threshold: float = 0.3,
                high_confidence: float = 0.7,
                continuity_bonus: float = 0.2):
        """
        Initialize the confidence scorer.
        
        Args:
            confidence_threshold: Minimum confidence required to select an agent
            high_confidence: Threshold for high confidence
            continuity_bonus: Bonus added when continuing with the same agent
        """
        self.confidence_threshold = confidence_threshold
        self.high_confidence = high_confidence
        self.continuity_bonus = continuity_bonus
        
    def apply_contextual_boost(self, agent_name: str, base_confidence: float,
                            context: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Apply contextual confidence boosts based on entities/intent.
        
        Args:
            agent_name: The name of the agent
            base_confidence: The base confidence score
            context: The context dictionary
            
        Returns:
            Tuple of (adjusted_confidence, context_used)
        """
        boost = 0.0
        context_used = False
        
        # Extract necessary data from context
        intent = context.get('intent')
        intent_mapping = context.get('intent_mapping', {})
        entities = context.get('entities', {})
        
        # Check for intent-agent alignment (smaller boost than direct routing)
        if intent and intent in intent_mapping and intent_mapping[intent].lower() == agent_name.lower():
            boost += 0.1
            context_used = True
            logger.debug(f"Applied intent alignment boost to {agent_name}: +0.1")
        
        # Check for entity-agent alignment
        if agent_name == "Package Tracking Agent" and any(entity in entities for entity in 
                                                    ['tracking_number', 'order_number', 'shipping_carrier']):
            boost += 0.15
            context_used = True
            logger.debug(f"Applied entity alignment boost to {agent_name}: +0.15")
            
        elif agent_name == "Reset Password Agent" and any(entity in entities for entity in 
                                                   ['email', 'username', 'account_type']):
            boost += 0.15
            context_used = True
            logger.debug(f"Applied entity alignment boost to {agent_name}: +0.15")
            
        elif agent_name == "Store Locator Agent" and any(entity in entities for entity in 
                                                  ['location', 'zip_code', 'service']):
            boost += 0.15
            context_used = True
            logger.debug(f"Applied entity alignment boost to {agent_name}: +0.15")
                
        # Apply the boost and cap at 1.0
        adjusted_confidence = min(base_confidence + boost, 1.0)
        
        if boost > 0:
            logger.debug(f"Agent '{agent_name}' base confidence: {base_confidence:.2f}, "
                       f"with context boost: {adjusted_confidence:.2f}")
                
        return adjusted_confidence, context_used
        
    def apply_continuity_bonus(self, current_agent_name: str, 
                             base_confidence: float,
                             is_topic_change: bool,
                             is_explicit_continuity: bool = False) -> float:
        """
        Apply confidence bonus for conversation continuity.
        
        Args:
            current_agent_name: The current agent's name
            base_confidence: The base confidence score
            is_topic_change: Whether a topic change was detected
            is_explicit_continuity: Whether continuity was explicitly requested
            
        Returns:
            Adjusted confidence score
        """
        if is_topic_change:
            logger.debug(f"Topic change detected for {current_agent_name} - not applying continuity bonus")
            return base_confidence
            
        if is_explicit_continuity:
            # For explicit continuity, ensure a minimum confidence and apply continuity bonus
            confidence = max(0.5, base_confidence)
            adjusted_confidence = min(0.95, confidence + self.continuity_bonus)
            
            logger.debug(f"Applied explicit continuity bonus to {current_agent_name}: "
                       f"{base_confidence:.2f} -> {adjusted_confidence:.2f}")
                       
            return adjusted_confidence
        else:
            # For time-based continuity, apply a reduced bonus
            adjusted_confidence = base_confidence + (self.continuity_bonus * 0.5)
            
            logger.debug(f"Applied time-based continuity bonus to {current_agent_name}: "
                       f"{base_confidence:.2f} -> {adjusted_confidence:.2f}")
                       
            return adjusted_confidence
            
    def rank_agents(self, agent_scores: List[Tuple[str, float, float, bool]]) -> List[Tuple[str, float, float, bool]]:
        """
        Rank agents by their adjusted confidence scores.
        
        Args:
            agent_scores: List of (agent_name, adjusted_confidence, base_confidence, context_used) tuples
            
        Returns:
            Sorted list of agent scores (highest confidence first)
        """
        return sorted(agent_scores, key=lambda x: x[1], reverse=True)
        
    def is_above_threshold(self, confidence: float) -> bool:
        """
        Check if confidence is above the threshold.
        
        Args:
            confidence: The confidence score
            
        Returns:
            True if confidence is above threshold
        """
        return confidence >= self.confidence_threshold
        
    def is_above_fallback_threshold(self, confidence: float, fallback_threshold: Optional[float] = None) -> bool:
        """
        Check if confidence is above the fallback threshold.
        
        Args:
            confidence: The confidence score
            fallback_threshold: Optional custom fallback threshold
            
        Returns:
            True if confidence is above fallback threshold
        """
        threshold = fallback_threshold or self.confidence_threshold * 0.7
        return confidence >= threshold
        
    def is_high_confidence(self, confidence: float) -> bool:
        """
        Check if confidence is high.
        
        Args:
            confidence: The confidence score
            
        Returns:
            True if confidence is high
        """
        return confidence >= self.high_confidence