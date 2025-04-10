"""
Configuration module for Staples Brain application.
This module handles loading configuration for different environments.
"""
import os
import logging
import time
from typing import Dict, Any

# Agent Service Endpoints
PACKAGE_TRACKING_ENDPOINT = os.environ.get("PACKAGE_TRACKING_ENDPOINT", "https://api.staples.com/tracking/v1")
STORE_LOCATOR_ENDPOINT = os.environ.get("STORE_LOCATOR_ENDPOINT", "https://api.staples.com/stores/v1")
PRODUCT_INFO_ENDPOINT = os.environ.get("PRODUCT_INFO_ENDPOINT", "https://api.staples.com/products/v1")
PASSWORD_RESET_ENDPOINT = os.environ.get("PASSWORD_RESET_ENDPOINT", "http://localhost:5000/api/mock/reset-password")

# Base configuration class with common settings
class Config:
    """Base configuration class with common settings."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    LOG_LEVEL = "INFO"
    METRICS_ENABLED = True
    LANGSMITH_ENABLED = True
    DATABRICKS_ENABLED = False
    
    # Agent Service Endpoints
    PACKAGE_TRACKING_ENDPOINT = PACKAGE_TRACKING_ENDPOINT
    STORE_LOCATOR_ENDPOINT = STORE_LOCATOR_ENDPOINT
    PRODUCT_INFO_ENDPOINT = PRODUCT_INFO_ENDPOINT
    PASSWORD_RESET_ENDPOINT = PASSWORD_RESET_ENDPOINT
    
    # LLM model settings
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
    LLM_TEMPERATURE = 0.7
    
    # Set up application start time for uptime calculations
    START_TIME = time.time()

# Development configuration for local laptop development
class DevelopmentConfig(Config):
    """Development configuration for local laptop development."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    METRICS_ENABLED = False  # Typically not needed for local dev
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-3.5-turbo")
    LLM_TEMPERATURE = 0.7

# Testing configuration for automated tests
class TestingConfig(Config):
    """Testing configuration for automated tests."""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    # Test database would typically be different
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", os.environ.get("DATABASE_URL", ""))

# QA configuration for quality assurance environment
class QAConfig(Config):
    """QA configuration for quality assurance environment."""
    LOG_LEVEL = "INFO"
    DEBUG = False
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
    LLM_TEMPERATURE = 0.8
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20
    }

# Pre-production/staging configuration mirroring production settings
class StagingConfig(Config):
    """Pre-production/staging configuration mirroring production settings."""
    LOG_LEVEL = "INFO"
    DEBUG = False
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
    LLM_TEMPERATURE = 0.7
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 40
    }

# Production configuration optimized for reliability and performance
class ProductionConfig(Config):
    """Production configuration optimized for reliability and performance."""
    LOG_LEVEL = "WARNING"
    DEBUG = False
    LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "gpt-4o")
    LLM_TEMPERATURE = 0.2  # Lower temperature for consistent responses
    
    # In production, check if secret key is set
    if not os.environ.get("SECRET_KEY"):
        logging.warning("SECRET_KEY environment variable not set in production. Using default value, which is insecure.")
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 30,
        "max_overflow": 60,
        "pool_timeout": 30
    }

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
    return config_class