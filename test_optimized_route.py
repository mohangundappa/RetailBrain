"""
Test script to compare the original and optimized agent selection for a password reset request.
"""
import json
import os
import time
import uuid
import requests

# Base URL for API
BASE_URL = "http://localhost:8000/api/v1"
ORIGINAL_CHAT_URL = f"{BASE_URL}/chat"
OPTIMIZED_CHAT_URL = f"{BASE_URL}/optimized/chat"

# Generate a unique session ID
session_id = str(uuid.uuid4())
print(f"Using session ID: {session_id}")

# Password reset query
query = "I forgot my password and need to reset it"

def test_original_route():
    """Test the original chat route."""
    print("\n=== Testing Original Route ===")
    start_time = time.time()
    
    payload = {
        "message": query,
        "session_id": session_id
    }
    
    try:
        response = requests.post(ORIGINAL_CHAT_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract relevant information
        success = result.get("success", False)
        agent_name = result.get("agent_name")
        confidence = result.get("confidence")
        response_text = result.get("response", "")
        
        # Print results
        print(f"Success: {success}")
        print(f"Selected Agent: {agent_name}")
        print(f"Confidence: {confidence}")
        print(f"Response: {response_text[:100]}..." if len(response_text) > 100 else f"Response: {response_text}")
        print(f"Time taken: {time.time() - start_time:.2f} seconds")
        
        return result
    except Exception as e:
        print(f"Error testing original route: {str(e)}")
        return None

def test_optimized_route():
    """Test the optimized chat route."""
    print("\n=== Testing Optimized Route ===")
    start_time = time.time()
    
    payload = {
        "message": query,
        "session_id": session_id
    }
    
    try:
        response = requests.post(OPTIMIZED_CHAT_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract relevant information
        success = result.get("success", False)
        agent_name = result.get("agent")
        confidence = result.get("confidence")
        response_text = result.get("response", "")
        metadata = result.get("metadata", {})
        selection_time = metadata.get("selection_time", 0) if metadata else 0
        
        # Print results
        print(f"Success: {success}")
        print(f"Selected Agent: {agent_name}")
        print(f"Confidence: {confidence}")
        print(f"Response: {response_text[:100]}..." if len(response_text) > 100 else f"Response: {response_text}")
        print(f"Selection time: {selection_time:.2f} seconds")
        print(f"Total time: {time.time() - start_time:.2f} seconds")
        
        return result
    except Exception as e:
        print(f"Error testing optimized route: {str(e)}")
        return None

def compare_results(original_result, optimized_result):
    """Compare the results from both routes."""
    if not original_result or not optimized_result:
        print("\n=== Comparison Failed: Missing Results ===")
        return
        
    print("\n=== Comparison of Results ===")
    
    # Compare selected agents
    original_agent = original_result.get("agent_name")
    optimized_agent = optimized_result.get("agent")
    print(f"Agent Selection Match: {original_agent == optimized_agent}")
    
    # Compare responses (first 50 chars)
    original_response = original_result.get("response", "")[:50]
    optimized_response = optimized_result.get("response", "")[:50]
    response_similar = original_response.lower() in optimized_response.lower() or optimized_response.lower() in original_response.lower()
    print(f"Response Similarity: {response_similar}")
    
    # Compare execution times
    original_metadata = original_result.get("metadata", {})
    optimized_metadata = optimized_result.get("metadata", {})
    
    if original_metadata and optimized_metadata:
        original_time = original_metadata.get("execution_time", 0)
        optimized_time = optimized_metadata.get("execution_time", 0)
        optimized_selection = optimized_metadata.get("selection_time", 0)
        
        print(f"Original execution time: {original_time:.2f} seconds")
        print(f"Optimized execution time: {optimized_time:.2f} seconds")
        print(f"Optimized selection time: {optimized_selection:.2f} seconds")
        
        if original_time > 0 and optimized_time > 0:
            improvement = (original_time - optimized_time) / original_time * 100
            print(f"Performance improvement: {improvement:.2f}%")

def execute_curl_commands():
    """Execute and display curl commands for manual testing."""
    print("\n=== Curl Commands for Manual Testing ===")
    
    original_curl = f"""
    curl -X POST {ORIGINAL_CHAT_URL} \\
         -H "Content-Type: application/json" \\
         -d '{{"message": "{query}", "session_id": "{session_id}"}}'
    """
    
    optimized_curl = f"""
    curl -X POST {OPTIMIZED_CHAT_URL} \\
         -H "Content-Type: application/json" \\
         -d '{{"message": "{query}", "session_id": "{session_id}"}}'
    """
    
    print("Original Chat API:")
    print(original_curl)
    print("\nOptimized Chat API:")
    print(optimized_curl)

if __name__ == "__main__":
    # Test both routes
    original_result = test_original_route()
    optimized_result = test_optimized_route()
    
    # Compare results
    compare_results(original_result, optimized_result)
    
    # Show curl commands
    execute_curl_commands()