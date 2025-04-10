"""
Agent Builder API Routes

This module provides the API endpoints for creating, managing, and testing custom agents
through the drag-and-drop agent builder interface.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from models import CustomAgent, AgentComponent, ComponentConnection, ComponentTemplate, AgentTemplate

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
agent_builder_bp = Blueprint('agent_builder_api', __name__)

@agent_builder_bp.route('/agents', methods=['GET'])
def list_agents():
    """
    Get a list of all agents, both custom and built-in.
    
    Returns:
        JSON list of agents with their basic information
    """
    try:
        # Get custom agents from database
        custom_agents = CustomAgent.query.all()
        result = [{
            'id': agent.id,
            'name': agent.name,
            'description': agent.description,
            'created_at': agent.created_at.isoformat() if agent.created_at else None,
            'updated_at': agent.updated_at.isoformat() if agent.updated_at else None,
            'is_active': agent.is_active,
            'creator': agent.creator,
            'component_count': len(agent.components),
            'is_custom': True,  # Flag to indicate this is a custom agent
            'can_edit': True    # Custom agents can be edited
        } for agent in custom_agents]
        
        # Get built-in agents from the brain
        from brain.staples_brain import initialize_staples_brain
        try:
            brain = initialize_staples_brain()
            builtin_agents = brain.agents
            
            # Add built-in agents to the result
            for idx, agent in enumerate(builtin_agents):
                # Use negative IDs to distinguish built-in agents
                agent_id = -(idx + 1)
                result.append({
                    'id': agent_id,
                    'name': agent.name,
                    'description': getattr(agent, 'description', f"Built-in agent for {agent.name.lower()} functionality"),
                    'created_at': None,
                    'updated_at': None,
                    'is_active': True,
                    'creator': 'System',
                    'component_count': 0,  # Built-in agents don't have components in the same way
                    'is_custom': False,    # Flag to indicate this is a built-in agent
                    'can_edit': False      # Built-in agents cannot be edited
                })
        except Exception as e:
            logger.warning(f"Error loading built-in agents: {str(e)}")
            # Continue with just the custom agents if we can't load built-in ones
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/agents', methods=['POST'])
def create_agent():
    """
    Create a new custom agent.
    
    The request body should contain the agent configuration.
    
    Returns:
        JSON with the created agent information
    """
    try:
        data = request.json
        logger.debug("Received request to create new agent")
        
        # Basic validation
        if not data.get('name'):
            logger.warning("Missing required field: name")
            return jsonify({'error': 'Agent name is required'}), 400
            
        # Check if name already exists
        existing = CustomAgent.query.filter_by(name=data['name']).first()
        if existing:
            logger.warning(f"Agent with name '{data['name']}' already exists")
            return jsonify({'error': f"Agent with name '{data['name']}' already exists"}), 409
            
        # Create agent
        agent = CustomAgent(
            name=data['name'],
            description=data.get('description', ''),
            creator=data.get('creator', 'UI Builder'),
            is_active=True
        )
        
        db.session.add(agent)
        db.session.flush()  # Get the agent ID
        
        # Validate required fields for component handling
        for idx, component in enumerate(data.get('components', [])):
            if 'template' not in component:
                logger.warning(f"Component {idx} missing template field, adding default")
                component_type = component.get('component_type', 'unknown')
                if component_type == 'prompt':
                    component['template'] = 'custom_prompt'
                elif component_type == 'llm':
                    component['template'] = 'openai_gpt4'
                elif component_type == 'output':
                    component['template'] = 'json_formatter'
                else:
                    component['template'] = f"{component_type}_default"
        
        # Add components
        component_id_map = {}
        for comp_data in data.get('components', []):
            # Build additional metadata for component storage
            metadata = {
                'template': comp_data.get('template')
            }
            
            # Create configuration by combining explicit config with metadata
            config = comp_data.get('configuration', {})
            config['_metadata'] = metadata
            
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data['component_type'],
                name=comp_data['name'],
                position_x=comp_data['position_x'],
                position_y=comp_data['position_y'],
                configuration=json.dumps(config)
            )
            
            db.session.add(component)
            db.session.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data['id']] = component.id
            logger.debug(f"Added component: {comp_data['name']} (ID: {component.id})")
        
        # Add connections
        for conn_data in data.get('connections', []):
            # Map frontend IDs to database IDs
            try:
                source_id = component_id_map[conn_data['source_id']]
                target_id = component_id_map[conn_data['target_id']]
            except KeyError as e:
                logger.warning(f"Invalid component reference in connection: {e}")
                continue
                
            connection = ComponentConnection(
                agent_id=agent.id,
                source_id=source_id,
                target_id=target_id,
                connection_type=conn_data.get('connection_type', 'default')
            )
            
            db.session.add(connection)
            logger.debug(f"Added connection from {conn_data['source_id']} to {conn_data['target_id']}")
        
        # Store the original configuration as JSON
        agent.configuration = json.dumps(data)
        
        db.session.commit()
        logger.info(f"Agent {agent.name} (ID: {agent.id}) created successfully")
        
        return jsonify({
            'id': agent.id,
            'name': agent.name,
            'message': 'Agent created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating agent: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/agents/<int:agent_id>', methods=['GET'])
def get_agent(agent_id):
    """
    Get a specific agent with all its components and connections.
    
    Args:
        agent_id: The ID of the agent
        
    Returns:
        JSON with the complete agent configuration
    """
    try:
        logger.debug(f"Getting agent with ID: {agent_id}")
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            logger.warning(f"Agent not found with ID: {agent_id}")
            return jsonify({'error': 'Agent not found'}), 404
            
        logger.debug(f"Agent found: {agent.name}, has configuration: {bool(agent.configuration)}")
        
        # If we have stored configuration, use that as the base
        if agent.configuration:
            try:
                config = json.loads(agent.configuration)
                logger.debug(f"Loaded configuration JSON successfully")
                
                # Update basic properties
                config['id'] = agent.id
                config['name'] = agent.name
                config['description'] = agent.description
                config['is_active'] = agent.is_active
                config['created_at'] = agent.created_at.isoformat() if agent.created_at else None
                config['updated_at'] = agent.updated_at.isoformat() if agent.updated_at else None
                
                # Validate required fields for component rendering
                for idx, component in enumerate(config.get('components', [])):
                    if 'template' not in component:
                        logger.warning(f"Component {idx} missing template field, adding default")
                        component_type = component.get('component_type', 'unknown')
                        if component_type == 'prompt':
                            component['template'] = 'custom_prompt'
                        elif component_type == 'llm':
                            component['template'] = 'openai_gpt4'
                        elif component_type == 'output':
                            component['template'] = 'json_formatter'
                        else:
                            component['template'] = f"{component_type}_default"
                
                return jsonify(config), 200
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent configuration JSON: {str(e)}")
                # If JSON parsing fails, fall back to building config from components
            
        # Otherwise build the configuration from components and connections
        logger.debug(f"Building configuration from components: {len(agent.components)} and connections: {len(agent.connections)}")
        components = []
        for comp in agent.components:
            # Determine template from component type if not available
            template = 'custom_prompt'
            if comp.component_type == 'llm':
                template = 'openai_gpt4'
            elif comp.component_type == 'output':
                template = 'json_formatter'
                
            component_data = {
                'id': f"component-{comp.id}",
                'component_type': comp.component_type,
                'name': comp.name,
                'template': template,  # Add template field which is required by the frontend
                'position_x': comp.position_x,
                'position_y': comp.position_y,
                'configuration': json.loads(comp.configuration) if comp.configuration else {}
            }
            components.append(component_data)
            
        connections = []
        for conn in agent.connections:
            connection_data = {
                'id': f"connection-{conn.id}",
                'source_id': f"component-{conn.source_id}",
                'target_id': f"component-{conn.target_id}",
                'connection_type': conn.connection_type
            }
            connections.append(connection_data)
            
        result = {
            'id': agent.id,
            'name': agent.name,
            'description': agent.description,
            'is_active': agent.is_active,
            'creator': agent.creator,
            'created_at': agent.created_at.isoformat() if agent.created_at else None,
            'updated_at': agent.updated_at.isoformat() if agent.updated_at else None,
            'components': components,
            'connections': connections
        }
        
        logger.debug(f"Built agent configuration with {len(components)} components and {len(connections)} connections")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error retrieving agent: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/agents/<int:agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """
    Update an existing agent.
    
    Args:
        agent_id: The ID of the agent to update
        
    Returns:
        JSON with the updated agent information
    """
    try:
        logger.debug(f"Updating agent with ID: {agent_id}")
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            logger.warning(f"Agent not found with ID: {agent_id}")
            return jsonify({'error': 'Agent not found'}), 404
            
        data = request.json
        logger.debug(f"Received update data for agent: {agent.name}")
        
        # Basic validation
        if not data.get('name'):
            logger.warning("Missing required field: name")
            return jsonify({'error': 'Agent name is required'}), 400
            
        # Check if name already exists (if changed)
        if data['name'] != agent.name:
            existing = CustomAgent.query.filter_by(name=data['name']).first()
            if existing:
                logger.warning(f"Agent with name '{data['name']}' already exists")
                return jsonify({'error': f"Agent with name '{data['name']}' already exists"}), 409
        
        # Delete existing components and connections
        ComponentConnection.query.filter_by(agent_id=agent.id).delete()
        AgentComponent.query.filter_by(agent_id=agent.id).delete()
        
        # Update agent
        agent.name = data['name']
        agent.description = data.get('description', '')
        agent.updated_at = datetime.utcnow()
        
        # Validate required fields for component handling
        for idx, component in enumerate(data.get('components', [])):
            if 'template' not in component:
                logger.warning(f"Component {idx} missing template field, adding default")
                component_type = component.get('component_type', 'unknown')
                if component_type == 'prompt':
                    component['template'] = 'custom_prompt'
                elif component_type == 'llm':
                    component['template'] = 'openai_gpt4'
                elif component_type == 'output':
                    component['template'] = 'json_formatter'
                else:
                    component['template'] = f"{component_type}_default"
        
        # Add new components
        component_id_map = {}
        for comp_data in data.get('components', []):
            # Build additional metadata for component storage
            metadata = {
                'template': comp_data.get('template')
            }
            
            # Create configuration by combining explicit config with metadata
            config = comp_data.get('configuration', {})
            config['_metadata'] = metadata
            
            # Create the component
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data['component_type'],
                name=comp_data['name'],
                position_x=comp_data['position_x'],
                position_y=comp_data['position_y'],
                configuration=json.dumps(config)
            )
            
            db.session.add(component)
            db.session.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data['id']] = component.id
            logger.debug(f"Added component: {comp_data['name']} (ID: {component.id})")
        
        # Add connections
        for conn_data in data.get('connections', []):
            # Map frontend IDs to database IDs
            try:
                source_id = component_id_map[conn_data['source_id']]
                target_id = component_id_map[conn_data['target_id']]
            except KeyError as e:
                logger.warning(f"Invalid component reference in connection: {e}")
                continue
                
            connection = ComponentConnection(
                agent_id=agent.id,
                source_id=source_id,
                target_id=target_id,
                connection_type=conn_data.get('connection_type', 'default')
            )
            
            db.session.add(connection)
            logger.debug(f"Added connection from {conn_data['source_id']} to {conn_data['target_id']}")
        
        # Store the updated configuration as JSON
        agent.configuration = json.dumps(data)
        
        db.session.commit()
        logger.info(f"Agent {agent.name} (ID: {agent.id}) updated successfully")
        
        return jsonify({
            'id': agent.id,
            'name': agent.name,
            'message': 'Agent updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating agent: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/agents/<int:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """
    Delete an agent.
    
    Args:
        agent_id: The ID of the agent to delete
        
    Returns:
        JSON confirmation message
    """
    try:
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
            
        # Delete will cascade to components and connections
        db.session.delete(agent)
        db.session.commit()
        
        return jsonify({
            'message': f'Agent "{agent.name}" deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting agent: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/agents/<int:agent_id>/test', methods=['POST'])
def test_agent(agent_id):
    """
    Test a custom agent with sample input.
    
    This is a simplified mock test function. In a real implementation,
    this would dynamically create and execute the agent based on its
    components and connections.
    
    Args:
        agent_id: The ID of the agent to test
        
    Returns:
        JSON with the test results
    """
    try:
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
            
        data = request.json
        test_input = data.get('input', '')
        
        if not test_input:
            return jsonify({'error': 'Test input is required'}), 400
        
        # Load the agent configuration
        if not agent.configuration:
            return jsonify({'error': 'Agent has no configuration'}), 400
            
        config = json.loads(agent.configuration)
        
        # In a real implementation, you would dynamically create and execute the agent
        # For this simplified version, we'll return a mock response
        
        # Find intent classifier components
        intent_classifiers = [
            comp for comp in config.get('components', []) 
            if comp.get('component_type') == 'prompt' and comp.get('template') == 'intent_classifier'
        ]
        
        # Find LLM components
        llm_components = [
            comp for comp in config.get('components', [])
            if comp.get('component_type') == 'llm'
        ]
        
        # Find output components
        output_components = [
            comp for comp in config.get('components', [])
            if comp.get('component_type') == 'output'
        ]
        
        # Simplified mock response based on components found
        result = {
            'input': test_input,
            'agent_id': agent_id,
            'agent_name': agent.name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add some mock results based on the components
        if intent_classifiers:
            # Get the first intent classifier
            classifier = intent_classifiers[0]
            intents = classifier.get('configuration', {}).get('available_intents', '')
            
            # Extract a simple list of intents
            intent_list = [i.strip() for i in intents.split(',') if i.strip()]
            
            # Simplified "classification" - just match keywords
            matched_intent = None
            for intent in intent_list:
                if intent.lower() in test_input.lower():
                    matched_intent = intent
                    break
                    
            if not matched_intent and intent_list:
                # Just pick the first one as a fallback
                matched_intent = intent_list[0]
                
            result['intent'] = matched_intent
            result['confidence'] = 0.85
        
        # Add simple response
        result['response'] = f"This is a mock response from the {agent.name} agent. In a real implementation, this agent would process your input: '{test_input}' through its component pipeline."
        
        # If we have JSON formatter components, structure the response accordingly
        json_formatters = [
            comp for comp in output_components
            if comp.get('template') == 'json_formatter'
        ]
        
        if json_formatters:
            # Add structured fields
            result['structured_data'] = {
                'processed': True,
                'components_used': len(config.get('components', [])),
                'execution_time_ms': 120
            }
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error testing agent: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/templates', methods=['GET'])
def get_agent_templates():
    """
    Get available agent templates.
    
    Returns:
        JSON list of agent templates
    """
    try:
        templates = AgentTemplate.query.all()
        
        if not templates:
            # If no templates in the database, return some predefined ones
            return jsonify([
                {
                    "id": "agent-template-1",
                    "name": "Customer Support Agent",
                    "description": "General purpose customer support agent with FAQ capabilities",
                    "category": "customer_support",
                    "icon": "headset",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 120,
                    "rating": 4.5,
                    "configuration": {
                        "system_prompt": "You are a helpful customer support agent for Staples. Answer questions professionally and accurately.",
                        "tools": ["find_store_locations", "get_order_status", "search_products"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                {
                    "id": "agent-template-2",
                    "name": "Order Tracking Specialist",
                    "description": "Specialized agent for order tracking and shipment inquiries",
                    "category": "orders",
                    "icon": "package",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 85,
                    "rating": 4.7,
                    "configuration": {
                        "system_prompt": "You are an order tracking specialist for Staples. Help customers track their orders and provide shipment information.",
                        "tools": ["get_order_status", "get_tracking_info"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                {
                    "id": "agent-template-3",
                    "name": "Store Finder",
                    "description": "Agent that helps customers find nearby Staples stores",
                    "category": "locations",
                    "icon": "map-pin",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 65,
                    "rating": 4.8,
                    "configuration": {
                        "system_prompt": "You are a store finder assistant for Staples. Help customers locate the nearest Staples stores and provide information about services offered.",
                        "tools": ["find_store_locations"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                }
            ]), 200
        
        # Otherwise, return the templates from the database
        return jsonify([{
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "icon": template.icon or "puzzle-piece",
            "is_featured": template.is_featured,
            "author": template.author or "Staples",
            "downloads": template.downloads,
            "rating": template.rating,
            "configuration": json.loads(template.configuration) if template.configuration else {}
        } for template in templates]), 200
        
    except Exception as e:
        logger.error(f"Error getting agent templates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/templates/<template_id>', methods=['GET'])
def get_agent_template(template_id):
    """
    Get a specific agent template by ID.
    
    Args:
        template_id: The ID of the template to get
        
    Returns:
        JSON with the complete template configuration
    """
    try:
        # Handle hard-coded templates from the default list
        if template_id in ["agent-template-1", "agent-template-2", "agent-template-3"]:
            # Return the template based on ID
            templates = {
                "agent-template-1": {
                    "id": "agent-template-1",
                    "name": "Customer Support Agent",
                    "description": "General purpose customer support agent with FAQ capabilities",
                    "category": "customer_support",
                    "icon": "headset",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 120,
                    "rating": 4.5,
                    "configuration": {
                        "system_prompt": "You are a helpful customer support agent for Staples. Answer questions professionally and accurately.",
                        "tools": ["find_store_locations", "get_order_status", "search_products"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                "agent-template-2": {
                    "id": "agent-template-2",
                    "name": "Order Tracking Specialist",
                    "description": "Specialized agent for order tracking and shipment inquiries",
                    "category": "orders",
                    "icon": "package",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 85,
                    "rating": 4.7,
                    "configuration": {
                        "system_prompt": "You are an order tracking specialist for Staples. Help customers track their orders and provide shipment information.",
                        "tools": ["get_order_status", "get_tracking_info"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                "agent-template-3": {
                    "id": "agent-template-3",
                    "name": "Store Finder",
                    "description": "Agent that helps customers find nearby Staples stores",
                    "category": "locations",
                    "icon": "map-pin",
                    "is_featured": True,
                    "author": "Staples",
                    "downloads": 65,
                    "rating": 4.8,
                    "configuration": {
                        "system_prompt": "You are a store finder assistant for Staples. Help customers locate the nearest Staples stores and provide information about services offered.",
                        "tools": ["find_store_locations"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                }
            }
            return jsonify(templates.get(template_id)), 200
        
        # Handle database templates
        try:
            template_id_int = int(template_id)
            template = AgentTemplate.query.get(template_id_int)
        except ValueError:
            # Not an integer ID
            logger.warning(f"Invalid template ID format: {template_id}")
            return jsonify({'error': 'Template not found'}), 404
        
        if not template:
            logger.warning(f"Template not found with ID: {template_id}")
            return jsonify({'error': 'Template not found'}), 404
        
        # Increment download count
        template.downloads += 1
        db.session.commit()
        
        # Return template data
        return jsonify({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "icon": template.icon or "puzzle-piece",
            "is_featured": template.is_featured,
            "author": template.author or "Staples",
            "downloads": template.downloads,
            "rating": template.rating,
            "configuration": json.loads(template.configuration) if template.configuration else {}
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent template: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_builder_bp.route('/component-templates', methods=['GET'])
def get_component_templates():
    """
    Get available component templates for the agent builder.
    
    Returns:
        JSON list of component templates
    """
    try:
        templates = ComponentTemplate.query.all()
        
        if not templates:
            # If no templates in the database, return some predefined ones
            return jsonify([
                {
                    'id': 'intent_classifier',
                    'name': 'Intent Classifier',
                    'description': 'Classifies user input into predefined intents',
                    'component_type': 'prompt',
                    'category': 'Processing',
                    'is_system': True
                },
                {
                    'id': 'entity_extractor',
                    'name': 'Entity Extractor',
                    'description': 'Extracts structured entities from user input',
                    'component_type': 'prompt',
                    'category': 'Processing',
                    'is_system': True
                },
                {
                    'id': 'openai_gpt4',
                    'name': 'OpenAI GPT-4',
                    'description': 'Language model for generating responses',
                    'component_type': 'llm',
                    'category': 'Models',
                    'is_system': True
                }
            ]), 200
            
        # Otherwise, return the templates from the database
        result = [{
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'component_type': template.component_type,
            'category': template.category,
            'is_system': template.is_system,
            'configuration_template': json.loads(template.configuration_template) if template.configuration_template else None
        } for template in templates]
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting component templates: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
        
        
@agent_builder_bp.route('/llm-assist', methods=['POST'])
def llm_assist():
    """
    Generate agent configuration components using LLM assistance.
    
    Request Body:
        assistance_type: Type of assistance requested (prompt, entity, schema, etc.)
        description: User's description of what they need
        agent_type: Type of agent being configured (optional)
        existing_context: Any existing configuration to consider (optional)
    
    Returns:
        JSON with the LLM-generated suggestions
    """
    try:
        data = request.json
        assistance_type = data.get('assistance_type')
        description = data.get('description', '')
        agent_type = data.get('agent_type', 'custom')
        existing_context = data.get('existing_context', {})
        
        # Import OpenAI client
        from brain.staples_brain import get_openai_client
        client = get_openai_client()
        
        # Define system prompts based on assistance type
        system_prompts = {
            'system_prompt': """You are an expert AI prompt engineer. Your task is to create a clear, effective system prompt for a customer service agent for Staples.
