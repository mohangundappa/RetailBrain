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
    # Create and configure the Flask app
    app = Flask(__name__)
    
    # Use ProxyFix to handle proxy headers properly (for URL generation with https)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Set up configuration
    app_env = os.environ.get("APP_ENV", "development")
    
    # Basic configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-not-secure")
    if app_env == "production" and app.config["SECRET_KEY"] == "dev-key-not-secure":
        logger.warning("SECRET_KEY environment variable not set in production. Using default value, which is insecure.")
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Apply any override configurations
    if config_override:
        app.config.update(config_override)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    with app.app_context():
        # Import blueprints - do this here to avoid circular imports
        from api.routes import api_bp
        
        # Register blueprints
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # Create database tables
        db.create_all()
        
        # Set application start time (for uptime calculation)
        app.config["START_TIME"] = time.time()
        
        # Initialize Staples Brain (will be used by routes)
        from brain.staples_brain import initialize_staples_brain
        app.staples_brain = initialize_staples_brain()
        
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    # Run the app directly when script is executed
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)