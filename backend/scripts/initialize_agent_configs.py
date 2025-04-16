"""
Initialize agent configurations in the database.
This script populates the database with system prompts and workflows
for the standard agents in the system.
"""
import asyncio
import logging
import json
import os
import uuid
from typing import Dict, Any, List

import asyncpg

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent configuration templates
AGENT_CONFIGS = {
    "reset_password": {
        "name": "Reset Password Agent",
        "description": "Reset password flow: The password reset process requires the user to provide an email address associated to his account, once the email is provided a reset password email will be sent to his email if the email is associated to a staples account.",
        "agent_type": "reset_password",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "reset password", "priority": 1, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "forgot password", "priority": 2, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "change password", "priority": 3, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "login problem", "priority": 4, "confidence_boost": 0.6}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are a helpful assistant specialized in helping users reset their password for Staples accounts.

Reset password flow: The password reset process requires the user to provide an email address associated to his account. Once the email is provided, a reset password email will be sent to his email if the email is associated with a Staples account.

Follow these steps:
1. Ask the user for their email address if they haven't provided it
2. Once you have the email, inform them that a password reset link has been sent to their email address
3. Instruct them to check their inbox (and spam folder) for the reset password email
4. Let them know they can return to the Staples website and use the reset link to create a new password

Be courteous, professional, and security-conscious throughout the interaction.
Do not ask for or accept sensitive information like current passwords.

If the user asks for help with anything unrelated to password reset, inform them that you're specialized in password resets, but you'd be happy to connect them with someone who can assist with their other needs.""",
                "description": "Main system prompt for Reset Password Agent",
                "variables": None
            },
            {
                "prompt_type": "email_extraction",
                "content": """Extract the email address from the user's message if present. Return a JSON object with the following structure:
{
    "email": "user@example.com"  // The extracted email address, or null if not found
}

Ensure you extract only valid email addresses in the format user@domain.tld. If multiple email addresses are present, extract the one that appears to be the user's account email.""",
                "description": "Prompt for extracting email addresses from user messages",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Password Reset Flow",
            "description": "Workflow for handling password reset requests",
            "nodes": [
                {
                    "name": "check_email",
                    "node_type": "extraction",
                    "function_name": "extract_email",
                    "prompt_type": "email_extraction",
                    "response_template": None,
                    "config": {"required": True}
                },
                {
                    "name": "request_email",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "To reset your password, I'll need your email address. What email address is associated with your Staples account?",
                    "config": {}
                },
                {
                    "name": "confirm_reset",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "Thank you. I've sent a password reset link to {data.extraction.email}. Please check your inbox (and spam folder) for an email from Staples with instructions to reset your password. Once you receive it, click the link in the email to create a new password. Is there anything else I can help you with?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "check_email", "target": "request_email", "condition_type": "conditional", "condition_value": "null", "priority": 1},
                {"source": "check_email", "target": "confirm_reset", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "request_email", "target": "check_email", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "confirm_reset", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    },
    "product_search": {
        "name": "Product Search Agent",
        "description": "Product search flow: The product search flow is defined by a user trying to find a product in the website. This process requires the user to give a brief description of the product/item he is looking for in the website or product/item he wants to buy, if the user doesn't provide a clear description, ask for details. In case the user provides additional details or changes the description, return the updated or combined description in the productDescription field.",
        "agent_type": "product_search",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "find product", "priority": 1, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "looking for", "priority": 2, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "search for", "priority": 3, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "do you have", "priority": 4, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "want to buy", "priority": 5, "confidence_boost": 0.7}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are a helpful Staples product search assistant.

Product search flow: This process helps users find products in the Staples website. Your job is to:

1. Have the user provide a description of the product/item they're looking for
2. If the description isn't clear enough, ask for more specific details
3. If the user provides additional details or changes the description, update your understanding accordingly
4. Help guide the user to the right product category

Be friendly and helpful. Focus on understanding exactly what product the customer is looking for, including specific features, brands, or requirements they might have.

If you don't have enough information, ask clarifying questions to narrow down the search.""",
                "description": "Main system prompt for Product Search Agent",
                "variables": None
            },
            {
                "prompt_type": "product_extraction",
                "content": """Extract the product description from the user's message. Return a JSON object with the following structure:
{
    "productDescription": "detailed description of the product",  // The product the user is looking for, or null if not clear
    "productCategory": "category if identifiable",  // Product category if mentioned, or null
    "specificRequirements": ["requirement1", "requirement2"]  // Any specific features or requirements, or empty array
}

If the user's request isn't clear enough to identify a product, return null for productDescription and provide guidance on what additional information would be helpful.""",
                "description": "Prompt for extracting product information from user messages",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Product Search Flow",
            "description": "Workflow for handling product search requests",
            "nodes": [
                {
                    "name": "extract_product",
                    "node_type": "extraction",
                    "function_name": "extract_product",
                    "prompt_type": "product_extraction",
                    "response_template": None, 
                    "config": {"required": True}
                },
                {
                    "name": "request_details",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'd be happy to help you find what you're looking for. Could you please provide more details about the product you need? For example, specific features, brand preferences, or how you plan to use it?",
                    "config": {}
                },
                {
                    "name": "confirm_search",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'll help you find {data.extraction.productDescription}. Let me search for products that match your requirements. Is there anything specific about this product that's particularly important to you, such as price range, brand, or specific features?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "extract_product", "target": "request_details", "condition_type": "conditional", "condition_value": "null", "priority": 1},
                {"source": "extract_product", "target": "confirm_search", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "request_details", "target": "extract_product", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "confirm_search", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    },
    "greeting": {
        "name": "Greeting and Thank You Agent",
        "description": "Greeting and thank you flow: In case the user sends a thanks or greeting message, consider the current conversation over, reply back with a thank you message and ask if he needs help with something else.",
        "agent_type": "greeting",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "hello", "priority": 1, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "hi", "priority": 2, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "hey", "priority": 3, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "thanks", "priority": 4, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "thank you", "priority": 5, "confidence_boost": 0.9}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are a friendly Staples customer service assistant.

When users greet you or thank you:
1. Respond with a warm and professional greeting or acknowledgment
2. Consider the current phase of conversation as complete 
3. Ask if they need help with something else or have any other questions
4. Be ready to direct them to specific assistance if they mention a new topic

Keep responses short, friendly, and focused on how you can help them next.""",
                "description": "Main system prompt for Greeting Agent",
                "variables": None
            },
            {
                "prompt_type": "greeting_detection",
                "content": """Determine if the user's message is a greeting or expression of thanks. Return a JSON object with the following structure:
{
    "messageType": "greeting | thanks | other",  // The type of message detected
    "intensity": "casual | standard | formal"     // The level of formality detected
}

If the message contains both a greeting and thanks, prioritize the thanks classification.""",
                "description": "Prompt for detecting greetings and thank you messages",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Greeting and Thank You Flow",
            "description": "Workflow for handling greetings and expressions of thanks",
            "nodes": [
                {
                    "name": "detect_message_type",
                    "node_type": "extraction",
                    "function_name": "detect_greeting",
                    "prompt_type": "greeting_detection",
                    "response_template": None,
                    "config": {"required": True}
                },
                {
                    "name": "respond_to_greeting",
                    "node_type": "response",
                    "function_name": None, 
                    "prompt_type": None,
                    "response_template": "Hello! Welcome to Staples customer service. How can I assist you today?",
                    "config": {}
                },
                {
                    "name": "respond_to_thanks",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "You're welcome! I'm glad I could help. Is there anything else you need assistance with today?",
                    "config": {}
                },
                {
                    "name": "default_response",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "Thank you for reaching out to Staples customer service. How can I assist you today?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "detect_message_type", "target": "respond_to_greeting", "condition_type": "conditional", "condition_value": "greeting", "priority": 1},
                {"source": "detect_message_type", "target": "respond_to_thanks", "condition_type": "conditional", "condition_value": "thanks", "priority": 2},
                {"source": "detect_message_type", "target": "default_response", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "respond_to_greeting", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "respond_to_thanks", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "default_response", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    },
    "human_transfer": {
        "name": "Transfer to Human Agent",
        "description": "The transfer to human flow works when the user objectively asks to talk with a human or for assistance",
        "agent_type": "human_transfer",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "speak to human", "priority": 1, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "talk to agent", "priority": 2, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "real person", "priority": 3, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "customer service", "priority": 4, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "speak to representative", "priority": 5, "confidence_boost": 0.9}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are an assistant responsible for transferring users to human agents when requested.

The transfer to human flow should be triggered when:
1. A user explicitly asks to speak with a human agent or representative
2. A user requests assistance that clearly requires human intervention
3. A user expresses frustration with automated assistance

When this occurs, acknowledge their request politely, assure them that you'll connect them with a human agent, and provide any necessary information about the transfer process.""",
                "description": "Main system prompt for Transfer to Human Agent",
                "variables": None
            },
            {
                "prompt_type": "transfer_detection",
                "content": """Determine if the user is requesting to be transferred to a human agent. Return a JSON object with the following structure:
{
    "transferRequested": true|false,  // Whether a transfer has been explicitly requested
    "reason": "string",               // The reason for the transfer request, if applicable
    "urgency": "low|medium|high"      // The perceived urgency of the request
}

Look for explicit phrases like "talk to a human", "speak with an agent", "real person", as well as indications of frustration or complex issues that might require human intervention.""",
                "description": "Prompt for detecting human transfer requests",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Transfer to Human Flow",
            "description": "Workflow for handling transfers to human agents",
            "nodes": [
                {
                    "name": "detect_transfer_request",
                    "node_type": "extraction",
                    "function_name": "detect_transfer",
                    "prompt_type": "transfer_detection",
                    "response_template": None,
                    "config": {"required": True}
                },
                {
                    "name": "confirm_transfer",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I understand you'd like to speak with a human agent. I'll connect you to a customer service representative right away. Please stay on the line and a Staples team member will assist you shortly. Is there any specific information about your inquiry that I can pass along to the agent?",
                    "config": {}
                },
                {
                    "name": "no_transfer_needed",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'm here to help you with your request. Could you please provide more details about what you need assistance with, and I'll do my best to help or direct you to the right resource?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "detect_transfer_request", "target": "confirm_transfer", "condition_type": "conditional", "condition_value": "true", "priority": 1},
                {"source": "detect_transfer_request", "target": "no_transfer_needed", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "confirm_transfer", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "no_transfer_needed", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    },
    "package_tracking": {
        "name": "Package Tracking Agent",
        "description": "Package tracking flow: The package tracking, order tracking or product tracking process consists in finding where the products purchased by the customers are. It requires the user to provide an order number that is a sequence of numeric numbers between 8 and 10 digits and the zip code to where the order will be delivered. Look for information in the context to provide the response. If the order number is ORDER_DETAILS map, use the json provided as part of the values in the map to provide a response based on the tracking status on each line. Provide the response in bullet points containing the sku, productDescription, trackingStatus and expectedDeliveryDate. In case the customer wants additional information related to the order, user the ORDER_DETAILS map to provide the answer. In case you don't have the order data in ORDER_DETAILS_MAP, tell the user you are looking for his order tracking details. In case the customer do not have the order number or zip code transfer the user to a human.",
        "agent_type": "package_tracking",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "track package", "priority": 1, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "track order", "priority": 2, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "where is my order", "priority": 3, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "delivery status", "priority": 4, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "shipping status", "priority": 5, "confidence_boost": 0.8}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are a package tracking assistant for Staples.

Package tracking flow: Your goal is to help customers track their orders and provide them with accurate delivery information. 

To provide tracking information you need:
1. An order number (8-10 digits)
2. The delivery zip code

When providing tracking details:
- Format the response in bullet points
- Include the SKU, product description, tracking status, and expected delivery date
- If additional order information is requested, provide it from available order data
- If order data is not available, inform the customer you are looking up their tracking details
- If the customer doesn't have their order number or zip code, offer to transfer them to a human agent

Be efficient, accurate, and focus on providing exactly the information the customer needs about their delivery.""",
                "description": "Main system prompt for Package Tracking Agent",
                "variables": None
            },
            {
                "prompt_type": "order_extraction",
                "content": """Extract the order tracking information from the user's message. Return a JSON object with the following structure:
{
    "orderNumber": "string",  // The order number (8-10 digit number), or null if not provided
    "zipCode": "string",      // The delivery zip code, or null if not provided
    "specifics": "string"     // Any specific question about the order (e.g., "when will it arrive?")
}

If multiple order numbers are mentioned, extract the one that appears to be the main subject of the inquiry.""",
                "description": "Prompt for extracting order information from user messages",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Package Tracking Flow",
            "description": "Workflow for handling package tracking requests",
            "nodes": [
                {
                    "name": "extract_order_info",
                    "node_type": "extraction",
                    "function_name": "extract_order_info",
                    "prompt_type": "order_extraction",
                    "response_template": None,
                    "config": {"required": True}
                },
                {
                    "name": "request_order_number",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'd be happy to help you track your package. Could you please provide your order number? It should be an 8-10 digit number found on your order confirmation email or receipt.",
                    "config": {}
                },
                {
                    "name": "request_zip_code",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "Thank you for providing your order number. Could you also share the zip code where the order is being delivered to? This helps me verify and provide accurate tracking information.",
                    "config": {}
                },
                {
                    "name": "provide_tracking",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "Thank you. I've found your order {data.extraction.orderNumber}. Here's the current status of your items:\n\n• Item: [Product Name]\n  Status: [Shipping Status]\n  Expected Delivery: [Date]\n\nIs there anything specific about this order you'd like to know?",
                    "config": {}
                },
                {
                    "name": "offer_human_transfer",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I understand you don't have all the information needed to track your order. I'd be happy to connect you with a customer service representative who can help you further. Would you like me to transfer you to a human agent?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "extract_order_info", "target": "request_order_number", "condition_type": "conditional", "condition_value": "null_order", "priority": 1},
                {"source": "extract_order_info", "target": "request_zip_code", "condition_type": "conditional", "condition_value": "null_zip", "priority": 2},
                {"source": "extract_order_info", "target": "provide_tracking", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "request_order_number", "target": "extract_order_info", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "request_zip_code", "target": "extract_order_info", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "provide_tracking", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "offer_human_transfer", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    },
    "order_cancellation": {
        "name": "Order Cancellation Agent",
        "description": "Order cancellation flow: The cancel process has two options: 1 - Cancel the entire order. 2 - Cancel only a subset of the order lines in the order. In case the user wants to cancel the entire order he needs to provide only an order number that is a sequence of numeric numbers between 8 and 10 digits, a customer number,a zip code, an email address and a reason. Only order number and customer are mandatory. In case the user wants to cancel a subset of the order lines in the order the user needs to provide an order number, a zip code, customer number and also the products he wants to cancel",
        "agent_type": "order_cancellation",
        "status": "active",
        "is_system": True,
        "patterns": [
            {"pattern_type": "keyword", "pattern_value": "cancel order", "priority": 1, "confidence_boost": 0.9},
            {"pattern_type": "keyword", "pattern_value": "cancel my purchase", "priority": 2, "confidence_boost": 0.8},
            {"pattern_type": "keyword", "pattern_value": "stop delivery", "priority": 3, "confidence_boost": 0.7},
            {"pattern_type": "keyword", "pattern_value": "don't want item", "priority": 4, "confidence_boost": 0.6},
            {"pattern_type": "keyword", "pattern_value": "remove from order", "priority": 5, "confidence_boost": 0.7}
        ],
        "prompts": [
            {
                "prompt_type": "main",
                "content": """You are an order cancellation assistant for Staples.

Order cancellation flow: You need to determine if the customer wants to:
1. Cancel an entire order - Requires order number (mandatory), customer number (mandatory), and optionally zip code, email address, and reason
2. Cancel specific items from an order - Requires order number, customer number, zip code, and identification of which products to cancel

Your role is to:
- Collect all required information
- Clearly explain the cancellation process 
- Confirm the customer's intent before proceeding
- Provide appropriate expectations about the cancellation

Be direct and efficient while ensuring you have all necessary information to process the cancellation correctly. If the customer doesn't provide enough information, ask clear follow-up questions to obtain the missing details.""",
                "description": "Main system prompt for Order Cancellation Agent",
                "variables": None
            },
            {
                "prompt_type": "cancellation_extraction",
                "content": """Extract order cancellation information from the user's message. Return a JSON object with the following structure:
{
    "cancellationType": "full|partial|unknown",  // Whether the entire order or just specific items are being cancelled
    "orderNumber": "string",                    // The order number (8-10 digit number), or null if not provided
    "customerNumber": "string",                 // The customer number, or null if not provided
    "zipCode": "string",                        // The delivery zip code, or null if not provided
    "email": "string",                          // The customer's email address, or null if not provided
    "reason": "string",                         // The reason for cancellation, or null if not provided
    "itemsToCancel": ["string"],                // Array of items to cancel (for partial cancellation), or empty array
    "missingRequiredFields": ["string"]         // Array of required fields that are missing
}

For full cancellation, orderNumber and customerNumber are required.
For partial cancellation, orderNumber, customerNumber, and itemsToCancel are required.""",
                "description": "Prompt for extracting cancellation information from user messages",
                "variables": None
            }
        ],
        "workflows": {
            "name": "Order Cancellation Flow",
            "description": "Workflow for handling order cancellation requests",
            "nodes": [
                {
                    "name": "extract_cancellation_info",
                    "node_type": "extraction",
                    "function_name": "extract_cancellation_info",
                    "prompt_type": "cancellation_extraction",
                    "response_template": None,
                    "config": {"required": True}
                },
                {
                    "name": "request_missing_info",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'd be happy to help with your cancellation request. To proceed, I'll need a few more details. Could you please provide: {data.extraction.missingRequiredFields.join(', ')}?",
                    "config": {}
                },
                {
                    "name": "confirm_full_cancellation",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'm processing your request to cancel the entire order #{data.extraction.orderNumber}. Please confirm that you want to cancel this entire order. Once confirmed, I'll submit the cancellation request for you.",
                    "config": {}
                },
                {
                    "name": "confirm_partial_cancellation",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "I'm processing your request to cancel specific items from order #{data.extraction.orderNumber}. You've indicated you want to cancel: {data.extraction.itemsToCancel.join(', ')}. Please confirm this is correct, and I'll submit the partial cancellation request.",
                    "config": {}
                },
                {
                    "name": "process_cancellation",
                    "node_type": "response",
                    "function_name": None,
                    "prompt_type": None,
                    "response_template": "Thank you for confirming. I've submitted your cancellation request for order #{data.extraction.orderNumber}. You should receive a confirmation email shortly. Please note that if your order is already in processing or shipping, we may not be able to cancel it. Is there anything else I can help you with today?",
                    "config": {}
                }
            ],
            "edges": [
                {"source": "extract_cancellation_info", "target": "request_missing_info", "condition_type": "conditional", "condition_value": "missing_fields", "priority": 1},
                {"source": "extract_cancellation_info", "target": "confirm_full_cancellation", "condition_type": "conditional", "condition_value": "full", "priority": 2},
                {"source": "extract_cancellation_info", "target": "confirm_partial_cancellation", "condition_type": "conditional", "condition_value": "partial", "priority": 3},
                {"source": "request_missing_info", "target": "extract_cancellation_info", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "confirm_full_cancellation", "target": "process_cancellation", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "confirm_partial_cancellation", "target": "process_cancellation", "condition_type": "direct", "condition_value": None, "priority": 0},
                {"source": "process_cancellation", "target": None, "condition_type": "direct", "condition_value": None, "priority": 0}
            ]
        }
    }
}

async def initialize_agents(db_pool):
    """
    Initialize agent configurations in the database.
    
    Args:
        db_pool: PostgreSQL connection pool
    """
    async with db_pool.acquire() as conn:
        # Use a transaction to ensure atomicity
        async with conn.transaction():
            for agent_type, config in AGENT_CONFIGS.items():
                logger.info(f"Initializing agent: {config['name']}")
                
                # Check if agent already exists
                existing_query = """
                    SELECT id FROM agent_definitions 
                    WHERE agent_type = $1 AND is_system = true
                    LIMIT 1
                """
                existing_agent = await conn.fetchrow(existing_query, agent_type)
                
                if existing_agent:
                    agent_id = existing_agent['id']
                    logger.info(f"Agent {config['name']} already exists with ID {agent_id}. Updating...")
                    
                    # Update agent
                    update_query = """
                        UPDATE agent_definitions
                        SET name = $1, description = $2, status = $3, updated_at = NOW()
                        WHERE id = $4
                        RETURNING id
                    """
                    updated = await conn.fetchrow(
                        update_query, 
                        config['name'],
                        config['description'],
                        config['status'],
                        agent_id
                    )
                    
                    # Clear existing patterns
                    await conn.execute(
                        "DELETE FROM agent_patterns WHERE agent_id = $1",
                        agent_id
                    )
                else:
                    # Create new agent
                    insert_query = """
                        INSERT INTO agent_definitions 
                        (name, description, agent_type, version, status, is_system, created_by)
                        VALUES ($1, $2, $3, 1, $4, true, 'system')
                        RETURNING id
                    """
                    result = await conn.fetchrow(
                        insert_query, 
                        config['name'],
                        config['description'],
                        agent_type,
                        config['status']
                    )
                    agent_id = result['id']
                    logger.info(f"Created agent {config['name']} with ID {agent_id}")
                
                # Insert patterns
                for pattern in config.get('patterns', []):
                    await conn.execute(
                        """
                        INSERT INTO agent_patterns 
                        (agent_id, pattern_type, pattern_value, priority, confidence_boost)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        agent_id,
                        pattern['pattern_type'],
                        pattern['pattern_value'],
                        pattern['priority'],
                        pattern['confidence_boost']
                    )
                    
                # Create workflow
                if 'workflows' in config:
                    workflow_config = config['workflows']
                    
                    # Create workflow
                    workflow_query = """
                        INSERT INTO workflows 
                        (agent_id, name, description, version, is_active, created_by)
                        VALUES ($1, $2, $3, 1, true, 'system')
                        RETURNING id
                    """
                    workflow_result = await conn.fetchrow(
                        workflow_query,
                        agent_id,
                        workflow_config['name'],
                        workflow_config['description']
                    )
                    workflow_id = workflow_result['id']
                    
                    # Update agent with workflow reference
                    await conn.execute(
                        """
                        UPDATE agent_definitions
                        SET workflow_id = $1
                        WHERE id = $2
                        """,
                        workflow_id,
                        agent_id
                    )
                    
                    # Create system prompts
                    prompt_id_map = {}
                    for prompt in config.get('prompts', []):
                        prompt_query = """
                            INSERT INTO system_prompts 
                            (agent_id, prompt_type, content, description, version, is_active, 
                             created_by, variables)
                            VALUES ($1, $2, $3, $4, 1, true, 'system', $5)
                            RETURNING id
                        """
                        prompt_result = await conn.fetchrow(
                            prompt_query,
                            agent_id,
                            prompt['prompt_type'],
                            prompt['content'],
                            prompt['description'],
                            json.dumps(prompt['variables']) if prompt['variables'] else None
                        )
                        prompt_id = prompt_result['id']
                        prompt_id_map[prompt['prompt_type']] = prompt_id
                        
                    # Create workflow nodes
                    node_id_map = {}
                    for node in workflow_config.get('nodes', []):
                        # Get prompt ID if specified
                        prompt_id = None
                        if node.get('prompt_type'):
                            prompt_id = prompt_id_map.get(node['prompt_type'])
                            
                        node_query = """
                            INSERT INTO workflow_nodes 
                            (workflow_id, name, node_type, function_name, system_prompt_id,
                             response_template, config)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            RETURNING id
                        """
                        node_result = await conn.fetchrow(
                            node_query,
                            workflow_id,
                            node['name'],
                            node['node_type'],
                            node['function_name'],
                            prompt_id,
                            node['response_template'],
                            json.dumps(node['config']) if 'config' in node else None
                        )
                        node_id = node_result['id']
                        node_id_map[node['name']] = node_id
                        
                    # Set entry node
                    if workflow_config.get('nodes') and len(workflow_config['nodes']) > 0:
                        first_node_name = workflow_config['nodes'][0]['name']
                        first_node_id = node_id_map[first_node_name]
                        
                        await conn.execute(
                            """
                            UPDATE workflows
                            SET entry_node = $1
                            WHERE id = $2
                            """,
                            first_node_id,
                            workflow_id
                        )
                    
                    # Create workflow edges
                    for edge in workflow_config.get('edges', []):
                        source_id = node_id_map[edge['source']]
                        target_id = node_id_map[edge['target']] if edge['target'] else None
                        
                        edge_query = """
                            INSERT INTO workflow_edges 
                            (workflow_id, source_node_id, target_node_id, condition_type, 
                             condition_value, priority)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            RETURNING id
                        """
                        await conn.execute(
                            edge_query,
                            workflow_id,
                            source_id,
                            target_id,
                            edge['condition_type'],
                            edge['condition_value'],
                            edge['priority']
                        )
                        
            logger.info("Agent initialization complete")

async def main():
    """
    Main function to run the database initialization.
    """
    # Set up logging
    logger.info("Starting agent configuration initialization")
    
    # Get database connection
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return
        
    # Create connection pool
    try:
        pool = await asyncpg.create_pool(database_url)
        logger.info("Connected to database")
        
        # Initialize agents
        await initialize_agents(pool)
        
        # Close connection
        await pool.close()
        logger.info("Database connection closed")
        
    except Exception as e:
        logger.exception(f"Error initializing agent configurations: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(main())