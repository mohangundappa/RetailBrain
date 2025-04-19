"""
Entity definition module for agent data collection.

This module provides the EntityDefinition class that defines
requirements for entity collection by agents, including validation
patterns and metadata.
"""
import re
from typing import Dict, Any, List, Optional

class EntityDefinition:
    """
    Define entity requirements for agent data collection.
    """
    
    def __init__(self, 
                 name: str, 
                 required: bool = True, 
                 validation_pattern: Optional[str] = None,
                 error_message: Optional[str] = None,
                 description: Optional[str] = None,
                 examples: Optional[List[str]] = None,
                 alternate_names: Optional[List[str]] = None):
        """
        Initialize an entity definition.
        
        Args:
            name: The name of the entity (e.g., 'order_number', 'zip_code')
            required: Whether this entity is required for the agent to proceed
            validation_pattern: A regex pattern to validate the entity value
            error_message: Custom error message when validation fails
            description: A description of the entity for the user
            examples: Example values for this entity
            alternate_names: Other names this entity might be called in user input
        """
        self.name = name
        self.required = required
        self.validation_pattern = validation_pattern
        self.error_message = error_message or f"Please provide a valid {name.replace('_', ' ')}."
        self.description = description or f"The {name.replace('_', ' ')} for this request."
        self.examples = examples or []
        self.alternate_names = alternate_names or []
        self.collected = False
        self.value: Optional[str] = None
        self.attempts = 0
        self.max_attempts = 3  # Maximum attempts to collect this entity

    def is_valid(self, value: str) -> bool:
        """
        Validate the entity value against the pattern if provided.
        
        Args:
            value: The value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not value:
            return False
            
        if not self.validation_pattern:
            return True
            
        return bool(re.match(self.validation_pattern, value))
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entity definition to a dictionary.
        
        Returns:
            A dictionary representation of the entity
        """
        return {
            "name": self.name,
            "required": self.required,
            "description": self.description,
            "examples": self.examples,
            "collected": self.collected,
            "value": self.value,
            "attempts": self.attempts
        }