The prompt should define the agent's behavior, tone, and guidelines for interacting with customers.
Provide only the prompt text without explanations or additional information.""",
            
            'entity_definition': """You are an expert in defining entities for conversational AI agents. 
Your task is to identify and define entities that should be extracted from customer queries for a Staples customer service agent.
For each entity, provide:
1. name: A clear, programming-friendly name (snake_case)
2. description: What this entity represents
3. validation_pattern: A regex pattern to validate this entity 
4. error_message: A helpful error message to show when validation fails
5. examples: An array of at least 3 diverse examples of this entity
6. required: Boolean indicating if this entity is required (true) or optional (false)

Format your response as a JSON array of entity objects with this structure:
[
  {
    "name": "entity_name",
    "description": "Description of what this entity represents",
    "validation_pattern": "^regex_pattern$",
    "error_message": "Please provide a valid entity_name",
    "examples": ["example1", "example2", "example3"],
    "required": true
  }
]

Aim to provide 3-5 well-defined entities that would be essential for the described use case.""",
            
            'response_schema': """You are an expert in designing structured response formats for AI agents.
Create a JSON schema that defines the structure of responses for a Staples customer service agent.
The schema should include fields for customer-facing text as well as structured data needed for processing.
Format your response as a JSON schema object with appropriate types and descriptions.""",
            
            'prompt_template': """You are an expert prompt engineer specializing in creating templates for specific customer service scenarios.
