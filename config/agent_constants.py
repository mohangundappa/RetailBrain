"""
Constants for agent configuration.
This file provides a single source of truth for agent names and other constants.
"""

# Agent Names
PACKAGE_TRACKING_AGENT = "Package Tracking Agent"
RESET_PASSWORD_AGENT = "Reset Password Agent" 
STORE_LOCATOR_AGENT = "Store Locator Agent"
PRODUCT_INFO_AGENT = "Product Information Agent"

# Confidence Thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence required to select an agent
HIGH_CONFIDENCE_THRESHOLD = 0.7     # Threshold for high confidence
CONTINUITY_BONUS = 0.2              # Bonus added when continuing with the same agent

# Intent to Agent Mapping
INTENT_AGENT_MAPPING = {
    # Package Tracking intents
    "package_tracking": PACKAGE_TRACKING_AGENT,
    "order_status": PACKAGE_TRACKING_AGENT,
    "shipping_inquiry": PACKAGE_TRACKING_AGENT,
    "delivery_status": PACKAGE_TRACKING_AGENT,
    "package_location": PACKAGE_TRACKING_AGENT,
    
    # Reset Password intents
    "password_reset": RESET_PASSWORD_AGENT,
    "account_access": RESET_PASSWORD_AGENT,
    "login_issue": RESET_PASSWORD_AGENT,
    "forgot_password": RESET_PASSWORD_AGENT,
    
    # Store Locator intents
    "store_locator": STORE_LOCATOR_AGENT,
    "store_hours": STORE_LOCATOR_AGENT,
    "store_services": STORE_LOCATOR_AGENT,
    
    # Product Information intents
    "product_info": PRODUCT_INFO_AGENT,
    "product_comparison": PRODUCT_INFO_AGENT,
    "product_recommendation": PRODUCT_INFO_AGENT
}