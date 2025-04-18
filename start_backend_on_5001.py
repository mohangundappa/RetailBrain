#!/usr/bin/env python
"""
Start the backend on port 5001.
This script explicitly overrides any port configuration and ensures the backend runs on port 5001.
"""
import os
import sys
import importlib
import logging
import uvicorn

# Explicitly set API port
os.environ["API_PORT"] = "5001"

# Write the port to a file for frontend to reference
with open("backend_port.txt", "w") as f:
    f.write("5001")

print(f"Starting backend on port 5001...")

# Import the app directly rather than using subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app

# Run the main application directly with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)