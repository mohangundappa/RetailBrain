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
from models import CustomAgent, AgentComponent, ComponentConnection, ComponentTemplate

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
        
        # Basic validation
        if not data.get('name'):
            return jsonify({'error': 'Agent name is required'}), 400
            
        # Check if name already exists
        existing = CustomAgent.query.filter_by(name=data['name']).first()
        if existing:
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
        
        # Add components
        component_id_map = {}
        for comp_data in data.get('components', []):
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data['component_type'],
                name=comp_data['name'],
                position_x=comp_data['position_x'],
                position_y=comp_data['position_y'],
                configuration=json.dumps(comp_data.get('configuration', {}))
            )
            
            db.session.add(component)
            db.session.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data['id']] = component.id
        
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
        
        # Store the original configuration as JSON
        agent.configuration = json.dumps(data)
        
        db.session.commit()
        
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
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
            
        data = request.json
        
        # Basic validation
        if not data.get('name'):
            return jsonify({'error': 'Agent name is required'}), 400
            
        # Check if name already exists (if changed)
        if data['name'] != agent.name:
            existing = CustomAgent.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'error': f"Agent with name '{data['name']}' already exists"}), 409
        
        # Delete existing components and connections
        ComponentConnection.query.filter_by(agent_id=agent.id).delete()
        AgentComponent.query.filter_by(agent_id=agent.id).delete()
        
        # Update agent
        agent.name = data['name']
        agent.description = data.get('description', '')
        agent.updated_at = datetime.utcnow()
        
        # Add new components
        component_id_map = {}
        for comp_data in data.get('components', []):
            component = AgentComponent(
                agent_id=agent.id,
                component_type=comp_data['component_type'],
                name=comp_data['name'],
                position_x=comp_data['position_x'],
                position_y=comp_data['position_y'],
                configuration=json.dumps(comp_data.get('configuration', {}))
            )
            
            db.session.add(component)
            db.session.flush()  # Get the component ID
            
            # Keep a mapping of frontend IDs to database IDs
            component_id_map[comp_data['id']] = component.id
        
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
        
        # Store the updated configuration as JSON
        agent.configuration = json.dumps(data)
        
        db.session.commit()
        
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