#!/usr/bin/env python
"""
A simple runner script for starting the Staples Brain API with uvicorn.
This script is designed to be used by the Replit workflow.
"""
import os
import sys
import logging
import subprocess

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger("staples_brain_runner")
logger.info("Starting Staples Brain API runner script")

# Configuration
host = "0.0.0.0"
port = 5000
app_module = "main:app"

logger.info(f"Starting uvicorn with app={app_module}, host={host}, port={port}")

# Construct the command
cmd = [
    sys.executable, "-m", "uvicorn", 
    app_module, 
    "--host", host, 
    "--port", str(port),
    "--reload"
]

# Execute uvicorn directly
try:
    logger.info(f"Executing command: {' '.join(cmd)}")
    # We use subprocess.run() with check=True to raise an exception on error
    process = subprocess.run(cmd, check=True)
    logger.info(f"Process exited with code {process.returncode}")
except Exception as e:
    logger.error(f"Error starting uvicorn: {str(e)}", exc_info=True)
    sys.exit(1)