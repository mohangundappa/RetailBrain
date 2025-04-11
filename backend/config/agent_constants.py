"""
Constants for agent configuration in Staples Brain.
"""

# Mapping from intents to agent names
INTENT_AGENT_MAPPING = {
    "package_tracking": "package_tracking",
    "password_reset": "reset_password",
    "store_locator": "store_locator",
    "product_info": "product_info",
    "returns": "returns_processing",
    "help": None,  # "help" intent doesn't map to a specific agent
    "greeting": None,  # "greeting" intent doesn't map to a specific agent
    "fallback": None,  # When no clear intent is found
}

# Confidence thresholds for orchestrator
DEFAULT_CONFIDENCE_THRESHOLD = 0.65  # Minimum confidence to consider an intent valid
HIGH_CONFIDENCE_THRESHOLD = 0.85    # Threshold for "high confidence" intents
CONTINUITY_BONUS = 0.15             # Bonus applied to continue with the same agent

# Number of turns to look back for context
CONTEXT_WINDOW = 5

# Common agent configuration
DEFAULT_AGENT_CONFIG = {
    "max_recursion_depth": 3,       # Maximum depth for recursive agent calls
    "context_window_size": 10,      # Number of messages to include in LLM context
    "default_temperature": 0.2,     # Default temperature for LLM calls
    "max_tokens_per_call": 1024,    # Max tokens for output
    "response_format": "markdown",  # Default response format
}

# Default memory access permissions for agents
DEFAULT_AGENT_PERMISSIONS = {
    "package_tracking": ["order_data", "tracking_info", "user_data"],
    "reset_password": ["user_data", "account_info"],
    "store_locator": ["location_data", "store_inventory"],
    "product_info": ["product_data", "inventory", "pricing"],
    "returns_processing": ["order_data", "return_policy", "shipping_info"],
}

# Circuit breaker settings for external API calls
API_CIRCUIT_BREAKER = {
    "failure_threshold": 5,         # Number of failures before circuit opens
    "recovery_timeout": 30,         # Seconds to wait before trying again
    "timeout": 10,                  # API call timeout in seconds
    "backoff_factor": 2,            # Exponential backoff factor
    "max_retries": 3,               # Maximum retry attempts
}

# Agent response timeouts (seconds)
AGENT_TIMEOUTS = {
    "package_tracking": 15,
    "reset_password": 10,
    "store_locator": 12,
    "product_info": 12,
    "returns_processing": 15,
    "default": 20,                  # Default timeout for other agents
}