Create a prompt template for handling a specific type of customer inquiry at Staples.
The template should include placeholders for dynamic content in the format {placeholder_name}.
Provide only the template text without explanations.""",
            
            'output_template': """You are an expert in designing output templates for AI agent responses.
Create a template that will format structured data into a user-friendly response.
The template should include placeholders in the format {field_name} that correspond to fields in the response schema.
Focus on creating a clear, professional response that presents information in a logical order.
Provide only the template text without explanations."""
        }
        
        # Select appropriate system prompt
        system_prompt = system_prompts.get(assistance_type, """You are an AI assistant helping to configure a customer service agent. 
Provide helpful, detailed suggestions based on the user's request.""")
        
        # Construct user prompt based on assistance type and context
        user_prompt = f"I'm creating a {agent_type} agent for Staples and need help with {assistance_type}.\n\n"
        user_prompt += f"Description: {description}\n\n"
        
        # Add existing context if available
        if existing_context:
            user_prompt += f"Here's my current configuration:\n{json.dumps(existing_context, indent=2)}\n\n"
        
        user_prompt += "Please provide suggestions that would work well for this specific use case."
        
        # Call the LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        # Process response based on assistance type
        result = response.choices[0].message.content
        
        # For structured outputs, attempt to parse JSON
        if assistance_type in ['entity_definition', 'response_schema']:
            try:
                # Find JSON in the response if it's wrapped in markdown or explanations
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result)
                if json_match:
                    result = json_match.group(1)
                
                # Try to parse as JSON
                result = json.loads(result)
            except json.JSONDecodeError:
                # If parsing fails, return raw text
                logger.warning(f"Failed to parse LLM response as JSON: {result}")
                pass
        
        return jsonify({
            'suggestion': result,
            'assistance_type': assistance_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error in LLM assistant: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500