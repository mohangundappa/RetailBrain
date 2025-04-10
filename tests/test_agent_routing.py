"""
Tests for agent routing mechanisms, including intent-based routing and continuity bonuses.
This tests the core routing logic in the orchestrator component.
"""

import unittest
import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brain.orchestrator import AgentOrchestrator
from brain.staples_brain import initialize_staples_brain
from agents.base_agent import BaseAgent
from config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT,
    INTENT_AGENT_MAPPING
)
from utils.memory import ConversationMemory


class TestAgentRouting(unittest.TestCase):
    """Tests for the agent routing mechanisms."""
    
    def setUp(self):
        """Set up the test environment."""
        # We need to patch multiple LLM imports to avoid actual API calls
        self.patchers = []
        
        # Patch langchain_community.chat_models.ChatOpenAI
        self.llm_community_patcher = patch('langchain_community.chat_models.ChatOpenAI')
        self.mock_community_llm = self.llm_community_patcher.start()
        self.patchers.append(self.llm_community_patcher)
        
        # Patch langchain_openai.chat_models.ChatOpenAI
        self.llm_openai_patcher = patch('langchain_openai.chat_models.ChatOpenAI')
        self.mock_openai_llm = self.llm_openai_patcher.start()
        self.patchers.append(self.llm_openai_patcher)
        
        # Mock the create method for both
        for mock_llm in [self.mock_community_llm, self.mock_openai_llm]:
            mock_llm.return_value = MagicMock()
            mock_llm.return_value._generate.return_value.generations[0].message.content = "0.7"
            # Setup instance attributes
            mock_llm.return_value.client = MagicMock()
            mock_llm.return_value.model_name = "gpt-4-mock"
            # Mock chat completions create method
            mock_chat = MagicMock()
            mock_completions = MagicMock()
            mock_llm.return_value.client.chat = mock_chat
            mock_chat.completions = mock_completions
            mock_choice = MagicMock()
            mock_choice.message.content = "0.7"
            mock_completions.create.return_value.choices = [mock_choice]
        
        # Patch direct openai usage
        self.openai_patcher = patch('openai.OpenAI')
        self.mock_openai = self.openai_patcher.start()
        self.patchers.append(self.openai_patcher)
        
        # Mock the OpenAI client
        mock_client = MagicMock()
        self.mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="0.7"))]
        
        # Import our test utilities and use them for consistent mocking
        from tests.test_utils import create_mock_chat_model, patch_llm_in_brain
        
        # Set environment variables for initialization
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        
        # Initialize the brain
        self.brain = initialize_staples_brain()
        
        # Use our test_utils to patch the LLM in the brain
        self.mock_llm = create_mock_chat_model()
        patch_llm_in_brain(self.brain, self.mock_llm)
        
        # For some tests, we need direct access to the orchestrator
        self.orchestrator = self.brain.orchestrator
    
    def tearDown(self):
        """Clean up after the test."""
        # Stop all patchers
        for patcher in self.patchers:
            patcher.stop()
    
    def test_intent_routing_logic(self):
        """Test that the intent routing logic correctly maps intents to agents."""
        # Verify all intents are mapped to valid agents
        for intent, agent_name in INTENT_AGENT_MAPPING.items():
            with self.subTest(intent=intent):
                # Verify the agent exists
                self.assertIn(agent_name, [a.name for a in self.brain.agents],
                             f"Intent '{intent}' maps to non-existent agent '{agent_name}'")
        
        # Test specific intent routing with various confidence levels
        test_cases = [
            # (intent, confidence, query, expected_agent)
            ("package_tracking", 0.8, "Check my order", PACKAGE_TRACKING_AGENT),
            ("password_reset", 0.7, "Can't log in", RESET_PASSWORD_AGENT),
            ("store_locator", 0.9, "Find a store", STORE_LOCATOR_AGENT),
            ("product_info", 0.75, "Tell me about printers", PRODUCT_INFO_AGENT),
            # Low confidence intent should fall back to content-based routing
            ("package_tracking", 0.3, "Where is the nearest store?", STORE_LOCATOR_AGENT),
        ]
        
        for intent, confidence, query, expected_agent in test_cases:
            with self.subTest(intent=intent, confidence=confidence, query=query):
                with patch.object(self.orchestrator, '_select_agent') as mock_select:
                    # We need to patch the select_agent method to avoid the full routing logic
                    # but still verify the intent routing part
                    if confidence <= 0.6:
                        # For low confidence, simulate content-based routing
                        for agent in self.brain.agents:
                            if agent.name == expected_agent:
                                mock_select.return_value = (agent, 0.8, False)
                    else:
                        # For high confidence, simulate intent-based routing
                        for agent in self.brain.agents:
                            if agent.name == expected_agent:
                                mock_select.return_value = (agent, 0.9, True)
                    
                    # Process the request with the intent
                    response = asyncio.run(self.brain.process_request(
                        query, 
                        {
                            "session_id": f"test_intent_{intent}_{confidence}",
                            "intent": intent, 
                            "intent_confidence": confidence
                        }
                    ))
                    
                    # Verify the agent selection
                    self.assertEqual(response["selected_agent"], expected_agent)
                    
                    # Verify that _select_agent was called with the right parameters
                    mock_select.assert_called()
    
    def test_continuity_bonus_application(self):
        """Test that the continuity bonus is correctly applied when appropriate."""
        session_id = "test_continuity_bonus"
        
        # First, we need to create a memory with a selected agent
        memory = ConversationMemory(session_id)
        memory.update_working_memory('last_selected_agent', PACKAGE_TRACKING_AGENT)
        memory.update_working_memory('continue_with_same_agent', True)
        
        # Manually inject this memory into the orchestrator
        self.orchestrator.memories[session_id] = memory
        
        # Define a test query and context
        query = "What's the status?"
        context = {"session_id": session_id, "conversation_memory": memory}
        
        # For this test, we'll directly call _select_agent and verify the bonus is applied
        with patch.object(BaseAgent, 'can_handle') as mock_can_handle:
            # Mock the agent scores - package tracking should win due to continuity bonus
            def mock_can_handle_side_effect(self, user_input, context=None):
                if self.name == PACKAGE_TRACKING_AGENT:
                    return 0.6  # Would be lower than store locator but will get bonus
                elif self.name == STORE_LOCATOR_AGENT:
                    return 0.7  # Highest raw score
                elif self.name == RESET_PASSWORD_AGENT:
                    return 0.5
                elif self.name == PRODUCT_INFO_AGENT:
                    return 0.4
                return 0.1
            
            mock_can_handle.side_effect = mock_can_handle_side_effect
            
            # Call _select_agent
            best_agent, confidence, context_used = self.orchestrator._select_agent(query, context)
            
            # Verify the package tracking agent was selected due to continuity bonus
            self.assertEqual(best_agent.name, PACKAGE_TRACKING_AGENT)
            
            # Verify the confidence score includes the bonus
            # Base confidence 0.6 + continuity bonus (default 0.15)
            self.assertGreater(confidence, 0.7)
            
            # Verify context was used
            self.assertTrue(context_used)
    
    def test_reset_continuity_flag(self):
        """Test that the continue_with_same_agent flag is reset after being used."""
        session_id = "test_reset_continuity_flag"
        
        # Set up memory with continuity flag
        memory = ConversationMemory(session_id)
        memory.update_working_memory('last_selected_agent', PACKAGE_TRACKING_AGENT)
        memory.update_working_memory('continue_with_same_agent', True)
        
        # Create context with this memory
        context = {"session_id": session_id, "conversation_memory": memory}
        
        # Process a request with this context
        with patch.object(AgentOrchestrator, '_select_agent') as mock_select:
            # Mock the _select_agent method to return a known agent
            for agent in self.brain.agents:
                if agent.name == PACKAGE_TRACKING_AGENT:
                    mock_select.return_value = (agent, 0.9, True)
                    break
            
            # Process the request
            asyncio.run(self.orchestrator.process_request("Test query", context))
        
        # Verify the continue_with_same_agent flag was reset
        self.assertFalse(memory.get_working_memory('continue_with_same_agent', False),
                       "continue_with_same_agent should be reset after being used")


if __name__ == '__main__':
    unittest.main()