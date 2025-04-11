"""
Configuration classes for the orchestration system.
These classes provide centralized configuration for the orchestrator and related components.
"""
from typing import Dict, List, Any


class OrchestratorConfig:
    """Configuration for the Agent Orchestrator."""
    
    def __init__(self,
                confidence_threshold: float = 0.3,
                high_confidence_threshold: float = 0.7,
                continuity_bonus: float = 0.2,
                recency_window: int = 300,
                max_history: int = 20,
                fallback_threshold: float = 0.21):  # 0.3 * 0.7
        """
        Initialize orchestrator configuration with customizable parameters.
        
        Args:
            confidence_threshold: Minimum confidence required to select an agent
            high_confidence_threshold: Threshold for high confidence in intent routing
            continuity_bonus: Bonus applied when continuing with the same agent
            recency_window: Time window in seconds for considering context from previous interactions
            max_history: Maximum number of past interactions to store
            fallback_threshold: Lower threshold used for fallback scenarios
        """
        self.confidence_threshold = confidence_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.continuity_bonus = continuity_bonus
        self.recency_window = recency_window
        self.max_history = max_history
        self.fallback_threshold = fallback_threshold
        
    @classmethod
    def from_constants(cls, constants_module) -> 'OrchestratorConfig':
        """
        Create config from a constants module.
        
        Args:
            constants_module: Module containing configuration constants
            
        Returns:
            New OrchestratorConfig instance
        """
        return cls(
            confidence_threshold=getattr(constants_module, 'DEFAULT_CONFIDENCE_THRESHOLD', 0.3),
            high_confidence_threshold=getattr(constants_module, 'HIGH_CONFIDENCE_THRESHOLD', 0.7),
            continuity_bonus=getattr(constants_module, 'CONTINUITY_BONUS', 0.2),
        )


class IntentMappingConfig:
    """Configuration for intent-to-agent mapping."""
    
    def __init__(self, intent_mapping: Dict[str, str]):
        """
        Initialize with an intent-to-agent mapping.
        
        Args:
            intent_mapping: Dictionary mapping intent names to agent names
        """
        self.intent_mapping = intent_mapping
    
    def get_agent_for_intent(self, intent: str) -> str:
        """
        Get the agent name for a given intent.
        
        Args:
            intent: The intent name
            
        Returns:
            Agent name or None if no mapping exists
        """
        return self.intent_mapping.get(intent)
    
    @classmethod
    def from_constants(cls, constants_module) -> 'IntentMappingConfig':
        """
        Create config from a constants module.
        
        Args:
            constants_module: Module containing INTENT_AGENT_MAPPING
            
        Returns:
            New IntentMappingConfig instance
        """
        return cls(
            intent_mapping=getattr(constants_module, 'INTENT_AGENT_MAPPING', {})
        )