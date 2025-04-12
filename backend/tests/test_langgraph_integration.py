"""
Integration tests for LangGraph-based implementation with database-driven agents.
"""
import asyncio
import os
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.config.config import Config
from backend.database.db import get_db
from backend.agents.framework.langgraph import LangGraphAgent, LangGraphAgentFactory
from backend.agents.framework.langgraph.langgraph_orchestrator import LangGraphOrchestrator
from backend.services.graph_brain_service import GraphBrainService


class TestLangGraphIntegration(unittest.TestCase):
    """Test LangGraph integration with database-driven agents."""

    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Create a mock session
        self.mock_session = MagicMock(spec=AsyncSession)
        self.mock_get_db = lambda: self.mock_session

    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()

    def test_create_langgraph_agent(self):
        """Test creating a LangGraph agent."""
        # Create a test agent config
        config = {
            "id": str(uuid.uuid4()),
            "name": "Test Agent",
            "description": "A test agent",
            "patterns": [],
            "tools": [],
            "response_templates": {},
            "entity_definitions": []
        }

        # Create the agent
        agent = LangGraphAgent(config)

        # Assert the agent was created with the correct config
        self.assertEqual(agent.name, "Test Agent")
        self.assertEqual(agent.description, "A test agent")

    @patch('backend.services.graph_brain_service.ChatOpenAI')
    def test_create_brain_service(self, mock_chat_openai):
        """Test creating a Graph brain service."""
        # Mock the LLM
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm

        # Create the brain service
        service = GraphBrainService(db_session=self.mock_session)

        # Assert the service was created
        self.assertIsNotNone(service)
        self.assertEqual(service.db_session, self.mock_session)

    def test_run_agent_function(self):
        """Test running an agent function."""
        # Create a test agent config
        config = {
            "id": str(uuid.uuid4()),
            "name": "Test Agent",
            "description": "A test agent",
            "patterns": [],
            "tools": [],
            "response_templates": {},
            "entity_definitions": []
        }

        # Create the agent
        agent = LangGraphAgent(config)

        # We'll test the _initialize_state function since it's synchronous
        state = {
            "messages": [],
            "context": {},
            "entities": {},
            "tools_calls": [],
            "tools_results": [],
            "agent_config": config,
            "current_step": "initialize",
            "memory": {}
        }

        # Call the function
        result = agent._initialize_state(state)

        # Assert it did what we expected
        self.assertEqual(result["current_step"], "extract_entities")

    def test_orchestrator_list_agents(self):
        """Test the orchestrator's list_agents method."""
        # Create test agents
        config1 = {
            "id": str(uuid.uuid4()),
            "name": "Test Agent 1",
            "description": "A test agent",
            "patterns": [],
            "tools": [],
            "response_templates": {},
            "entity_definitions": []
        }
        config2 = {
            "id": str(uuid.uuid4()),
            "name": "Test Agent 2",
            "description": "Another test agent",
            "patterns": [],
            "tools": [],
            "response_templates": {},
            "entity_definitions": []
        }

        agent1 = LangGraphAgent(config1)
        agent2 = LangGraphAgent(config2)

        # Create the orchestrator
        orchestrator = LangGraphOrchestrator(agents=[agent1, agent2])

        # Get the list of agents
        agents = orchestrator.list_agents()

        # Assert the correct agents are returned
        self.assertEqual(len(agents), 2)
        self.assertIn("Test Agent 1", agents)
        self.assertIn("Test Agent 2", agents)

    @patch('backend.repositories.agent_repository.AgentRepository')
    @patch('backend.agents.framework.langgraph.langgraph_factory.AgentRepository')
    def test_agent_factory_initialization(self, mock_repo_class, mock_repo_import):
        """Test initializing the agent factory."""
        # Setup mock
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo_import.return_value = mock_repo

        # Create the factory
        factory = LangGraphAgentFactory(self.mock_session)

        # Assert the factory was created with the correct repository
        self.assertEqual(factory.db_session, self.mock_session)
        self.assertIsNotNone(factory.agent_repository)


# This allows the test to be run standalone
if __name__ == '__main__':
    unittest.main()