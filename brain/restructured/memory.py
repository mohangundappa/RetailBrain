"""
Memory management for the orchestration system.
This module handles conversation memory, entity extraction, and context preservation.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class OrchestrationMemory:
    """Memory management for agent orchestration."""
    
    def __init__(self, session_id: str, max_history: int = 20):
        """
        Initialize memory for a session.
        
        Args:
            session_id: The unique session identifier
            max_history: Maximum number of items to store in history
        """
        self.session_id = session_id
        self.working_memory = {}  # Short-term, in-memory context
        self.entities = {}        # Extracted entities storage
        self.agent_history = []   # Track agent routing decisions
        self.max_history = max_history
        
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """
        Get a value from working memory.
        
        Args:
            key: The memory key
            default: Default value if key doesn't exist
            
        Returns:
            The stored value or default
        """
        return self.working_memory.get(key, default)
        
    def update_working_memory(self, key: str, value: Any) -> None:
        """
        Update a value in working memory.
        
        Args:
            key: The memory key
            value: The value to store
        """
        self.working_memory[key] = value
        
    def get_entity(self, name: str) -> Optional[Any]:
        """
        Get a specific entity by name.
        
        Args:
            name: The entity name
            
        Returns:
            The entity value or None if not found
        """
        return self.entities.get(name)
        
    def add_entity(self, name: str, value: Any) -> None:
        """
        Add or update an entity.
        
        Args:
            name: The entity name
            value: The entity value
        """
        self.entities[name] = value
        # Also update working memory with entity_X for easier access
        self.update_working_memory(f"entity_{name}", value)
        
    def add_entities(self, entities: Dict[str, Any]) -> None:
        """
        Add multiple entities at once.
        
        Args:
            entities: Dictionary of entity name/value pairs
        """
        for name, value in entities.items():
            if value:  # Only store non-empty values
                self.add_entity(name, value)
        
        # Update a combined entities dictionary in working memory
        self.update_working_memory("entities", self.entities)
        
    def record_agent_selection(self, agent_name: str, confidence: float, 
                             intent: Optional[str] = None,
                             context_used: bool = False) -> None:
        """
        Record an agent selection for this session.
        
        Args:
            agent_name: The selected agent's name
            confidence: The confidence score
            intent: The detected intent (if any)
            context_used: Whether context contributed to this selection
        """
        selection = {
            "agent": agent_name,
            "confidence": confidence,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "context_used": context_used
        }
        
        self.agent_history.append(selection)
        
        # Trim history to max_history entries
        if len(self.agent_history) > self.max_history:
            self.agent_history = self.agent_history[-self.max_history:]
            
        # Update working memory with last agent for easier access
        self.update_working_memory("last_selected_agent", agent_name)
        self.update_working_memory("last_confidence", confidence)
        self.update_working_memory("last_intent", intent)
        
    def get_recent_agent(self) -> Optional[str]:
        """
        Get the most recently used agent, if any.
        
        Returns:
            The most recent agent name or None if no history
        """
        if not self.agent_history:
            return None
            
        return self.agent_history[-1]["agent"]
        
    def get_last_timestamp(self) -> Optional[str]:
        """
        Get the timestamp of the last interaction.
        
        Returns:
            ISO formatted timestamp or None if no history
        """
        if not self.agent_history:
            return None
            
        return self.agent_history[-1]["timestamp"]
        
    def get_context(self) -> Dict[str, Any]:
        """
        Get the full context with all memory data.
        
        Returns:
            Dictionary with all memory contents
        """
        return {
            "session_id": self.session_id,
            "working_memory": self.working_memory,
            "entities": self.entities,
            "agent_history": self.agent_history
        }
        
    def should_continue_with_same_agent(self) -> bool:
        """
        Check if the conversation should continue with the same agent.
        
        Returns:
            True if the conversation should continue with the same agent
        """
        return self.get_working_memory("continue_with_same_agent", False)
        
    def mark_continue_with_same_agent(self, continue_flag: bool = True) -> None:
        """
        Mark whether to continue with the same agent.
        
        Args:
            continue_flag: Whether to continue with the same agent
        """
        self.update_working_memory("continue_with_same_agent", continue_flag)