"""
Main application module for Staples Brain.
This is the entry point for the Flask application.
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("staples_brain.log")
    ]
)

logger = logging.getLogger("staples_brain")

# Load environment variables
from dotenv import load_dotenv
print(f"Loading environment from {os.path.abspath('.env')}")
load_dotenv()

# Import Flask and other dependencies
from flask import Flask, render_template, jsonify, request, redirect, url_for, abort
import prometheus_client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Import the database
from db import db

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-not-secure")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Set up metrics
PROCESSING_TIME = prometheus_client.Summary(
    'request_processing_seconds', 'Time spent processing request'
)

@app.route('/')
def index():
    """Render the main page with application statistics."""
    stats = {
        "database_connected": db_is_healthy()["status"] == "healthy",
        "openai_api_configured": llm_is_healthy()["status"] == "healthy",
        "total_conversations": 0,
        "total_messages": 0,
        "agent_distribution": {},
        "avg_response_time": 0
    }
    return render_template('index.html', stats=stats)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": db_is_healthy(),
            "llm": llm_is_healthy()
        }
    }
    return jsonify(health_status)

def db_is_healthy():
    """Check if the database connection is healthy."""
    try:
        # Use SQLAlchemy to execute a simple query
        with db.engine.connect() as connection:
            result = connection.execute("SELECT 1").fetchone()
            is_connected = result is not None
        return {"status": "healthy" if is_connected else "unhealthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def llm_is_healthy():
    """Check if the LLM service is healthy."""
    try:
        # Check if OpenAI API key is configured
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"status": "unhealthy", "error": "API key not configured"}
        
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.route('/api/agents')
def list_agents():
    """List all available agents."""
    # This endpoint will redirect to the FastAPI endpoint
    return redirect("/api/v1/agents")

@app.route('/api/conversations')
def list_conversations():
    """List all conversations."""
    # This would typically connect to the database
    # For now, return a static response
    return jsonify({
        "success": True,
        "data": {
            "conversations": []
        }
    })

@app.route('/api/conversations/<conversation_id>')
def get_conversation(conversation_id):
    """Get a specific conversation with all its messages and related data."""
    # This would typically connect to the database
    # For now, return a static response
    return jsonify({
        "success": True,
        "data": {
            "conversation_id": conversation_id,
            "messages": []
        }
    })

@app.route('/api/process', methods=['POST'])
def process_request():
    """Process a user request with LLM-based intent identification."""
    # This endpoint will redirect to the FastAPI endpoint
    return redirect("/api/v1/chat/messages")

@app.route('/documentation')
def documentation():
    """Render the comprehensive user documentation."""
    return render_template('documentation.html')

@app.route('/architecture')
def architecture():
    """Render the architecture documentation with block diagrams."""
    return render_template('architecture.html')

@app.route('/dashboard')
def dashboard():
    """Render the observability dashboard."""
    return render_template('dashboard.html')

@app.route('/metrics')
def metrics():
    """Provide Prometheus metrics endpoint."""
    return prometheus_client.generate_latest()

@app.route('/dashboard/metrics')
def dashboard_metrics():
    """Provide metrics for the dashboard."""
    return jsonify({
        "success": True,
        "data": {
            "requests_per_minute": 0,
            "average_response_time": 0,
            "error_rate": 0,
            "agent_distribution": {}
        }
    })

@app.route('/agent-diagrams')
def agent_diagrams():
    """Show agent builder diagrams HTML page."""
    return render_template('agent_diagrams.html')

@app.route('/circuit-breaker')
def circuit_breaker_dashboard():
    """Show circuit breaker dashboard HTML page."""
    return render_template('circuit_breaker.html')

@app.route('/telemetry')
def telemetry_dashboard():
    """Show agent selection telemetry dashboard."""
    return render_template('telemetry.html')

@app.route('/chat-telemetry')
def chat_with_telemetry():
    """Show chat interface with real-time telemetry view side by side."""
    return render_template('chat_telemetry.html')

if __name__ == '__main__':
    # Run the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)