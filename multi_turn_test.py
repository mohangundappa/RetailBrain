#!/usr/bin/env python3
"""
Script to test the Staples Brain API functionality with multiple turns in a conversation.
This supports testing workflows like Reset Password that require multiple interactions.
"""

import sys
import json
import aiohttp
import asyncio
import logging
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("multi_turn_tester")

# API endpoint
API_BASE_URL = "http://localhost:5000/api/v1"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"

# Generate a unique session ID
SESSION_ID = f"test-session-{uuid.uuid4()}"

async def send_message(session, message: str, session_id: str):
    """Send a message to the brain API and return the response."""
    try:
        # Prepare the payload
        payload = {
            "message": message,
            "session_id": session_id
        }
        
        # Send the request
        logger.info(f"Sending message: '{message}'")
        async with session.post(CHAT_ENDPOINT, json=payload, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"Success: {data.get('success', False)}")
                
                response_data = data.get('response', {})
                if isinstance(response_data, dict):
                    response_message = response_data.get('message', 'No message')
                else:
                    response_message = response_data
                
                logger.info(f"Response: {response_message}")
                return response_message
            else:
                text = await response.text()
                logger.error(f"API error {response.status}: {text}")
                return None
    
    except asyncio.TimeoutError:
        logger.error("Request timed out after 30 seconds")
        return None
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None

async def test_reset_password_flow():
    """Test the Reset Password workflow with multiple turns."""
    logger.info(f"Starting multi-turn test with session ID: {SESSION_ID}")
    
    async with aiohttp.ClientSession() as session:
        # Start with a reset password request
        response1 = await send_message(
            session, 
            "I forgot my password and need to reset it", 
            SESSION_ID
        )
        
        # Wait for a moment to simulate user think time
        await asyncio.sleep(1)
        
        # Provide an email address in response to the expected request
        if response1 and "email" in response1.lower():
            response2 = await send_message(
                session,
                "My email is test@example.com",
                SESSION_ID
            )
            
            # Wait for a moment
            await asyncio.sleep(1)
            
            # Confirm the reset if prompted
            if response2 and "reset" in response2.lower():
                await send_message(
                    session,
                    "Yes, please reset my password",
                    SESSION_ID
                )
        
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_reset_password_flow())