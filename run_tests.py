#!/usr/bin/env python
"""
Test runner for Staples Brain application.
This script redirects to the main test runner in backend/scripts.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_runner_wrapper")

def main():
    """Redirect to the main test runner in backend/scripts"""
    logger.info("Starting test runner wrapper")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the backend tests script
    backend_test_script = os.path.join(current_dir, "backend", "scripts", "run_tests.py")
    
    if not os.path.exists(backend_test_script):
        logger.error(f"Backend test script not found: {backend_test_script}")
        return 1
    
    # Pass all arguments to the backend test script
    cmd_args = [sys.executable, backend_test_script] + sys.argv[1:]
    
    logger.info(f"Executing: {' '.join(cmd_args)}")
    
    # Execute the backend test script
    import subprocess
    result = subprocess.run(cmd_args)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())