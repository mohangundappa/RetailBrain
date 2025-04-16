"""
Initialize Agent Configurations for Staples Brain.

This script initializes the database with default agent configurations,
including workflow definitions, prompts, and tools.
"""
import logging
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import asyncpg

logger = logging.getLogger(__name__)

# Configuration data for default agents
# Actual configurations would be defined here in a real implementation

# Define prompt templates for different agent types
AGENT_PROMPTS = {
    'greeting': """
        You are Staples Brain, a helpful assistant for Staples customers.
        Always maintain a friendly and professional tone.
        
        When greeting users:
        - Be warm and welcoming
        - Ask how you can help with Staples-related questions
        - Mention capabilities like product info, order tracking, and store locations
        
        Keep responses concise and focused on Staples services.
    """,
    
    'password_reset': """
        You are a Password Reset specialist for Staples.
        
        Help customers reset their password for Staples.com or related services.
        
        Guidelines:
        - Never ask for their current password
        - Direct them to the official reset page at staples.com/account/reset
        - Explain they'll receive an email with reset instructions
        - Advise them to check spam/junk folders if they don't see the email
        - If they have trouble, offer to transfer them to customer service
        
        Never attempt to actually reset the password within this conversation.
        For security, always direct them to the official reset process.
    """,
    
    'package_tracking': """
        You are a Package Tracking specialist for Staples.
        
        Help customers track their Staples orders and provide delivery updates.
        
        Guidelines:
        - Ask for their order number if not provided
        - Explain tracking statuses clearly
        - Provide estimated delivery dates when available
        - Offer to help with delivery issues
        - For problems, advise on next steps (contacting customer service, etc.)
        
        You use simulated data for this demo, so make it clear these are example responses.
    """,
    
    'product_search': """
        You are a Product Information specialist for Staples.
        
        Help customers find information about Staples products.
        
        Guidelines:
        - Assist with finding specific products
        - Provide details on features, specifications, and compatibility
        - Give pricing information when available
        - Help compare similar products
        - Suggest alternatives if a product is unavailable
        
        You use simulated data for this demo, so make it clear these are example responses.
    """,
    
    'store_locator': """
        You are a Store Locator specialist for Staples.
        
        Help customers find Staples stores near them.
        
        Guidelines:
        - Ask for their location if not provided (city, zip code)
        - Provide store addresses, hours, and phone numbers
        - Mention special services available at specific stores
        - Give brief directions if requested
        
        You use simulated data for this demo, so make it clear these are example responses.
    """,
    
    'returns': """
        You are a Returns Processing specialist for Staples.
        
        Help customers understand and process returns for Staples purchases.
        
        Guidelines:
        - Explain Staples' return policy (30 days for most items)
        - Ask for order number and purchase date
        - Guide through the return process step by step
        - Explain refund timelines and methods
        - Mention options for in-store or mail returns
        
        You use simulated data for this demo, so make it clear these are example responses.
    """,
}

