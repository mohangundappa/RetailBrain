"""
Integration tests for complex conversation flows involving multiple agents.
These tests simulate realistic user interactions with interruptions and context switches.
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
from config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT
)


class TestComplexConversationFlow(unittest.TestCase):
    """Tests for simulating realistic conversation flows."""
    
    def setUp(self):
        """Set up the test environment."""
        # We'll use a patch for the LLM import to avoid actual API calls
        self.llm_patcher = patch('langchain_community.chat_models.ChatOpenAI')
        self.mock_llm = self.llm_patcher.start()
        
        # Create a mock for the LLM response
        self.mock_llm.return_value = MagicMock()
        
        # Set environment variables for initialization
        os.environ["OPENAI_API_KEY"] = "test_api_key"
        
        # Mock the LLM response for various method calls
        async def mock_agenerate(*args, **kwargs):
            messages = kwargs.get("messages", [])
            # Extract the last user message for easier analysis
            user_message = ""
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            # Default content
            content = "0.9"
            
            # Check if this is a can_handle call
            if any("can you handle" in str(m).lower() for m in messages):
                # Adjust confidence based on the agent and query
                if "package" in user_message.lower() or "track" in user_message.lower():
                    return MagicMock(generations=[MagicMock(message=MagicMock(content="0.95"))])
                elif "password" in user_message.lower() or "login" in user_message.lower():
                    return MagicMock(generations=[MagicMock(message=MagicMock(content="0.9"))])
                elif "store" in user_message.lower() or "location" in user_message.lower():
                    return MagicMock(generations=[MagicMock(message=MagicMock(content="0.85"))])
                elif "product" in user_message.lower() or "printer" in user_message.lower():
                    return MagicMock(generations=[MagicMock(message=MagicMock(content="0.8"))])
                else:
                    return MagicMock(generations=[MagicMock(message=MagicMock(content="0.6"))])
            
            # Package tracking processing
            if any("package_tracking" in str(m).lower() for m in messages):
                if "zip code" in user_message.lower() or "zipcode" in user_message.lower():
                    # User is providing zip code
                    content = json.dumps({
                        "zip_code": "12345",
                        "tracking_number": None,
                        "message": "Thanks for providing your zip code. Can you also share your tracking number?"
                    })
                elif "track" in user_message.lower() or "tracking number" in user_message.lower():
                    if "ABC123" in user_message:
                        # User has provided tracking number
                        content = json.dumps({
                            "zip_code": "12345",
                            "tracking_number": "ABC123",
                            "message": "Your package with tracking number ABC123 is currently in transit and expected to be delivered on May 15th."
                        })
                    else:
                        # Asking for tracking number
                        content = json.dumps({
                            "zip_code": None,
                            "tracking_number": None,
                            "message": "To track your package, I'll need your zip code and tracking number."
                        })
                else:
                    # General package tracking response
                    content = json.dumps({
                        "zip_code": None,
                        "tracking_number": None,
                        "message": "I can help you track your package. Could you please provide your zip code?"
                    })
            
            # Password reset processing
            elif any("reset_password" in str(m).lower() for m in messages):
                if "email" in user_message.lower():
                    if "@" in user_message:
                        # User has provided email
                        content = json.dumps({
                            "email": "user@example.com",
                            "account_type": None,
                            "message": "Thank you for providing your email address. What type of account are you trying to access? (Staples.com, Rewards, Business account, etc.)"
                        })
                    else:
                        # Invalid email
                        content = json.dumps({
                            "email": None,
                            "account_type": None,
                            "message": "Please provide a valid email address."
                        })
                elif "account" in user_message.lower() or "staples.com" in user_message.lower():
                    # User provided account type
                    content = json.dumps({
                        "email": "user@example.com",
                        "account_type": "Staples.com",
                        "message": "I've sent password reset instructions to your email address (user@example.com). Please check your inbox and follow the instructions."
                    })
                else:
                    # General password reset response
                    content = json.dumps({
                        "email": None,
                        "account_type": None,
                        "message": "I can help you reset your password. Could you please provide the email address associated with your account?"
                    })
            
            # Store locator processing
            elif any("store_locator" in str(m).lower() for m in messages):
                if "zip code" in user_message.lower() or "zipcode" in user_message.lower() or "10001" in user_message:
                    # User has provided zip code
                    content = json.dumps({
                        "zip_code": "10001",
                        "location": "New York",
                        "message": "I found 3 Staples stores near zip code 10001: 1. Staples - Manhattan (1.2 miles away), 2. Staples - Chelsea (2.5 miles away), 3. Staples - Midtown (3.1 miles away)."
                    })
                else:
                    # General store locator response
                    content = json.dumps({
                        "zip_code": None,
                        "location": None,
                        "message": "I can help you find a Staples store. Could you please provide your zip code or city?"
                    })
            
            # Product info processing
            elif any("product_info" in str(m).lower() for m in messages):
                if "printer" in user_message.lower():
                    # User asking about printers
                    content = json.dumps({
                        "product_type": "printer",
                        "query": user_message,
                        "message": "We carry a variety of printers including inkjet, laser, and all-in-one models from brands like HP, Epson, Canon, and Brother."
                    })
                else:
                    # General product info response
                    content = json.dumps({
                        "product_type": None,
                        "query": user_message,
                        "message": "I can provide information about Staples products. What specific product or category are you interested in?"
                    })
            
            return MagicMock(generations=[MagicMock(message=MagicMock(content=content))])
        
        self.mock_llm.return_value._agenerate = mock_agenerate
        self.mock_llm.return_value._generate = lambda *args, **kwargs: asyncio.run(mock_agenerate(*args, **kwargs))
        
        # Initialize the brain
        self.brain = initialize_staples_brain()
    
    def tearDown(self):
        """Clean up after the test."""
        self.llm_patcher.stop()
    
    def test_realistic_conversation_with_interruptions(self):
        """
        Test a realistic conversation with multiple topics, interruptions, and context switches.
        This simulates a user who starts tracking a package, interrupts to ask about stores,
        then returns to the package tracking, and finally asks about products.
        """
        # Use the same session ID for all requests in this scenario
        session_id = "test_realistic_conversation"
        
        # Define conversation flow with expected agent and response checks
        conversation = [
            # Start with package tracking
            {
                "input": "I want to track my recent order",
                "expected_agent": PACKAGE_TRACKING_AGENT,
                "response_contains": "provide your zip code"
            },
            # Provide zip code
            {
                "input": "My zip code is 12345",
                "expected_agent": PACKAGE_TRACKING_AGENT,
                "response_contains": "tracking number"
            },
            # Interrupt with store question
            {
                "input": "Actually, where is the nearest Staples store?",
                "expected_agent": STORE_LOCATOR_AGENT,
                "response_contains": "zip code or city"
            },
            # Provide zip code for store locator
            {
                "input": "I'm in zip code 10001",
                "expected_agent": STORE_LOCATOR_AGENT,
                "response_contains": "stores near"
            },
            # Go back to package tracking
            {
                "input": "Going back to my package, the tracking number is ABC123",
                "expected_agent": PACKAGE_TRACKING_AGENT,
                "response_contains": "expected to be delivered"
            },
            # Switch to password reset
            {
                "input": "I also need to reset my password",
                "expected_agent": RESET_PASSWORD_AGENT,
                "response_contains": "email address"
            },
            # Provide email
            {
                "input": "My email is user@example.com",
                "expected_agent": RESET_PASSWORD_AGENT,
                "response_contains": "account"
            },
            # Provide account type
            {
                "input": "It's my Staples.com account",
                "expected_agent": RESET_PASSWORD_AGENT,
                "response_contains": "sent password reset"
            },
            # Final switch to product info
            {
                "input": "Can you tell me about printers?",
                "expected_agent": PRODUCT_INFO_AGENT,
                "response_contains": "inkjet"
            }
        ]
        
        # Process the conversation step by step
        for i, step in enumerate(conversation):
            with self.subTest(step=i+1, query=step["input"]):
                result = asyncio.run(self.brain.process_request(
                    step["input"], 
                    {"session_id": session_id}
                ))
                
                # Verify the correct agent was selected
                self.assertEqual(result["selected_agent"], step["expected_agent"],
                               f"Step {i+1}: Query '{step['input']}' should be handled by {step['expected_agent']}")
                
                # Verify response contains expected text
                self.assertIn(step["response_contains"].lower(), result["response"].lower(),
                            f"Step {i+1}: Response should contain '{step['response_contains']}'")
                
                # Print step details for debug
                print(f"Step {i+1}:")
                print(f"  Input: {step['input']}")
                print(f"  Agent: {result['selected_agent']} (Expected: {step['expected_agent']})")
                print(f"  Confidence: {result.get('confidence', 'N/A')}")
                print(f"  Response: {result['response'][:100]}...")
                print()


if __name__ == '__main__':
    unittest.main()