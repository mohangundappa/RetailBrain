"""
Test script to verify API endpoints are accessible.
"""
import requests
import json
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_test")

# API URL
API_BASE_URL = "http://localhost:5000/api/v1"

def test_health_endpoint():
    """Test the health endpoint."""
    try:
        url = f"{API_BASE_URL}/health"
        logger.info(f"Testing health endpoint: {url}")
        
        response = requests.get(url)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("Health check successful")
            return True
        else:
            logger.error("Health check failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during health check: {str(e)}")
        return False
        
def test_agents_endpoint():
    """Test the agents endpoint."""
    try:
        url = f"{API_BASE_URL}/agents"
        logger.info(f"Testing agents endpoint: {url}")
        
        response = requests.get(url)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("Agents endpoint check successful")
            return True
        else:
            logger.error("Agents endpoint check failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during agents endpoint check: {str(e)}")
        return False

def test_telemetry_endpoint():
    """Test the telemetry endpoint."""
    try:
        url = f"{API_BASE_URL}/telemetry/sessions"
        logger.info(f"Testing telemetry endpoint: {url}")
        
        response = requests.get(url)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("Telemetry endpoint check successful")
            return True
        else:
            logger.error("Telemetry endpoint check failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during telemetry endpoint check: {str(e)}")
        return False
        
if __name__ == "__main__":
    logger.info("Starting API tests")
    
    # Add a small delay to ensure server is up
    time.sleep(2)
    
    # Test health endpoint
    health_result = test_health_endpoint()
    
    # Test agents endpoint
    agents_result = test_agents_endpoint()
    
    # Test telemetry endpoint
    telemetry_result = test_telemetry_endpoint()
    
    # Overall result
    overall_result = health_result and agents_result and telemetry_result
    
    if overall_result:
        logger.info("All API tests passed")
    else:
        logger.error("Some API tests failed")
        
    logger.info("API tests completed")