"""
Simple test file to verify our mock framework is working correctly
"""
import unittest
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from test_utils in the same directory
from test_utils import create_mock_chat_model, create_async_chain_mock

class TestMockFramework(unittest.TestCase):
    """Test the mock framework for LLMs and chains"""
    
    def test_mock_llm_sync(self):
        """Test that the mock LLM works in synchronous mode"""
        # Create a mock LLM with predetermined responses
        responses = ["Response 1", "Response 2", "Response 3"]
        mock_llm = create_mock_chat_model(responses=responses)
        
        # Test invoke (synchronous)
        result = mock_llm.invoke("Test input")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "Response 1")
        
        # Test invoke with new prompt
        result = mock_llm.invoke("Another input")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "Response 2")


class TestAsyncMockFramework(unittest.IsolatedAsyncioTestCase):
    """Test the async features of the mock framework"""
    
    async def test_mock_llm_async(self):
        """Test that the mock LLM works in asynchronous mode"""
        # Create a mock LLM with predetermined responses
        responses = ["Async Response 1", "Async Response 2"]
        mock_llm = create_mock_chat_model(responses=responses)
        
        # Test ainvoke (asynchronous)
        result = await mock_llm.ainvoke("Test async input")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "Async Response 1")
        
        # Test ainvoke with new prompt
        result = await mock_llm.ainvoke("Another async input")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "Async Response 2")
    
    async def test_mock_chain(self):
        """Test that the mock chain works"""
        # Create a mock chain
        expected_response = "Mock chain response"
        mock_chain = create_async_chain_mock(expected_response)
        
        # Test ainvoke
        result = await mock_chain.ainvoke({"input": "Test input"})
        self.assertIsNotNone(result)
        self.assertEqual(result, expected_response)
        
        # Test with different input
        result = await mock_chain.ainvoke({"query": "Another query"})
        self.assertIsNotNone(result)
        self.assertEqual(result, expected_response)


if __name__ == "__main__":
    unittest.main()