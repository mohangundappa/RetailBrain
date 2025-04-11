"""
Flask application module for Staples Brain.
This defines the Flask app and initializes necessary components.
"""
import os
import time
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass

# Initialize SQLAlchemy with our Base class
db = SQLAlchemy(model_class=Base)

def create_app(config_override=None):
    """
    Application factory for creating the Flask app with the specified configuration.
    
    Args:
        config_override: Optional configuration that overrides environment-based config
        
    Returns:
        Flask application instance
    """
    # Create and configure the app
    app = Flask(__name__, 
                static_folder="../static", 
                template_folder="../templates")
    
    # Apply WSGI middleware for proper proxy handling
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Load configuration based on environment
    if config_override is None:
        # Default to loading environment-based config
        from backend.config import get_config
        config_class = get_config()
        app.config.from_object(config_class)
    else:
        # Use provided configuration override
        app.config.from_object(config_override)
    
    # Configure secret key
    app.secret_key = app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY', 'dev-key')
    
    # Initialize extensions
    db.init_app(app)
    
    # Register routes
    with app.app_context():
        # Import routes
        from backend.routes import register_routes
        register_routes(app)
        
        # Create database tables
        db.create_all()
        
        # Record application startup
        logger.info("Application initialized successfully.")
    
    return app