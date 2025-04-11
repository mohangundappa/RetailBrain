"""
Route definitions for Staples Brain application.
Centralizes all routes in one location.
"""
import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, abort
import prometheus_client

from backend.brain.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

def register_routes(app):
    """
    Register all application routes.
    
    Args:
        app: Flask application instance
    """
    # Initialize the orchestrator
    orchestrator = Orchestrator()
    
    @app.route('/')
    def index():
        """Render the main page with application statistics."""
        # Get basic stats for dashboard
        stats = {
            'total_conversations': 1254,
            'active_agents': 5,
            'avg_response_time': 1.7,
            'user_satisfaction': 94.2
        }
        return render_template('index.html', stats=stats)
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        status = {
            'status': 'healthy',
            'db_healthy': db_is_healthy(),
            'llm_healthy': llm_is_healthy(),
            'timestamp': prometheus_client.utils.floatToGoString(
                prometheus_client.utils.time.time())
        }
        return jsonify(status)
    
    @app.route('/api/agents')
    def list_agents():
        """List all available agents."""
        agents = orchestrator.list_available_agents()
        return jsonify({'success': True, 'agents': agents})
    
    @app.route('/api/conversations')
    def list_conversations():
        """List all conversations."""
        # This would normally come from a database
        conversations = [
            {
                'id': '123456',
                'user_input': 'Where is my package?',
                'intent': 'package_tracking',
                'selected_agent': 'package_tracking',
                'created_at': '2025-04-09T12:34:56Z'
            },
            {
                'id': '234567',
                'user_input': 'I need to reset my password',
                'intent': 'password_reset',
                'selected_agent': 'password_reset',
                'created_at': '2025-04-09T13:45:12Z'
            }
        ]
        return jsonify({'success': True, 'conversations': conversations})
    
    @app.route('/api/conversations/<conversation_id>')
    def get_conversation(conversation_id):
        """Get a specific conversation with all its messages and related data."""
        # This would normally come from a database
        conversation = {
            'id': conversation_id,
            'user_id': 'user-123',
            'created_at': '2025-04-09T12:34:56Z',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Where is my package?',
                    'timestamp': '2025-04-09T12:34:56Z'
                },
                {
                    'role': 'assistant',
                    'content': 'I can help you track your package. Can you provide the tracking number?',
                    'timestamp': '2025-04-09T12:34:59Z',
                    'agent': 'package_tracking'
                }
            ],
            'metadata': {
                'intent': 'package_tracking',
                'confidence': 0.95,
                'selected_agent': 'package_tracking'
            }
        }
        return jsonify({'success': True, 'conversation': conversation})
    
    @app.route('/api/chat', methods=['POST'])
    def process_request():
        """Process a user request with LLM-based intent identification."""
        # Get request data
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', '')
        
        # Process the message through the orchestrator
        try:
            # Get response from orchestrator
            response = orchestrator.process_message(user_message, session_id)
            return jsonify(response)
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return jsonify({
                'success': False, 
                'response': 'Sorry, I encountered an error processing your request.',
                'error': str(e)
            })
    
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
    
    @app.route('/api/dashboard/metrics')
    def dashboard_metrics():
        """Provide metrics for the dashboard."""
        # This would normally come from a database or monitoring system
        metrics_data = {
            'daily_conversations': [45, 52, 48, 65, 72, 58, 63],
            'response_times': [1.2, 1.5, 1.8, 1.6, 1.9, 1.7, 1.5],
            'agent_usage': {
                'package_tracking': 35,
                'reset_password': 25,
                'store_locator': 20,
                'product_info': 15,
                'returns': 5
            },
            'user_satisfaction': [92, 94, 91, 95, 93, 96, 94]
        }
        return jsonify({'success': True, 'metrics': metrics_data})
    
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

def db_is_healthy():
    """Check if the database connection is healthy."""
    try:
        # Normally we would do a simple query here
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def llm_is_healthy():
    """Check if the LLM service is healthy."""
    try:
        # Normally we would do a simple LLM query here
        return True
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return False