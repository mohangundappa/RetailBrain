"""
Update agent workflows script.

This script updates existing agents with workflow-based configurations.
It reads the agent configurations from existing agents and creates
corresponding workflows in the database.
"""
import logging
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import asyncpg

logger = logging.getLogger(__name__)

# Configuration for agent workflows
WORKFLOW_CONFIGURATIONS = {
    'reset_password': {
        'name': 'Password Reset Workflow',
        'description': 'Workflow for helping users reset their password',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': """
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
                'prompt': """
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
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'SMALL_TALK': {
        'name': 'General Conversation Workflow',
        'description': 'Workflow for general conversation and small talk',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': """
                    You are Staples Brain, a helpful assistant for Staples customers.
                    Always maintain a friendly and professional tone.
                    
                    Guidelines for conversation:
                    - Be warm and welcoming
                    - Answer general questions about Staples
                    - For specific help with orders, products, etc., offer to connect to specialized agents
                    - Keep responses concise and focused on Staples services
                    
                    You are an AI assistant, but focus on being helpful rather than discussing AI capabilities.
                """,
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'product_info': {
        'name': 'Product Information Workflow',
        'description': 'Workflow for helping users find and learn about products',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': """
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
                'prompt': """
                    You are a Store Locator specialist for Staples.
                    
                    Help customers find Staples stores near them.
                    
                    Guidelines:
                    - Ask for their location if not provided (city, zip code)
                    - Provide store addresses, hours, and phone numbers
                    - Mention special services available at specific stores
                    - Give brief directions if requested
                    
                    You use simulated data for this demo, so make it clear these are example responses.
                """,
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    'returns_processing': {
        'name': 'Returns Processing Workflow',
        'description': 'Workflow for helping users process returns',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': """
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
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    },
    
    # Default for any agent type not specified above
    'default': {
        'name': 'Default Agent Workflow',
        'description': 'Default workflow for any agent type',
        'nodes': {
            'entry': {
                'type': 'prompt',
                'prompt': """
                    You are a Staples assistant. 
                    Help customers with their Staples-related questions in a friendly and professional manner.
                """,
                'output_key': 'response'
            }
        },
        'edges': {},
        'entry_node': 'entry'
    }
}

async def update_agent_workflows(db_pool):
    """
    Update agents with workflow-based configurations.
    
    Args:
        db_pool: PostgreSQL connection pool
    """
    try:
        async with db_pool.acquire() as conn:
            # Check if tables exist
            tables_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'workflows'
                )
            """)
            
            if not tables_exist:
                logger.info("Creating workflow tables")
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
            
            # Get all active agents without workflows
            agents = await conn.fetch("""
                SELECT id, name, description, agent_type, is_system
                FROM agent_definitions
                WHERE status = 'active' AND (workflow_id IS NULL OR workflow_id = '')
            """)
            
            if not agents:
                logger.info("No agents found that need workflow updates")
                return
                
            now = datetime.utcnow()
            
            # Update each agent with a workflow
            for agent in agents:
                agent_id = agent['id']
                agent_name = agent['name']
                agent_type = agent['agent_type']
                
                # Get workflow configuration based on agent type
                workflow_config = WORKFLOW_CONFIGURATIONS.get(
                    agent_type, 
                    WORKFLOW_CONFIGURATIONS['default']
                )
                
                # Create workflow
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
                    workflow_config['name'],
                    workflow_config['description'],
                    json.dumps(workflow_config['nodes']),
                    json.dumps(workflow_config['edges']),
                    workflow_config['entry_node'],
                    now,
                    now
                )
                
                # Update agent with workflow ID
                await conn.execute(
                    """
                    UPDATE agent_definitions
                    SET workflow_id = $1, updated_at = $2
                    WHERE id = $3
                    """,
                    workflow_id,
                    now,
                    agent_id
                )
                
                logger.info(f"Updated agent: {agent_name} (ID: {agent_id}) with workflow")
            
            logger.info(f"Updated {len(agents)} agents with workflows")
    except Exception as e:
        logger.error(f"Error updating agent workflows: {str(e)}", exc_info=True)
        raise

async def main():
    """
    Main function to run the script.
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
        # Create a connection pool
        pool = await asyncpg.create_pool(
            user=username,
            password=password,
            database=database,
            host=host,
            port=port,
            min_size=1,
            max_size=10
        )
        
        try:
            # Update agent workflows
            await update_agent_workflows(pool)
            
            logger.info("Agent workflows updated successfully")
        finally:
            # Close the connection pool
            await pool.close()
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the update
    asyncio.run(main())