"""
Flask application module for Staples Brain.
This defines the Flask app and initializes necessary components.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Define the base model class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with this base
db = SQLAlchemy(model_class=Base)

def create_app(config_override=None):
    """
    Application factory for creating the Flask app with the specified configuration.
    
    Args:
        config_override: Optional configuration that overrides environment-based config
        
    Returns:
        Flask application instance
    """
    # Create the Flask application
    app = Flask(__name__)
    
    # Configure app from environment by default
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///staples_brain.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.secret_key = os.environ.get("SECRET_KEY", "dev-key-not-secure")
    
    # Apply any override configuration
    if config_override:
        app.config.update(config_override)
    
    # Initialize the database
    db.init_app(app)
    
    # Register blueprints 
    from api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

# Create the application instance
app = create_app()

# Create database tables when used as a script
if __name__ == '__main__':
    with app.app_context():
        # Import models here to avoid circular imports
        import models
        db.create_all()