# Define workflow templates for different agent types
AGENT_WORKFLOWS = {
    'password_reset': {
        'name': 'Password Reset Workflow',
        'description': 'Workflow for helping users reset their password',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['password_reset'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'greeting': {
        'name': 'Greeting Workflow',
        'description': 'Workflow for greeting users and handling small talk',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['greeting'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'package_tracking': {
        'name': 'Package Tracking Workflow',
        'description': 'Workflow for tracking packages and providing delivery updates',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['package_tracking'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'product_search': {
        'name': 'Product Search Workflow',
        'description': 'Workflow for helping users find and learn about products',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['product_search'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'store_locator': {
        'name': 'Store Locator Workflow',
        'description': 'Workflow for helping users find nearby Staples stores',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['store_locator'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'returns': {
        'name': 'Returns Processing Workflow',
        'description': 'Workflow for helping users process returns',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': AGENT_PROMPTS['returns'],
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    }
}

# Define agents to be created
AGENTS_TO_CREATE = [
    {
        'name': 'Password Reset Agent',
        'description': 'I can help you reset your password, recover your account, and guide you through the login process for Staples online services.',
        'agent_type': 'reset_password',
        'workflow_template': 'password_reset',
        'is_system': True,
        'status': 'active'
    },
    {
        'name': 'Package Tracking Agent',
        'description': 'I can help track your orders, check package status, and provide delivery updates for Staples purchases.',
        'agent_type': 'package_tracking',
        'workflow_template': 'package_tracking',
        'is_system': True,
        'status': 'active'
    },
    {
        'name': 'Product Information Agent',
        'description': 'I can help you find information about Staples products, check product availability, and answer questions about features and compatibility.',
        'agent_type': 'product_info',
        'workflow_template': 'product_search',
        'is_system': True,
        'status': 'active'
    },
    {
        'name': 'Store Locator Agent',
        'description': 'I can help you find Staples stores near you, check store hours, and provide information about store services.',
        'agent_type': 'store_locator',
        'workflow_template': 'store_locator',
        'is_system': True,
        'status': 'active'
    },
    {
        'name': 'Returns Processing Agent',
        'description': 'I can help you process returns, understand the return policy, and provide information about return status for Staples purchases.',
        'agent_type': 'returns_processing',
        'workflow_template': 'returns',
        'is_system': True,
        'status': 'active'
    }
]

async def initialize_database_schema(conn):
    """
    Initialize database schema for workflows and prompts.
    
    Args:
        conn: Database connection
    """
    try:
        # Create workflows table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                nodes JSONB,
                edges JSONB,
                entry_node TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        # Create system_prompts table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS system_prompts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                template_variables JSONB,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        # Add workflow_id column to agent_definitions if it doesn't exist
        # This uses a more compatible approach than ALTER TABLE IF NOT EXISTS
        table_info = await conn.fetch('''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_definitions'
              AND column_name = 'workflow_id'
        ''')
        
        if not table_info:
            logger.info("Adding workflow_id column to agent_definitions table")
            await conn.execute('''
                ALTER TABLE agent_definitions
                ADD COLUMN workflow_id TEXT
            ''')
        
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database schema: {str(e)}", exc_info=True)
        raise

async def initialize_prompts(conn):
    """
    Initialize default system prompts.
    
    Args:
        conn: Database connection
    """
    try:
        now = datetime.utcnow()
        
        # Insert prompts
        for prompt_type, prompt_content in AGENT_PROMPTS.items():
            prompt_id = f"prompt_{prompt_type}"
            prompt_name = f"{prompt_type.replace('_', ' ').title()} Prompt"
            
            # Check if prompt already exists
            existing = await conn.fetchval(
                "SELECT id FROM system_prompts WHERE id = $1",
                prompt_id
            )
            
            if not existing:
                # Insert new prompt
                await conn.execute(
                    """
                    INSERT INTO system_prompts (id, name, content, template_variables, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    prompt_id,
                    prompt_name,
                    prompt_content,
                    json.dumps([]),
                    now,
                    now
                )
                logger.info(f"Created system prompt: {prompt_name}")
            else:
                logger.info(f"System prompt already exists: {prompt_name}")
        
        logger.info("System prompts initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing system prompts: {str(e)}", exc_info=True)
        raise

async def initialize_agents(conn):
    """
    Initialize default agents with workflows.
    
    Args:
        conn: Database connection
    """
    try:
        now = datetime.utcnow()
        
        for agent_config in AGENTS_TO_CREATE:
            agent_name = agent_config['name']
            agent_type = agent_config['agent_type']
            
            # Check if agent already exists
            existing = await conn.fetchval(
                "SELECT id FROM agent_definitions WHERE name = $1",
                agent_name
            )
            
            if not existing:
                # Create new agent
                agent_id = str(uuid.uuid4())
                
                await conn.execute(
                    """
                    INSERT INTO agent_definitions (
                        id, name, description, agent_type, version, status, 
                        is_system, created_at, updated_at, created_by
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    agent_id,
                    agent_name,
                    agent_config['description'],
                    agent_type,
                    1,  # version
                    agent_config['status'],
                    agent_config['is_system'],
                    now,
                    now,
                    'system'  # created_by
                )
                
                # Create workflow for agent
                workflow_template = agent_config['workflow_template']
                workflow_data = AGENT_WORKFLOWS.get(workflow_template)
                
                if workflow_data:
                    workflow_id = str(uuid.uuid4())
                    
                    # Store workflow
                    await conn.execute(
                        """
                        INSERT INTO workflows (
                            id, agent_id, name, description, 
                            nodes, edges, entry_node, 
                            created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        workflow_id,
                        agent_id,
                        workflow_data['name'],
                        workflow_data['description'],
                        json.dumps(workflow_data['nodes']),
                        json.dumps(workflow_data['edges']),
                        workflow_data['entry_node'],
                        now,
                        now
                    )
                    
                    # Update agent with workflow ID
                    await conn.execute(
                        """
                        UPDATE agent_definitions
                        SET workflow_id = $1
                        WHERE id = $2
                        """,
                        workflow_id,
                        agent_id
                    )
                    
                    logger.info(f"Created agent: {agent_name} with workflow: {workflow_data['name']}")
                else:
                    logger.warning(f"No workflow template found for {workflow_template}")
                    logger.info(f"Created agent: {agent_name} without workflow")
            else:
                logger.info(f"Agent already exists: {agent_name}")
        
        logger.info("Default agents initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing agents: {str(e)}", exc_info=True)
        raise

async def main():
    """
    Main function to initialize everything.
    """
    # Get database connection from environment
    import os
    from urllib.parse import urlparse
    
    # Extract host, port, user, password, database from DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    # Parse the URL to get connection parameters
    parsed = urlparse(db_url)
    username = parsed.username
    password = parsed.password
    database = parsed.path[1:]  # Remove leading slash
    host = parsed.hostname
    port = parsed.port or 5432
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            user=username,
            password=password,
            database=database,
            host=host,
            port=port
        )
        
        try:
            # Initialize schema first
            await initialize_database_schema(conn)
            
            # Initialize prompts
            await initialize_prompts(conn)
            
            # Initialize agents with workflows
            await initialize_agents(conn)
            
            logger.info("Agent configurations initialized successfully")
        finally:
            # Close the connection
            await conn.close()
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the initialization
    asyncio.run(main())