"""
Test suite for API routes
"""
import unittest
import json
import os
from app import app, db
from models import CustomAgent, AgentComponent, ComponentConnection

class TestApiRoutes(unittest.TestCase):
    """Test case for API routes"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        self.client = app.test_client()
        
        # Create a test agent for reuse in tests
        self.test_agent_data = {
            'name': 'Test Agent',
            'description': 'An agent created during automated testing',
            'components': [
                {
                    'id': 'component-1',
                    'component_type': 'prompt',
                    'name': 'Intent Classifier',
                    'template': 'intent_classifier',
                    'position_x': 100,
                    'position_y': 100,
                    'configuration': {
                        'available_intents': 'test_intent_1, test_intent_2',
                        'system_prompt': 'Test prompt for intent classification',
                        'temperature': 0.3
                    }
                },
                {
                    'id': 'component-2',
                    'component_type': 'output',
                    'name': 'Response Formatter',
                    'template': 'json_formatter',
                    'position_x': 100,
                    'position_y': 300,
                    'configuration': {
                        'schema': '{"response": "string"}',
                        'enforce_schema': True
                    }
                }
            ],
            'connections': [
                {
                    'id': 'connection-1',
                    'source_id': 'component-1',
                    'target_id': 'component-2',
                    'connection_type': 'data'
                }
            ]
        }
        
    def tearDown(self):
        """Clean up after each test"""
        # Remove test agent if it exists
        with app.app_context():
            test_agent = CustomAgent.query.filter_by(name='Test Agent').first()
            if test_agent:
                db.session.delete(test_agent)
                db.session.commit()
    
    def test_agent_creation(self):
        """Test creating a new agent"""
        # Create agent
        response = self.client.post(
            '/api/builder/agents',
            data=json.dumps(self.test_agent_data),
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        # Assertions
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['name'], 'Test Agent')
        self.assertTrue('id' in data)
        
        # Verify agent was created in database
        with app.app_context():
            agent = CustomAgent.query.filter_by(name='Test Agent').first()
            self.assertIsNotNone(agent)
            self.assertEqual(agent.description, 'An agent created during automated testing')
            
            # Verify components were created
            components = AgentComponent.query.filter_by(agent_id=agent.id).all()
            self.assertEqual(len(components), 2)
            
            # Verify connections were created
            connections = ComponentConnection.query.filter_by(agent_id=agent.id).all()
            self.assertEqual(len(connections), 1)
    
    def test_agent_update(self):
        """Test updating an existing agent"""
        # First create the agent
        create_response = self.client.post(
            '/api/builder/agents',
            data=json.dumps(self.test_agent_data),
            content_type='application/json'
        )
        create_data = json.loads(create_response.data)
        agent_id = create_data['id']
        
        # Now update it
        update_data = self.test_agent_data.copy()
        update_data['id'] = agent_id
        update_data['name'] = 'Updated Test Agent'
        update_data['description'] = 'This agent was updated during testing'
        
        # Change a component configuration
        update_data['components'][0]['configuration']['system_prompt'] = 'Updated test prompt'
        
        update_response = self.client.put(
            f'/api/builder/agents/{agent_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        update_result = json.loads(update_response.data)
        
        # Assertions
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_result['name'], 'Updated Test Agent')
        
        # Verify changes in database
        with app.app_context():
            agent = CustomAgent.query.get(agent_id)
            self.assertEqual(agent.name, 'Updated Test Agent')
            self.assertEqual(agent.description, 'This agent was updated during testing')
            
            # Get updated configuration from database
            config = json.loads(agent.configuration)
            self.assertEqual(
                config['components'][0]['configuration']['system_prompt'], 
                'Updated test prompt'
            )
    
    def test_agent_deletion(self):
        """Test deleting an agent"""
        # First create the agent
        create_response = self.client.post(
            '/api/builder/agents',
            data=json.dumps(self.test_agent_data),
            content_type='application/json'
        )
        create_data = json.loads(create_response.data)
        agent_id = create_data['id']
        
        # Now delete it
        delete_response = self.client.delete(f'/api/builder/agents/{agent_id}')
        delete_result = json.loads(delete_response.data)
        
        # Assertions
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn('deleted successfully', delete_result['message'])
        
        # Verify agent no longer exists in database
        with app.app_context():
            agent = CustomAgent.query.get(agent_id)
            self.assertIsNone(agent)
            
            # Verify components were deleted
            components = AgentComponent.query.filter_by(agent_id=agent_id).all()
            self.assertEqual(len(components), 0)
            
            # Verify connections were deleted
            connections = ComponentConnection.query.filter_by(agent_id=agent_id).all()
            self.assertEqual(len(connections), 0)
            
    def test_agent_retrieval(self):
        """Test retrieving an agent"""
        # First create the agent
        create_response = self.client.post(
            '/api/builder/agents',
            data=json.dumps(self.test_agent_data),
            content_type='application/json'
        )
        create_data = json.loads(create_response.data)
        agent_id = create_data['id']
        
        # Now retrieve it
        get_response = self.client.get(f'/api/builder/agents/{agent_id}')
        get_result = json.loads(get_response.data)
        
        # Assertions
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_result['name'], 'Test Agent')
        self.assertEqual(get_result['description'], 'An agent created during automated testing')
        self.assertEqual(len(get_result['components']), 2)
        self.assertEqual(len(get_result['connections']), 1)
        
    def test_list_agents(self):
        """Test listing all agents"""
        # Create a test agent
        self.client.post(
            '/api/builder/agents',
            data=json.dumps(self.test_agent_data),
            content_type='application/json'
        )
        
        # Get list of agents
        response = self.client.get('/api/builder/agents')
        result = json.loads(response.data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(result, list)
        
        # Check that our test agent is in the list
        test_agent_found = False
        for agent in result:
            if agent['name'] == 'Test Agent':
                test_agent_found = True
                break
                
        self.assertTrue(test_agent_found, "Test agent not found in agents list")


if __name__ == '__main__':
    unittest.main()