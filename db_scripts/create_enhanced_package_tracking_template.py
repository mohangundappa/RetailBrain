"""
Script to create the Enhanced Package Tracking template in the database.
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import AgentTemplate

# Define the Enhanced Package Tracking template
ENHANCED_PACKAGE_TRACKING_TEMPLATE = {
    "name": "Enhanced Package Tracking",
    "description": "An advanced package tracking agent with proactive notifications, delivery exception handling, and detailed status updates. This template extends the basic Package Tracking agent with additional features for a better customer experience.",
    "category": "customer-service",
    "icon": "fas fa-box-open",
    "tags": "tracking,delivery,logistics,shipping,notifications,proactive",
    "is_featured": True,
    "is_system": True,
    "downloads": 0,
    "rating": 4.8,
    "rating_count": 12,
    "configuration": json.dumps({
        "agent_type": "package_tracking",
        "name": "Enhanced Package Tracking Agent",
        "description": "Advanced package tracking agent with proactive notifications and delivery exception handling",
        "components": [
            {
                "id": "package_tracking_prompt",
                "type": "prompt",
                "name": "Package Tracking Prompt",
                "content": """
You are a helpful package tracking assistant for Staples. Your role is to help customers track their packages and provide detailed information about delivery status.

Follow these guidelines:
1. Always respond in a friendly, professional manner representing Staples
2. Proactively analyze tracking information for potential delivery issues
3. Offer alternative solutions when delivery exceptions are detected
4. Provide estimated delivery windows when available
5. Check weather conditions that might impact delivery
6. Suggest helpful next steps based on package status

When handling a tracking request:
- Extract tracking number, order number, or other relevant information
- Provide comprehensive status updates including location, estimated delivery, and carrier information
- Alert customers to any delays or exceptions
- Offer to send SMS notifications for important status changes
- Provide alternative delivery options when issues arise
- Connect customers with appropriate support when needed

For packages that are delayed or have issues:
- Explain the nature of the delay or issue clearly
- Provide options for resolution including redelivery, pickup alternatives, or replacement
- Offer to connect the customer with a service representative when needed
- Present estimated resolution timelines when possible
"""
            },
            {
                "id": "package_tracking_llm",
                "type": "llm",
                "name": "Package Tracking LLM",
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_tokens": 1024
            },
            {
                "id": "delivery_exception_handler",
                "type": "tool",
                "name": "Delivery Exception Handler",
                "description": "Identifies delivery exceptions and provides resolution options",
                "configuration": {
                    "exception_types": [
                        "weather_delay", 
                        "address_issue", 
                        "damaged_package", 
                        "lost_package", 
                        "delivery_attempt_failed", 
                        "customs_delay"
                    ]
                }
            },
            {
                "id": "weather_impact_analyzer",
                "type": "tool",
                "name": "Weather Impact Analyzer",
                "description": "Analyzes weather conditions that may impact delivery",
                "configuration": {
                    "conditions_monitored": [
                        "severe_weather", 
                        "winter_storm", 
                        "flooding", 
                        "hurricane", 
                        "wildfire"
                    ]
                }
            },
            {
                "id": "notification_manager",
                "type": "tool",
                "name": "Notification Manager",
                "description": "Manages proactive notifications for package status changes",
                "configuration": {
                    "notification_events": [
                        "out_for_delivery", 
                        "delivery_exception", 
                        "delivered", 
                        "delayed", 
                        "returned_to_sender"
                    ],
                    "notification_channels": ["sms", "email"]
                }
            },
            {
                "id": "alternative_delivery_options",
                "type": "tool",
                "name": "Alternative Delivery Options",
                "description": "Provides alternative delivery options when issues arise",
                "configuration": {
                    "options": [
                        "hold_at_location", 
                        "redirect_to_store", 
                        "reschedule_delivery", 
                        "pickup_at_carrier_facility"
                    ]
                }
            },
            {
                "id": "package_tracking_parser",
                "type": "output_parser",
                "name": "Package Tracking Output Parser",
                "configuration": {
                    "fields": [
                        "tracking_number", 
                        "shipping_carrier", 
                        "order_number", 
                        "status",
                        "estimated_delivery", 
                        "current_location", 
                        "delivery_exception", 
                        "resolution_options",
                        "weather_impact", 
                        "next_steps", 
                        "notification_preferences"
                    ],
                    "format": "json"
                }
            }
        ],
        "connections": [
            {"source": "package_tracking_prompt", "target": "package_tracking_llm"},
            {"source": "package_tracking_llm", "target": "package_tracking_parser"},
            {"source": "delivery_exception_handler", "target": "package_tracking_llm"},
            {"source": "weather_impact_analyzer", "target": "package_tracking_llm"},
            {"source": "notification_manager", "target": "package_tracking_llm"},
            {"source": "alternative_delivery_options", "target": "package_tracking_llm"}
        ],
        "default_memory": {
            "type": "conversation_buffer",
            "max_history": 10
        },
        "metadata": {
            "supports_sms": True,
            "supports_email": True,
            "requires_api_keys": False,
            "version": "1.0.0",
            "created": datetime.now().isoformat()
        }
    })
}

def create_enhanced_package_tracking_template():
    """Create the Enhanced Package Tracking template in the database."""
    with app.app_context():
        # Check if the template already exists
        existing_template = AgentTemplate.query.filter_by(name=ENHANCED_PACKAGE_TRACKING_TEMPLATE["name"]).first()
        
        if existing_template:
            print(f"Template '{ENHANCED_PACKAGE_TRACKING_TEMPLATE['name']}' already exists with id {existing_template.id}")
            return
        
        # Create the template
        template = AgentTemplate(**ENHANCED_PACKAGE_TRACKING_TEMPLATE)
        
        # Add and commit to database
        db.session.add(template)
        db.session.commit()
        
        print(f"Created Enhanced Package Tracking template with id {template.id}")

if __name__ == "__main__":
    create_enhanced_package_tracking_template()