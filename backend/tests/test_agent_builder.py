"""
Tests for the Agent Builder functionality.

This module tests the creation, retrieval, updating, and deletion of custom agents
through the Agent Builder API.
"""

import json
import pytest
from flask import url_for
from datetime import datetime
from unittest.mock import patch

from app import app, db
from models import CustomAgent, AgentComponent, ComponentConnection

@pytest.fixture
def client():
    """Test client fixture."""
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def sample_agent_data():
    """Sample data for creating a custom agent."""
    return {
        "name": "Test Customer Service Agent",
        "description": "An agent for handling customer service queries",
        "components": [
            {
                "id": "component-1",
                "component_type": "prompt",
                "template": "intent_classifier",
                "name": "Intent Classifier",
                "position_x": 100,
                "position_y": 100,
                "configuration": {
                    "available_intents": "order_status, returns, product_info",
                    "system_prompt": "Classify the intent of this customer service query."
                }
            },
            {
                "id": "component-2",
                "component_type": "llm",
                "template": "openai_gpt4",
                "name": "GPT-4 Model",
                "position_x": 100,
                "position_y": 250,
                "configuration": {
                    "model_name": "gpt-4o",
                    "temperature": 0.3
                }
            },
            {
                "id": "component-3",
                "component_type": "output",
                "template": "json_formatter",
                "name": "Response Formatter",
                "position_x": 100,
                "position_y": 400,
                "configuration": {
                    "schema": "{\n  \"response\": \"string\",\n  \"confidence\": \"number\"\n}"
                }
            }
        ],
        "connections": [
            {
                "id": "connection-1",
                "source_id": "component-1",
                "target_id": "component-2",
                "connection_type": "default"
            },
            {
                "id": "connection-2",
                "source_id": "component-2",
                "target_id": "component-3",
                "connection_type": "default"
            }
        ]
    }

@pytest.fixture
def create_test_agent(client, sample_agent_data):
    """Create a test agent and return its ID."""
    response = client.post('/api/builder/agents', 
                           json=sample_agent_data, 
                           content_type='application/json')
    data = json.loads(response.data)
    yield data['id']
    
    # Cleanup after test
    with app.app_context():
        agent = CustomAgent.query.get(data['id'])
        if agent:
            db.session.delete(agent)
            db.session.commit()

def test_create_agent(client, sample_agent_data):
    """Test creating a new custom agent."""
    response = client.post('/api/builder/agents', 
                           json=sample_agent_data, 
                           content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'id' in data
    assert data['name'] == sample_agent_data['name']
    
    # Cleanup
    with app.app_context():
        agent = CustomAgent.query.get(data['id'])
        db.session.delete(agent)
        db.session.commit()

def test_get_agent(client, create_test_agent):
    """Test retrieving a specific agent."""
    agent_id = create_test_agent
    response = client.get(f'/api/builder/agents/{agent_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == agent_id
    assert len(data['components']) == 3
    assert len(data['connections']) == 2
    
    # Check that all components have the required template field
    for component in data['components']:
        assert 'template' in component
        assert component['template'] is not None

def test_update_agent(client, create_test_agent, sample_agent_data):
    """Test updating an existing agent."""
    agent_id = create_test_agent
    
    # Modify the agent data for update
    updated_data = sample_agent_data.copy()
    updated_data['name'] = "Updated Agent Name"
    updated_data['description'] = "Updated description"
    
    # Add a new component
    updated_data['components'].append({
        "id": "component-4",
        "component_type": "tool",
        "template": "database_query",
        "name": "Database Query Tool",
        "position_x": 300,
        "position_y": 250,
        "configuration": {
            "query_template": "SELECT * FROM {table} WHERE {condition}"
        }
    })
    
    # Add a new connection
    updated_data['connections'].append({
        "id": "connection-3",
        "source_id": "component-1",
        "target_id": "component-4",
        "connection_type": "alternate"
    })
    
    response = client.put(f'/api/builder/agents/{agent_id}', 
                          json=updated_data, 
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == agent_id
    assert data['name'] == "Updated Agent Name"
    
    # Verify the update in the database
    response = client.get(f'/api/builder/agents/{agent_id}')
    agent_data = json.loads(response.data)
    assert len(agent_data['components']) == 4
    assert len(agent_data['connections']) == 3

def test_list_agents(client, create_test_agent):
    """Test listing all agents."""
    response = client.get('/api/builder/agents')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    
    # Find our test agent in the list
    agent_id = create_test_agent
    found = False
    for agent in data:
        if agent['id'] == agent_id:
            found = True
            break
    assert found, "Test agent not found in the list of agents"

def test_delete_agent(client, create_test_agent):
    """Test deleting an agent."""
    agent_id = create_test_agent
    response = client.delete(f'/api/builder/agents/{agent_id}')
    assert response.status_code == 200
    
    # Verify it's gone
    response = client.get(f'/api/builder/agents/{agent_id}')
    assert response.status_code == 404

def test_missing_template_handling(client, create_test_agent):
    """Test that the API handles components missing the template field."""
    agent_id = create_test_agent
    
    # Manually modify the agent in the database to remove template field
    with app.app_context():
        agent = CustomAgent.query.get(agent_id)
        config = json.loads(agent.configuration)
        
        # Remove template from a component
        for component in config['components']:
            if 'template' in component:
                del component['template']
                break
        
        agent.configuration = json.dumps(config)
        db.session.commit()
    
    # Now try to retrieve it - should add default templates
    response = client.get(f'/api/builder/agents/{agent_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Check that all components have the template field
    for component in data['components']:
        assert 'template' in component
        assert component['template'] is not None

def test_test_agent_endpoint(client, create_test_agent):
    """Test the agent testing endpoint."""
    agent_id = create_test_agent
    test_input = "I want to return a defective product"
    
    response = client.post(f'/api/builder/agents/{agent_id}/test', 
                           json={"input": test_input}, 
                           content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['input'] == test_input
    assert 'response' in data
    assert 'timestamp' in data

def test_invalid_agent_id(client):
    """Test handling of invalid agent IDs."""
    # Non-existent agent ID
    response = client.get('/api/builder/agents/9999')
    assert response.status_code == 404
    
    # Invalid format (non-numeric)
    response = client.get('/api/builder/agents/invalid')
    assert response.status_code == 404  # or could be 400 depending on routing

def test_malformed_agent_data(client):
    """Test handling of malformed agent data."""
    # Missing required fields
    response = client.post('/api/builder/agents', 
                           json={"description": "No name provided"}, 
                           content_type='application/json')
    assert response.status_code == 400
    
    # Duplicate name
    agent_data = {
        "name": "Duplicate Agent Test",
        "description": "Test agent with duplicate name",
        "components": []
    }
    
    # Create first agent
    response = client.post('/api/builder/agents', 
                           json=agent_data, 
                           content_type='application/json')
    assert response.status_code == 201
    first_id = json.loads(response.data)['id']
    
    # Try to create second agent with same name
    response = client.post('/api/builder/agents', 
                           json=agent_data, 
                           content_type='application/json')
    assert response.status_code == 409  # Conflict
    
    # Cleanup
    with app.app_context():
        agent = CustomAgent.query.get(first_id)
        db.session.delete(agent)
        db.session.commit()