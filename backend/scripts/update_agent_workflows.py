"""
Update agent workflows script.

This script updates existing agents with workflow-based configurations.
It reads the agent configurations from existing agents and creates
corresponding workflows in the database.
"""
import asyncio
import logging
import json
import os
import sys
import uuid
from typing import Dict, Any, List

import asyncpg
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent workflow configurations
AGENT_WORKFLOW_CONFIGS = {
    "reset_password": {
        "name": "Password Reset Flow",
        "description": "Workflow for handling password reset requests",
        "prompts": {
            "main": {
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
            "email_extraction": {
                "content": """Extract the email address from the user's message if present. Return a JSON object with the following structure:
{
    "email": "user@example.com"  // The extracted email address, or null if not found
}

Ensure you extract only valid email addresses in the format user@domain.tld. If multiple email addresses are present, extract the one that appears to be the user's account email.""",
                "description": "Prompt for extracting email addresses from user messages",
                "variables": None
            }
        },
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
    },
    "product_search": {
        "name": "Product Search Flow",
        "description": "Workflow for handling product search requests",
        "prompts": {
            "main": {
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
            "product_extraction": {
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
        },
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
    },
    "SMALL_TALK": {
        "name": "Greeting and Thank You Flow",
        "description": "Workflow for handling greetings and thank you messages",
        "prompts": {
            "main": {
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
            "greeting_detection": {
                "content": """Determine if the user's message is a greeting or expression of thanks. Return a JSON object with the following structure:
{
    "messageType": "greeting | thanks | other",  // The type of message detected
    "intensity": "casual | standard | formal"     // The level of formality detected
}

If the message contains both a greeting and thanks, prioritize the thanks classification.""",
                "description": "Prompt for detecting greetings and thank you messages",
                "variables": None
            }
        },
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
    },
    "package_tracking": {
        "name": "Package Tracking Flow",
        "description": "Workflow for handling package tracking requests",
        "prompts": {
            "main": {
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
            "order_extraction": {
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
        },
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
}


async def update_agent_workflows(db_pool):
    """
    Update agents with workflow-based configurations.
    
    Args:
        db_pool: PostgreSQL connection pool
    """
    async with db_pool.acquire() as conn:
        # Use a transaction to ensure atomicity
        async with conn.transaction():
            # Get all active agents
            agents_query = """
                SELECT id, name, agent_type, description 
                FROM agent_definitions 
                WHERE status = 'active'
            """
            agents = await conn.fetch(agents_query)
            
            for agent in agents:
                agent_id = agent['id']
                agent_type = agent['agent_type']
                
                # Skip if agent doesn't have a corresponding workflow config
                if agent_type not in AGENT_WORKFLOW_CONFIGS and agent_type.lower() not in AGENT_WORKFLOW_CONFIGS:
                    logger.info(f"No workflow config for agent type {agent_type}, skipping")
                    continue
                
                # Get workflow config
                workflow_config = AGENT_WORKFLOW_CONFIGS.get(agent_type) or AGENT_WORKFLOW_CONFIGS.get(agent_type.lower())
                
                # Check if agent already has a workflow
                workflow_check = """
                    SELECT id FROM workflows WHERE agent_id = $1 LIMIT 1
                """
                existing_workflow = await conn.fetchrow(workflow_check, agent_id)
                
                if existing_workflow:
                    logger.info(f"Agent {agent['name']} already has workflow {existing_workflow['id']}, skipping")
                    continue
                
                logger.info(f"Creating workflow for agent {agent['name']} (ID: {agent_id}, Type: {agent_type})")
                
                # Create workflow
                workflow_id = str(uuid.uuid4())
                workflow_name = workflow_config.get('name', f"Workflow for {agent['name']}")
                workflow_description = workflow_config.get('description', '')
                
                workflow_query = """
                    INSERT INTO workflows 
                    (id, agent_id, name, description, version, is_active, created_by)
                    VALUES ($1, $2, $3, $4, 1, true, 'system')
                    RETURNING id
                """
                await conn.fetchrow(
                    workflow_query,
                    workflow_id,
                    agent_id,
                    workflow_name,
                    workflow_description
                )
                
                # Create system prompts for each prompt type
                prompt_id_map = {}
                for prompt_type, prompt_data in workflow_config.get('prompts', {}).items():
                    prompt_id = str(uuid.uuid4())
                    prompt_content = prompt_data.get('content', '')
                    prompt_description = prompt_data.get('description', '')
                    prompt_variables = prompt_data.get('variables')
                    
                    prompt_query = """
                        INSERT INTO system_prompts 
                        (id, agent_id, prompt_type, content, description, 
                         version, is_active, created_by, variables)
                        VALUES ($1, $2, $3, $4, $5, 1, true, 'system', $6)
                        RETURNING id
                    """
                    await conn.fetchrow(
                        prompt_query,
                        prompt_id,
                        agent_id,
                        prompt_type,
                        prompt_content,
                        prompt_description,
                        json.dumps(prompt_variables) if prompt_variables else None
                    )
                    
                    prompt_id_map[prompt_type] = prompt_id
                
                # Create workflow nodes
                node_id_map = {}
                for node_data in workflow_config.get('nodes', []):
                    node_id = str(uuid.uuid4())
                    node_name = node_data.get('name')
                    node_type = node_data.get('node_type')
                    function_name = node_data.get('function_name')
                    response_template = node_data.get('response_template')
                    config = node_data.get('config', {})
                    
                    # Get prompt ID if specified
                    prompt_id = None
                    if 'prompt_type' in node_data and node_data['prompt_type']:
                        prompt_id = prompt_id_map.get(node_data['prompt_type'])
                    
                    # Create node
                    node_query = """
                        INSERT INTO workflow_nodes 
                        (id, workflow_id, name, node_type, function_name, 
                         system_prompt_id, response_template, config)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                    """
                    await conn.fetchrow(
                        node_query,
                        node_id,
                        workflow_id,
                        node_name,
                        node_type,
                        function_name,
                        prompt_id,
                        response_template,
                        json.dumps(config) if config else None
                    )
                    
                    node_id_map[node_name] = node_id
                
                # Create edges
                for edge_data in workflow_config.get('edges', []):
                    edge_id = str(uuid.uuid4())
                    source_name = edge_data.get('source')
                    target_name = edge_data.get('target')
                    condition_type = edge_data.get('condition_type', 'direct')
                    condition_value = edge_data.get('condition_value')
                    priority = edge_data.get('priority', 0)
                    
                    source_id = node_id_map.get(source_name)
                    target_id = node_id_map.get(target_name) if target_name else None
                    
                    if source_id:
                        edge_query = """
                            INSERT INTO workflow_edges 
                            (id, workflow_id, source_node_id, target_node_id, 
                             condition_type, condition_value, priority)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            RETURNING id
                        """
                        await conn.fetchrow(
                            edge_query,
                            edge_id,
                            workflow_id,
                            source_id,
                            target_id,
                            condition_type,
                            json.dumps(condition_value) if isinstance(condition_value, (dict, list)) else condition_value,
                            priority
                        )
                
                # Set entry node
                if workflow_config.get('nodes') and len(workflow_config['nodes']) > 0:
                    first_node_name = workflow_config['nodes'][0]['name']
                    first_node_id = node_id_map.get(first_node_name)
                    
                    if first_node_id:
                        await conn.execute(
                            """
                            UPDATE workflows
                            SET entry_node = $1
                            WHERE id = $2
                            """,
                            first_node_id,
                            workflow_id
                        )
                
                # Update agent with workflow reference
                await conn.execute(
                    """
                    UPDATE agent_definitions
                    SET workflow_id = $1, 
                        updated_at = $2
                    WHERE id = $3
                    """,
                    workflow_id,
                    datetime.now(),
                    agent_id
                )
                
                logger.info(f"Created workflow {workflow_id} for agent {agent['name']}")
            
            logger.info("Agent workflow update complete")


async def main():
    """
    Main function to run the script.
    """
    # Set up logging
    logger.info("Starting agent workflow update")
    
    # Get database connection
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return
        
    # Create connection pool
    try:
        pool = await asyncpg.create_pool(database_url)
        logger.info("Connected to database")
        
        # Update agent workflows
        await update_agent_workflows(pool)
        
        # Close connection
        await pool.close()
        logger.info("Database connection closed")
        
    except Exception as e:
        logger.exception(f"Error updating agent workflows: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(main())