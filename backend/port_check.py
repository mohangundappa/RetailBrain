"""
Script to check port configuration and ensure proper binding.
"""
import os
import sys

# This script ensures we're using the correct port configuration
port = os.environ.get("API_PORT", "5001")
print(f"API_PORT environment variable: {port}")

# Write the port to the backend_port.txt file for reference
with open("backend_port.txt", "w") as f:
    f.write(port)
    
print(f"Updated backend_port.txt with port {port}")