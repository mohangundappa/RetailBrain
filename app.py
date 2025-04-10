import os
import logging
from flask import Flask
from config import get_config
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from db import db

# Load environment variables from .env file
load_dotenv()

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
    config_class = config_override or get_config()
    app.config.from_object(config_class)
    
    # Set a secure secret key (prioritize environment variable)
    if not app.secret_key:
        env_secret_key = os.environ.get("SECRET_KEY")
        if env_secret_key:
            app.secret_key = env_secret_key
        else:
            # Generate a random secret key for development
            import secrets
            app.secret_key = secrets.token_hex(32)
            app.logger.warning(
                "SECRET_KEY environment variable not set. "
                "Using a randomly generated key, which will change with each restart. "
                "For persistent sessions, set SECRET_KEY in your .env file."
            )
    
    # Configure logging
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.basicConfig(
        level=log_level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up the proxy fix to work behind reverse proxies in production
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Check database configuration
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # For local development, provide a default SQLite database
        default_db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'staples_brain_dev.db')
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{default_db_path}"
        app.logger.warning(
            "DATABASE_URL not found in environment variables. "
            f"Using SQLite database at {default_db_path} instead. "
            "This is only suitable for development."
        )
    
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
