"""
Entity collection state tracking for agent conversations.

This module provides the EntityCollectionState class that tracks
the state of entity collection during agent conversations,
managing the flow of collecting required information from users.
"""
from typing import Dict, Any, List, Optional

from backend.agents.framework.entity_definition import EntityDefinition

class EntityCollectionState:
    """
    Track the state of entity collection for an agent conversation.
    """
    
    def __init__(self):
        """Initialize the entity collection state."""
        self.entities: Dict[str, EntityDefinition] = {}
        self.entity_definitions: List[EntityDefinition] = []  # Store a list of entity definitions for reference
        self.current_entity: Optional[str] = None
        self.is_collecting = False
        self.max_collection_turns = 5  # Maximum conversation turns for entity collection
        self.collection_turns = 0
        self.exit_condition_met = False
        self.exit_reason = None
        
    def add_entity(self, entity: EntityDefinition) -> None:
        """
        Add an entity to collect.
        
        Args:
            entity: The entity definition
        """
        self.entities[entity.name] = entity
        self.entity_definitions.append(entity)  # Add to the list of entity definitions
        
    def set_value(self, entity_name: str, value: str) -> bool:
        """
        Set a value for an entity and validate it.
        
        Args:
            entity_name: The name of the entity
            value: The value to set
            
        Returns:
            True if the value is valid, False otherwise
        """
        if entity_name not in self.entities:
            return False
            
        entity = self.entities[entity_name]
        
        if entity.is_valid(value):
            # Cast to Optional[str] to satisfy type checker
            entity.value = value  # type: ignore
            entity.collected = True
            return True
        else:
            entity.attempts += 1
            
            # If we've exceeded max attempts, mark as exit condition
            if entity.attempts >= entity.max_attempts:
                self.exit_condition_met = True
                self.exit_reason = f"max_attempts_exceeded_for_{entity_name}"
                
            return False
            
    def get_next_missing_entity(self) -> Optional[str]:
        """
        Get the name of the next required entity that hasn't been collected.
        
        Returns:
            The name of the next entity to collect, or None if all required entities are collected
        """
        for name, entity in self.entities.items():
            if entity.required and not entity.collected:
                return name
        return None
        
    def get_missing_entities(self) -> List[str]:
        """
        Get a list of all required entities that haven't been collected.
        
        Returns:
            A list of entity names
        """
        return [name for name, entity in self.entities.items() 
                if entity.required and not entity.collected]
        
    def are_all_required_entities_collected(self) -> bool:
        """
        Check if all required entities have been collected.
        
        Returns:
            True if all required entities are collected, False otherwise
        """
        for entity in self.entities.values():
            if entity.required and not entity.collected:
                return False
        return True
        
    def get_collected_entities(self) -> Dict[str, Any]:
        """
        Get all collected entity values.
        
        Returns:
            A dictionary of entity names and their values
        """
        return {name: entity.value for name, entity in self.entities.items() 
                if entity.collected}
                
    def should_exit_collection(self) -> bool:
        """
        Determine if we should exit the entity collection process.
        
        Returns:
            True if we should exit, False otherwise
        """
        # Exit if all required entities are collected
        if self.are_all_required_entities_collected():
            self.exit_condition_met = True
            self.exit_reason = "all_required_entities_collected"
            return True
            
        # Exit if we've exceeded max collection turns
        if self.collection_turns >= self.max_collection_turns:
            self.exit_condition_met = True
            self.exit_reason = "max_collection_turns_exceeded"
            return True
            
        # Exit if an explicit exit condition has been met
        return self.exit_condition_met
        
    def increment_turn(self) -> None:
        """Increment the collection turn counter."""
        self.collection_turns += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the collection state to a dictionary.
        
        Returns:
            A dictionary representation of the collection state
        """
        return {
            "entities": {name: entity.to_dict() for name, entity in self.entities.items()},
            "current_entity": self.current_entity,
            "is_collecting": self.is_collecting,
            "collection_turns": self.collection_turns,
            "max_collection_turns": self.max_collection_turns,
            "exit_condition_met": self.exit_condition_met,
            "exit_reason": self.exit_reason
        }