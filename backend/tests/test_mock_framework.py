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
        result2 = mock_llm.invoke("Another input")
        self.assertEqual(result2.content, "Response 2")
        
        # Test that it cycles back to the start when responses are exhausted
        mock_llm.invoke("Third input")
        result4 = mock_llm.invoke("Fourth input")
        self.assertEqual(result4.content, "Response 1")
    
    def test_incorrect_response_format(self):
        """Test what happens if responses aren't strings"""
        # Create a mock with non-string responses
        mock_llm = create_mock_chat_model(responses=[{"answer": "test"}])
        
        # Should convert to string representation
        result = mock_llm.invoke("Test input")
        self.assertEqual(result.content, "{'answer': 'test'}")


class TestAsyncMockFramework(unittest.IsolatedAsyncioTestCase):
    """Test the async features of the mock framework"""
    
    async def test_mock_llm_async(self):
        """Test that the mock LLM works in asynchronous mode"""
        # Create a mock LLM with predetermined responses
        responses = ["Async Response 1", "Async Response 2"]
        mock_llm = create_mock_chat_model(responses=responses)
        
        # Test ainvoke (asynchronous)
        result = await mock_llm.ainvoke("Test input")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "Async Response 1")
        
        # Test second async call
        result2 = await mock_llm.ainvoke("Another input")
        self.assertEqual(result2.content, "Async Response 2")
    
    async def test_async_chain_mock(self):
        """Test the async chain mock"""
        mock_chain = create_async_chain_mock("Chain response")
        
        # Test ainvoke
        result = await mock_chain.ainvoke({"input": "test"})
        self.assertEqual(result["output"], "Chain response")
        
        # Test with different input
        result2 = await mock_chain.ainvoke({"input": "different test"})
        self.assertEqual(result2["output"], "Chain response")


if __name__ == "__main__":
    unittest.main()