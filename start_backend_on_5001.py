#!/usr/bin/env python
"""
Start the backend on port 5001.
This script explicitly overrides any port configuration and ensures the backend runs on port 5001.
"""
import os
import sys
import subprocess

# Explicitly set API port
os.environ["API_PORT"] = "5001"

# Write the port to a file for frontend to reference
with open("backend_port.txt", "w") as f:
    f.write("5001")

print(f"Starting backend on port 5001...")

# Run the main application
subprocess.run([sys.executable, "run.py"])