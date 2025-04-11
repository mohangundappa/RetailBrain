"""
Main application module for Staples Brain.
This module provides a Flask compatibility layer for the FastAPI backend.
"""
import os
import logging
from flask import Flask, request, jsonify
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staples_brain")

# Create the Flask app
app = Flask(__name__)

# Internal FastAPI port
INTERNAL_API_PORT = 8000

# Create a proxy gateway that forwards all requests to the FastAPI backend
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    url = f"http://localhost:{INTERNAL_API_PORT}/{path}"
    method = request.method
    params = request.args
    data = request.get_data()
    headers = {key: value for key, value in request.headers if key != 'Host'}
    
    try:
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        elif method == 'POST':
            response = requests.post(url, data=data, params=params, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, data=data, params=params, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, headers=headers)
        elif method == 'PATCH':
            response = requests.patch(url, data=data, params=params, headers=headers)
        else:
            return jsonify({"error": "Method not allowed"}), 405
        
        return response.content, response.status_code, response.headers.items()
    except requests.RequestException as e:
        logger.error(f"Error proxying request: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error (proxy failure)",
            "details": str(e)
        }), 500

# Start the FastAPI server in a subprocess
def start_fastapi_server():
    import subprocess
    import sys
    
    logger.info("Starting FastAPI server...")
    cmd = [
        sys.executable, 
        "run_fastapi.py"
    ]
    
    # Replace the PORT environment variable to avoid conflicts
    env = os.environ.copy()
    env["PORT"] = str(INTERNAL_API_PORT)
    
    # Start the FastAPI server as a subprocess
    subprocess.Popen(cmd, env=env)
    logger.info(f"FastAPI server started on port {INTERNAL_API_PORT}")

if __name__ == "__main__":
    # Start the FastAPI server
    start_fastapi_server()
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000)
else:
    # When running with gunicorn, start the FastAPI server before handling requests
    start_fastapi_server()