import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logger(name=None, log_level=None):
    """
    Configure logging for the application.
    
    Args:
        name: Logger name (defaults to root logger if None)
        log_level: Logging level (defaults to environment variable or DEBUG)
        
    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    
    numeric_level = getattr(logging, log_level, logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    logger.handlers = []  # Clear existing handlers
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"Could not create log directory: {e}")
    
    if os.path.exists(log_dir):
        log_file = os.path.join(log_dir, "staples_brain.log")
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=10485760, backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Could not set up file logging: {e}")
    
    return logger

def get_logger(name):
    """
    Get a logger with the specified name.
    
    Args:
        name: Name for the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
