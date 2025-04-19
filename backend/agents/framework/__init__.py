"""
Agent framework module for Staples Brain.

This module provides the base classes and utilities for agent implementation,
including the BaseAgent abstract class, guardrails, entity definitions, and
entity collection state tracking.
"""

# Re-export all classes to maintain backward compatibility
from .guardrails import GuardrailViolation, Guardrails
from .entity_definition import EntityDefinition
from .entity_collection_state import EntityCollectionState
from .base_agent import BaseAgent

# For backward compatibility with existing import patterns
__all__ = [
    'GuardrailViolation',
    'Guardrails',
    'EntityDefinition',
    'EntityCollectionState',
    'BaseAgent',
]