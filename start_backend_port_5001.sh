#!/bin/bash
# This script explicitly sets the backend API port to 5001 to avoid conflicts
export API_PORT=5001
echo "Starting backend server on port 5001"
python run.py