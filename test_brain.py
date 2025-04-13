#!/usr/bin/env python3
"""
Script to test the Staples Brain API functionality.
This script tests the brain's response to different types of queries.
"""

import sys
import json
import asyncio
import aiohttp
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("brain_tester")

# API endpoint
API_BASE_URL = "http://localhost:5000/api/v1"
CHAT_ENDPOINT = f"{API_BASE_URL}/optimized/chat"

# Test messages to send
TEST_MESSAGES = [
    "Hello, how can you help me today?",
    "I need to reset my password for my account",
    "Can you help me track my order?",
    "Where is the nearest Staples store?",
    "Tell me about office chairs",
    "I want to return a printer I bought"
]

async def send_message(session, message, session_id):
    """Send a message to the brain API."""
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    logger.info(f"Sending message: {message}")
    
    try:
        async with session.post(CHAT_ENDPOINT, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logger.error(f"API error: {response.status}")
                text = await response.text()
                logger.error(f"Response text: {text}")
                return None
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

async def test_brain():
    """Run a series of tests against the brain API."""
    # Generate a unique session ID for this test run
    session_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    logger.info(f"Starting brain test with session_id: {session_id}")
    
    async with aiohttp.ClientSession() as session:
        for i, message in enumerate(TEST_MESSAGES, 1):
            logger.info(f"*** TEST {i}/{len(TEST_MESSAGES)} ***")
            try:
                # Set a timeout for the request to avoid hanging
                result = await asyncio.wait_for(
                    send_message(session, message, session_id),
                    timeout=15  # 15 seconds timeout
                )
                
                if result:
                    # Get the full response
                    response_text = result.get('response', 'No response')
                    logger.info(f"Response from {result.get('agent', 'unknown')}:")
                    logger.info(f"{response_text}")
                    logger.info(f"Confidence: {result.get('confidence', 0)}")
                    logger.info("-" * 50)
                
            except asyncio.TimeoutError:
                logger.error(f"Request timed out for message: {message}")
            except Exception as e:
                logger.error(f"Error during test: {str(e)}")
            
            # Add a delay between requests to avoid rate limiting
            await asyncio.sleep(2)
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_brain())