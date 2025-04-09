"""
Tests for agent interactions, context switching, and continuity.
These tests verify that the agent selection and context management work correctly.
"""

import unittest
import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brain.staples_brain import StaplesBrain, initialize_staples_brain
from brain.orchestrator import AgentOrchestrator
from config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT
)
from utils.memory import ConversationMemory


class TestAgentSelection(unittest.TestCase):
    """Tests for basic agent selection capabilities."""
    
    def setUp(self):
        """Set up the test environment."""
        # Set environment variables for initialization
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        
        # Initialize the brain
        self.brain = initialize_staples_brain()
        
        # Import here to avoid circular imports
        from tests.test_utils import create_mock_chat_model, patch_llm_in_brain
        
        # Replace the LLM with our mock
        self.mock_llm = create_mock_chat_model()
        patch_llm_in_brain(self.brain, self.mock_llm)
    
    def tearDown(self):
        """Clean up after the test."""
        # No cleanup needed
        pass
    
    def test_agent_creation(self):
        """Test that all agents are created with correct names."""
        agent_names = self.brain.get_agent_names()
        
        # Check that all expected agents are created
        self.assertIn(PACKAGE_TRACKING_AGENT, agent_names)
        self.assertIn(RESET_PASSWORD_AGENT, agent_names)
        self.assertIn(STORE_LOCATOR_AGENT, agent_names)
        self.assertIn(PRODUCT_INFO_AGENT, agent_names)
        
        # Check the total number of agents
        self.assertEqual(len(agent_names), 4)
    
    def test_package_tracking_selection(self):
        """Test that package tracking queries are routed to the correct agent."""
        queries = [
            "Where is my order?",
            "Track my package",
            "What's the status of my delivery?",
            "When will my order arrive?",
            "I want to know where my package is"
        ]
        
        for query in queries:
            with self.subTest(query=query):
                result = asyncio.run(self.brain.process_request(query, {"session_id": f"test_{hash(query)}"}))
                self.assertEqual(result["selected_agent"], PACKAGE_TRACKING_AGENT)
    
    def test_reset_password_selection(self):
        """Test that password reset queries are routed to the correct agent."""
        queries = [
            "I need to reset my password",
            "Forgot my login",
            "Can't access my account",
            "How do I change my password?",
            "Login trouble"
        ]
        
        for query in queries:
            with self.subTest(query=query):
                result = asyncio.run(self.brain.process_request(query, {"session_id": f"test_{hash(query)}"}))
                self.assertEqual(result["selected_agent"], RESET_PASSWORD_AGENT)
    
    def test_store_locator_selection(self):
        """Test that store locator queries are routed to the correct agent."""
        queries = [
            "Find a store near me",
            "Where is the nearest Staples?",
            "Staples locations",
            "Store hours",
            "Is there a Staples in New York?"
        ]
        
        for query in queries:
            with self.subTest(query=query):
                result = asyncio.run(self.brain.process_request(query, {"session_id": f"test_{hash(query)}"}))
                self.assertEqual(result["selected_agent"], STORE_LOCATOR_AGENT)
    
    def test_product_info_selection(self):
        """Test that product info queries are routed to the correct agent."""
        queries = [
            "Tell me about printers",
            "Do you sell notebooks?",
            "What laptops do you have?",
            "Price of ink cartridges",
            "Compare office chairs"
        ]
        
        for query in queries:
            with self.subTest(query=query):
                result = asyncio.run(self.brain.process_request(query, {"session_id": f"test_{hash(query)}"}))
                self.assertEqual(result["selected_agent"], PRODUCT_INFO_AGENT)


