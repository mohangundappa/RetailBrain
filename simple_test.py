#!/usr/bin/env python3
"""
Simple script to test the Staples Brain API functionality with a single message.
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
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"

# Test message for Reset Password Agent
TEST_MESSAGE = "I forgot my password and need to reset it. Can you help me reset my Staples password?"
SESSION_ID = "test-reset-password-session"

async def main():
    """Send a single message to test the brain API."""
    logger.info(f"Testing with message: {TEST_MESSAGE}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Prepare the payload
            payload = {
                "message": TEST_MESSAGE,
                "session_id": SESSION_ID
            }
            
            # Send the request
            logger.info("Sending request...")
            async with session.post(CHAT_ENDPOINT, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Response received:")
                    logger.info(f"Success: {data.get('success', False)}")
                    logger.info(f"Conversation ID: {data.get('conversation_id', 'unknown')}")
                    
                    response_data = data.get('response', {})
                    if isinstance(response_data, dict):
                        logger.info(f"Response message: {response_data.get('message', 'No message')}")
                    else:
                        logger.info(f"Response: {response_data}")
                else:
                    text = await response.text()
                    logger.error(f"API error {response.status}: {text}")
        
        except asyncio.TimeoutError:
            logger.error("Request timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())