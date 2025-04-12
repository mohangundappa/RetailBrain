"""
Tests for the Agent Builder functionality.

This module tests the creation, retrieval, updating, and deletion of custom agents
through the Agent Builder API.
"""

import json
import unittest
from datetime import datetime
from unittest.mock import patch

from app import app, db
from models import CustomAgent, AgentComponent, ComponentConnection


class TestAgentBuilder(unittest.TestCase):
    """Tests for the Agent Builder API."""

    def setUp(self):
        """Set up test environment before each test."""
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Sample data for creating a custom agent
        self.sample_agent_data = {
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
        
        # Created test agents to clean up later
        self.test_agent_ids = []

    def tearDown(self):
        """Clean up after each test."""
        # Delete any test agents that were created
        for agent_id in self.test_agent_ids:
            agent = CustomAgent.query.get(agent_id)
            if agent:
                db.session.delete(agent)
        
        db.session.commit()
        self.app_context.pop()

    def create_test_agent(self):
        """Create a test agent and return its ID."""
        response = self.client.post('/api/builder/agents', 
                               json=self.sample_agent_data, 
                               content_type='application/json')
        data = json.loads(response.data)
        agent_id = data['id']
        self.test_agent_ids.append(agent_id)
        return agent_id

    def test_create_agent(self):
        """Test creating a new custom agent."""
        response = self.client.post('/api/builder/agents', 
                               json=self.sample_agent_data, 
                               content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.test_agent_ids.append(data['id'])
        
        # Verify the agent was created with correct data
        self.assertIn('id', data)
        self.assertEqual(data['name'], self.sample_agent_data['name'])
        self.assertEqual(data['description'], self.sample_agent_data['description'])
        
        # Check that components were created
        self.assertIn('components', data)
        self.assertEqual(len(data['components']), len(self.sample_agent_data['components']))
        
        # Check that connections were created
        self.assertIn('connections', data)
        self.assertEqual(len(data['connections']), len(self.sample_agent_data['connections']))

    def test_get_agent(self):
        """Test retrieving a specific agent."""
        agent_id = self.create_test_agent()
        
        response = self.client.get(f'/api/builder/agents/{agent_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['id'], agent_id)
        self.assertEqual(data['name'], self.sample_agent_data['name'])
        self.assertEqual(len(data['components']), len(self.sample_agent_data['components']))
        self.assertEqual(len(data['connections']), len(self.sample_agent_data['connections']))

    def test_update_agent(self):
        """Test updating an existing agent."""
        agent_id = self.create_test_agent()
        
        # Modify the agent data
        updated_data = self.sample_agent_data.copy()
        updated_data['name'] = "Updated Test Agent"
        updated_data['description'] = "This agent has been updated"
        
        response = self.client.put(f'/api/builder/agents/{agent_id}', 
                              json=updated_data, 
                              content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify the update
        response = self.client.get(f'/api/builder/agents/{agent_id}')
        data = json.loads(response.data)
        self.assertEqual(data['name'], "Updated Test Agent")
        self.assertEqual(data['description'], "This agent has been updated")

    def test_list_agents(self):
        """Test listing all agents."""
        agent_id = self.create_test_agent()
        
        response = self.client.get('/api/builder/agents')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('agents', data)
        self.assertIsInstance(data['agents'], list)
        
        # Check that our test agent is in the list
        found = False
        for agent in data['agents']:
            if agent['id'] == agent_id:
                found = True
                break
        self.assertTrue(found, "Test agent not found in the list of agents")

    def test_delete_agent(self):
        """Test deleting an agent."""
        agent_id = self.create_test_agent()
        
        response = self.client.delete(f'/api/builder/agents/{agent_id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify it's gone
        response = self.client.get(f'/api/builder/agents/{agent_id}')
        self.assertEqual(response.status_code, 404)
        
        # Remove from cleanup list since it's already deleted
        self.test_agent_ids.remove(agent_id)

    def test_missing_template_handling(self):
        """Test that the API handles components missing the template field."""
        agent_id = self.create_test_agent()
        
        # Manually modify the agent in the database to remove template field
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
        response = self.client.get(f'/api/builder/agents/{agent_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check that all components have the template field
        for component in data['components']:
            self.assertIn('template', component)
            self.assertIsNotNone(component['template'])

    def test_test_agent_endpoint(self):
        """Test the agent testing endpoint."""
        agent_id = self.create_test_agent()
        test_input = "I want to return a defective product"
        
        response = self.client.post(f'/api/builder/agents/{agent_id}/test', 
                               json={"input": test_input}, 
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['input'], test_input)
        self.assertIn('response', data)
        self.assertIn('timestamp', data)

    def test_invalid_agent_id(self):
        """Test handling of invalid agent IDs."""
        # Non-existent agent ID
        response = self.client.get('/api/builder/agents/9999')
        self.assertEqual(response.status_code, 404)
        
        # Invalid format (non-numeric)
        response = self.client.get('/api/builder/agents/invalid')
        self.assertEqual(response.status_code, 404)  # or could be 400 depending on routing

    def test_malformed_agent_data(self):
        """Test handling of malformed agent data."""
        # Missing required fields
        response = self.client.post('/api/builder/agents', 
                               json={"description": "No name provided"}, 
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Duplicate name
        agent_data = {
            "name": "Duplicate Agent Test",
            "description": "Test agent with duplicate name",
            "components": []
        }
        
        # Create first agent
        response = self.client.post('/api/builder/agents', 
                               json=agent_data, 
                               content_type='application/json')
        self.assertEqual(response.status_code, 201)
        first_id = json.loads(response.data)['id']
        self.test_agent_ids.append(first_id)
        
        # Try to create second agent with same name
        response = self.client.post('/api/builder/agents', 
                               json=agent_data, 
                               content_type='application/json')
        self.assertEqual(response.status_code, 409)  # Conflict


if __name__ == "__main__":
    unittest.main()