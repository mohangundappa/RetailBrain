"""
Configuration and fixtures for tests
"""
import os
import sys
import asyncio
from pathlib import Path
from unittest import TestCase

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the test utils
from tests.test_utils import (
    create_mock_chat_model,
    create_async_chain_mock,
    patch_llm_in_brain
)

# Functions to replace pytest fixtures
def mock_llm():
    """Mock LLM for testing"""
    responses = [
        "I understand you want to track your package",
        "I can help you reset your password",
        "I can find a store near you",
        "Here's the product information you requested"
    ]
    return create_mock_chat_model(responses=responses)

def mock_chain():
    """Mock chain for testing"""
    return create_async_chain_mock("This is a mock response")