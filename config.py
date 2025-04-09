import os

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
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
