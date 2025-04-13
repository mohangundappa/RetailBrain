#!/usr/bin/env python3
"""
Test script to verify that the system correctly routes to specific agents.
"""

import sys
import json
import aiohttp
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("brain_tester")

# API endpoint
API_BASE_URL = "http://localhost:5000/api/v1"
CHAT_ENDPOINT = f"{API_BASE_URL}/optimized/chat"

# Test messages specifically designed to trigger different agents
TEST_MESSAGES = [
    {
        "message": "I need to reset my password for my Staples account",
        "expected_agent": "Reset Password"
    },
    {
        "message": "Can you help me track my order #ST12345?",
        "expected_agent": "Package Tracking"
    },
    {
        "message": "Where is the nearest Staples store to zip code 90210?",
        "expected_agent": "Store Locator"
    },
    {
        "message": "I want to return a printer I bought last week",
        "expected_agent": "Returns Processing"
    }
]

async def send_message(session, message, session_id):
    """Send a message to the brain API."""
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    logger.info(f"Sending message: {message}")
    
    try:
        async with session.post(CHAT_ENDPOINT, json=payload, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                text = await response.text()
                logger.error(f"API error {response.status}: {text}")
                return None
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return None

async def test_agents():
    """Test specific agent routing."""
    # Generate a unique session ID for this test run
    session_id = f"test-agent-routing"
    
    logger.info(f"Starting agent routing test with session_id: {session_id}")
    
    async with aiohttp.ClientSession() as session:
        for test_case in TEST_MESSAGES:
            message = test_case["message"]
            expected_agent = test_case["expected_agent"]
            
            logger.info(f"Testing message expected to route to {expected_agent} agent")
            
            try:
                result = await asyncio.wait_for(
                    send_message(session, message, session_id),
                    timeout=30
                )
                
                if result:
                    agent_name = result.get('agent', 'unknown')
                    confidence = result.get('confidence', 0)
                    
                    # Check if the agent name contains the expected agent name
                    if expected_agent.lower() in agent_name.lower():
                        logger.info(f"✅ SUCCESS: Routed to {agent_name} as expected")
                    else:
                        logger.warning(f"❌ FAILED: Expected {expected_agent} but got {agent_name}")
                    
                    logger.info(f"Confidence: {confidence}")
                    logger.info(f"Response: {result.get('response', 'No response')[:100]}...")
                    logger.info("-" * 50)
                
            except asyncio.TimeoutError:
                logger.error(f"Request timed out for message: {message}")
            except Exception as e:
                logger.error(f"Error during test: {str(e)}")
            
            # Add a delay between requests
            await asyncio.sleep(2)
    
    logger.info("Agent routing test completed")

if __name__ == "__main__":
    asyncio.run(test_agents())