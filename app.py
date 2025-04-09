import os
import logging
from flask import Flask
from config import get_config
from werkzeug.middleware.proxy_fix import ProxyFix
from db import db

def create_app(config_override=None):
    """
    Application factory for creating the Flask app with the specified configuration.
    
    Args:
        config_override: Optional configuration that overrides environment-based config
        
    Returns:
        Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration based on environment
    config = config_override or get_config()
    app.config.from_object(config)
    
    # Configure logging
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.basicConfig(
        level=log_level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up the proxy fix to work behind reverse proxies in production
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize database
    db.init_app(app)
    
    # Import models
    import models
    
    # Register blueprints
    from api.routes import api_bp
    app.register_blueprint(api_bp)
    
    # Import and initialize Staples Brain
    from brain.staples_brain import initialize_staples_brain
    
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        # Initialize the brain
        app.staples_brain = initialize_staples_brain()
        app.logger.info("Staples Brain initialized successfully")
    
    # The default route is defined in main.py
    # We don't define it here to avoid conflicting route definitions
    
    return app

# Create app instance when this module is imported
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