class TestAgentContextSwitching(unittest.TestCase):
    """Tests for agent context switching and continuity."""
    
    def setUp(self):
        """Set up the test environment."""
        # Set environment variables for initialization
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        
        # Initialize the brain
        self.brain = initialize_staples_brain()
        
        # Import here to avoid circular imports
        from tests.test_utils import create_mock_chat_model, patch_llm_in_brain
        
        # Create a mock LLM with appropriate responses for context switching tests
        responses = [
            "0.9",  # Confidence score
            json.dumps({"zip_code": None, "tracking_number": None, "message": "Please provide your zip code"}),
            json.dumps({"email": None, "account_type": None, "message": "Please provide your email address"}),
            json.dumps({"location": None, "zip_code": None, "message": "Please provide your location or zip code"}),
            json.dumps({"product_type": None, "query": None, "message": "What product are you interested in?"}),
            "0.9"   # Another confidence score for continuity tests
        ]
        
        # Replace the LLM with our mock
        self.mock_llm = create_mock_chat_model(responses=responses)
        patch_llm_in_brain(self.brain, self.mock_llm)
    
    def tearDown(self):
        """Clean up after the test."""
        # No cleanup needed
        pass
    
    def test_entity_collection_continuity(self):
        """Test that entity collection maintains continuity across multiple interactions."""
        # Use the same session ID for all requests in this test
        session_id = "test_entity_collection"
        
        # First message - Package tracking inquiry
        result1 = asyncio.run(self.brain.process_request(
            "I need to track my package", 
            {"session_id": session_id}
        ))
        
        # Should select package tracking agent
        self.assertEqual(result1["selected_agent"], PACKAGE_TRACKING_AGENT)
        self.assertIn("Please provide your zip code", result1["response"], 
                      "Should ask for zip code")
        
        # Second message - Provide zip code
        result2 = asyncio.run(self.brain.process_request(
            "My zip code is 12345", 
            {"session_id": session_id}
        ))
        
        # Should continue with package tracking agent
        self.assertEqual(result2["selected_agent"], PACKAGE_TRACKING_AGENT)
        
        # Check that the continue_with_same_agent flag is reset after use
        memory = self.brain.orchestrator.memories[session_id]
        self.assertFalse(memory.get_working_memory('continue_with_same_agent', False), 
                         "continue_with_same_agent flag should be reset after use")
    
    def test_agent_interruption(self):
        """Test that a conversation with one agent can be interrupted by a query for another agent."""
        # Use the same session ID for all requests in this test
        session_id = "test_interruption"
        
        # First message - Package tracking inquiry
        result1 = asyncio.run(self.brain.process_request(
            "I need to track my package", 
            {"session_id": session_id}
        ))
        
        # Should select package tracking agent
        self.assertEqual(result1["selected_agent"], PACKAGE_TRACKING_AGENT)
        
        # Interrupt with a completely different query
        result2 = asyncio.run(self.brain.process_request(
            "Where is the nearest Staples store?", 
            {"session_id": session_id}
        ))
        
        # Should switch to store locator agent
        self.assertEqual(result2["selected_agent"], STORE_LOCATOR_AGENT)
        
        # Go back to original conversation
        result3 = asyncio.run(self.brain.process_request(
            "Back to my package, the tracking number is ABC123", 
            {"session_id": session_id}
        ))
        
        # Should switch back to package tracking agent
        self.assertEqual(result3["selected_agent"], PACKAGE_TRACKING_AGENT)
    
    def test_agent_continuity_bonus(self):
        """Test that the continuity bonus increases confidence for the same agent."""
        # Use the same session ID for all requests in this test
        session_id = "test_continuity_bonus"
        
        # First message - Ambiguous query that could be product or store related
        with patch.object(self.brain.orchestrator, '_select_agent') as mock_select_agent:
            # Mock return values for _select_agent
            mock_select_agent.side_effect = [
                (self.brain.get_agent_by_name(PRODUCT_INFO_AGENT), 0.7, False),
                (self.brain.get_agent_by_name(PRODUCT_INFO_AGENT), 0.85, True)  # With continuity bonus
            ]
            
            # Initial query
            asyncio.run(self.brain.process_request(
                "Tell me about Staples", 
                {"session_id": session_id}
            ))
            
            # Set the continue_with_same_agent flag to True in the memory
            memory = self.brain.orchestrator.memories[session_id]
            memory.update_working_memory('continue_with_same_agent', True)
            memory.update_working_memory('last_selected_agent', PRODUCT_INFO_AGENT)
            
            # Follow-up query 
            result = asyncio.run(self.brain.process_request(
                "Do you have any more information?", 
                {"session_id": session_id}
            ))
            
            # The second call to _select_agent should include context
            args, kwargs = mock_select_agent.call_args_list[1]
            self.assertTrue(kwargs.get('context', {}).get('conversation_memory'), 
                           "Context should include conversation memory")
            
            # Confidence should be higher in the second call
            self.assertGreater(result["confidence"], 0.8, 
                              "Confidence score should include continuity bonus")
    
    def test_multiple_agent_interactions(self):
        """Test a complex conversation involving multiple agents."""
        # Use the same session ID for all requests in this test
        session_id = "test_multiple_agents"
        
        # Sequence of requests and expected agents
        conversation = [
            ("I need to track my package", PACKAGE_TRACKING_AGENT),
            ("My zip code is 12345", PACKAGE_TRACKING_AGENT),
            ("Actually, I forgot my password", RESET_PASSWORD_AGENT),
            ("My email is test@example.com", RESET_PASSWORD_AGENT),
            ("Where is the nearest store?", STORE_LOCATOR_AGENT),
            ("Let me go back to my package", PACKAGE_TRACKING_AGENT),
            ("Tell me about printers", PRODUCT_INFO_AGENT)
        ]
        
        for i, (query, expected_agent) in enumerate(conversation):
            with self.subTest(step=i+1, query=query):
                result = asyncio.run(self.brain.process_request(
                    query, 
                    {"session_id": session_id}
                ))
                
                self.assertEqual(result["selected_agent"], expected_agent,
                                f"Query '{query}' should be handled by {expected_agent}")
    
    def test_intent_based_routing(self):
        """Test that providing explicit intents routes to the correct agent."""
        # Use the same session ID for all requests in this test
        session_id = "test_intent_routing"
        
        # Sequence of requests with explicit intents
        conversation = [
            # Query with explicit intent
            (
                "I need help", 
                {"session_id": session_id, "intent": "package_tracking", "intent_confidence": 0.9},
                PACKAGE_TRACKING_AGENT
            ),
            # Another query with different intent
            (
                "I need help again", 
                {"session_id": session_id, "intent": "password_reset", "intent_confidence": 0.8},
                RESET_PASSWORD_AGENT
            ),
            # Query with low intent confidence (should use content-based routing)
            (
                "Where is the nearest store?", 
                {"session_id": session_id, "intent": "product_info", "intent_confidence": 0.3},
                STORE_LOCATOR_AGENT
            )
        ]
        
        for i, (query, context, expected_agent) in enumerate(conversation):
            with self.subTest(step=i+1, query=query, intent=context.get("intent")):
                result = asyncio.run(self.brain.process_request(query, context))
                
                self.assertEqual(result["selected_agent"], expected_agent,
                                f"Query '{query}' with intent '{context.get('intent')}' should be handled by {expected_agent}")


if __name__ == '__main__':
    unittest.main()