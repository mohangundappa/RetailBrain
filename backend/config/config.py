import os
import logging

# Configure logging for config module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: Environment variables are loaded from .env file in app.py
# using python-dotenv before this module is imported

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found. Make sure it's set in your .env file.")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# Databricks configuration
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
DATABRICKS_CLUSTER_ID = os.environ.get("DATABRICKS_CLUSTER_ID")

# Integration endpoints (for demonstration purposes)
PACKAGE_TRACKING_ENDPOINT = os.environ.get("PACKAGE_TRACKING_ENDPOINT", "https://api.staples.com/tracking")
PASSWORD_RESET_ENDPOINT = os.environ.get("PASSWORD_RESET_ENDPOINT", "https://api.staples.com/reset-password")

# Application settings
APP_ENV = os.environ.get("APP_ENV", "development")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")

# Define configuration classes for different environments
class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-not-secure'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'INFO'
    # In production, ensure SECRET_KEY is set in environment variables
    
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            logger.warning("SECRET_KEY environment variable not set in production. Using default value, which is insecure.")
            return super().SECRET_KEY
        return key

# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Return the appropriate configuration class based on the environment."""
    env = os.environ.get('APP_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])
