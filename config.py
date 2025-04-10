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
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")

# Databricks configuration
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
DATABRICKS_CLUSTER_ID = os.environ.get("DATABRICKS_CLUSTER_ID")

# Integration endpoints (for demonstration purposes)
PACKAGE_TRACKING_ENDPOINT = os.environ.get("PACKAGE_TRACKING_ENDPOINT", "https://api.staples.com/tracking")
PASSWORD_RESET_ENDPOINT = os.environ.get("PASSWORD_RESET_ENDPOINT", "https://api.staples.com/reset-password")

# Application settings
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
