"""
Constants for agent configuration and operation in Staples Brain.

This module defines constants used throughout the agent orchestration system,
including confidence thresholds, timeouts, and other parameters that affect
agent selection and behavior.
"""

# Confidence thresholds for agent selection
DEFAULT_CONFIDENCE_THRESHOLD = 0.65
HIGH_CONFIDENCE_THRESHOLD = 0.85
MIN_CONFIDENCE_THRESHOLD = 0.3
MAX_CONFIDENCE_THRESHOLD = 0.9

# Special case detection thresholds
GREETING_CONFIDENCE = 0.7
CONVERSATION_END_CONFIDENCE = 0.7
HUMAN_TRANSFER_CONFIDENCE = 0.7
HOLD_REQUEST_CONFIDENCE = 0.8

# Agent selection parameters
CONTINUITY_BONUS = 0.15
NEGATIVE_FEEDBACK_PENALTY = 0.2
SEMANTIC_RELEVANCE_WEIGHT = 0.1

# Conversation memory parameters
CONTEXT_WINDOW = 5  # Number of turns to keep in immediate context
MEMORY_EXPIRATION_SECONDS = 3600  # 1 hour

# Agent timeouts (in seconds)
AGENT_TIMEOUTS = {
    'default': 10,
    'package_tracking': 15,
    'store_locator': 8,
    'product_info': 12,
    'reset_password': 8
}

# Intent-to-agent mapping
INTENT_AGENT_MAPPING = {
    'package_tracking': 'package_tracking',
    'order_status': 'package_tracking',
    'track_shipment': 'package_tracking',
    'reset_password': 'reset_password',
    'password_help': 'reset_password',
    'find_store': 'store_locator',
    'store_hours': 'store_locator',
    'product_information': 'product_info',
    'product_availability': 'product_info',
    'product_compatibility': 'product_info'
}

# Agent type constants

# Legacy agent types (kept for backward compatibility)
PACKAGE_TRACKING_AGENT = "package_tracking"
RESET_PASSWORD_AGENT = "reset_password"
STORE_LOCATOR_AGENT = "store_locator"
PRODUCT_INFO_AGENT = "product_info"
RETURNS_PROCESSING_AGENT = "returns_processing"

# New agent type classification system
AGENT_TYPE_BUILT_IN = "BUILT_IN"
AGENT_TYPE_CUSTOM = "CUSTOM"
AGENT_TYPE_KNOWLEDGE = "KNOWLEDGE"
AGENT_TYPE_PROCESS = "PROCESS"
AGENT_TYPE_TRACKER = "TRACKER"
AGENT_TYPE_SMALL_TALK = "SMALL_TALK"
AGENT_TYPE_FALLBACK = "FALLBACK"

# Mapping from legacy types to new classification
AGENT_TYPE_MAPPING = {
    "package_tracking": AGENT_TYPE_TRACKER,
    "reset_password": AGENT_TYPE_PROCESS,
    "store_locator": AGENT_TYPE_KNOWLEDGE,
    "product_info": AGENT_TYPE_KNOWLEDGE,
    "returns_processing": AGENT_TYPE_PROCESS,
    "policy-enforcer": AGENT_TYPE_BUILT_IN,
    "llm-driven": AGENT_TYPE_SMALL_TALK
}