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
CHAT_ENDPOINT = f"{API_BASE_URL}/optimized/chat"

# Test message
TEST_MESSAGE = "Hello, tell me about the Staples Brain system"
SESSION_ID = "test-simple-session"

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
                    logger.info(f"Agent: {data.get('agent', 'unknown')}")
                    logger.info(f"Confidence: {data.get('confidence', 0)}")
                    logger.info(f"Response: {data.get('response', 'No response')}")
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