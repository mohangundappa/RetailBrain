"""
Configuration module for Staples Brain application.
This module handles loading configuration for different environments.
"""
import os
import importlib
from pathlib import Path
from dataclasses import dataclass

# Agent Service Endpoints
PACKAGE_TRACKING_ENDPOINT = os.environ.get("PACKAGE_TRACKING_ENDPOINT", "https://api.staples.com/tracking/v1")
STORE_LOCATOR_ENDPOINT = os.environ.get("STORE_LOCATOR_ENDPOINT", "https://api.staples.com/stores/v1")
PRODUCT_INFO_ENDPOINT = os.environ.get("PRODUCT_INFO_ENDPOINT", "https://api.staples.com/products/v1")
PASSWORD_RESET_ENDPOINT = os.environ.get("PASSWORD_RESET_ENDPOINT", "https://api.staples.com/accounts/v1/reset")

@dataclass
class Config:
    """Base configuration class with common settings."""
    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = None
    LOG_LEVEL: str = "INFO"
    METRICS_ENABLED: bool = True
    LANGSMITH_ENABLED: bool = True
    DATABRICKS_ENABLED: bool = False
    
    # Agent Service Endpoints
    PACKAGE_TRACKING_ENDPOINT: str = PACKAGE_TRACKING_ENDPOINT
    STORE_LOCATOR_ENDPOINT: str = STORE_LOCATOR_ENDPOINT
    PRODUCT_INFO_ENDPOINT: str = PRODUCT_INFO_ENDPOINT
    PASSWORD_RESET_ENDPOINT: str = PASSWORD_RESET_ENDPOINT
    
    # Set up application start time for uptime calculations
    START_TIME: float = None
    
    def __post_init__(self):
        import time
        self.START_TIME = time.time()
        
        if self.SQLALCHEMY_ENGINE_OPTIONS is None:
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
class QAConfig(Config):
    """QA configuration."""
    LOG_LEVEL: str = "INFO"
    
class StagingConfig(Config):
    """Pre-production/staging configuration."""
    LOG_LEVEL: str = "INFO"
    
class ProductionConfig(Config):
    """Production configuration."""
    LOG_LEVEL: str = "WARNING"
    # In production, we require proper secret key
    SECRET_KEY: str = os.environ.get("SECRET_KEY")
    
# Configuration dictionary mapping
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "qa": QAConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}

def get_config():
    """
    Get the configuration based on the environment.
    Returns the appropriate configuration class based on FLASK_ENV or APP_ENV.
    """
    env = os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or "development"
    config_class = config_by_name.get(env.lower(), DevelopmentConfig)
    return config_class()