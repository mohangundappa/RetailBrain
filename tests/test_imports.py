"""
Basic test to verify that all required imports are available.
This test should be run first to ensure the environment is correctly set up.
"""

import unittest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestImports(unittest.TestCase):
    """Tests for verifying all required imports are available."""
    
    def test_langchain_imports(self):
        """Test that all LangChain imports are available."""
        # Core langchain imports
        try:
            import langchain_core
            from langchain_core.language_models.chat_models import BaseChatModel
            from langchain_core.outputs import ChatResult, ChatGenerationChunk
            from langchain_core.messages import AIMessageChunk
            self.assertTrue(True, "LangChain Core imports successful")
        except ImportError as e:
            self.fail(f"LangChain Core import failed: {str(e)}")
        
        # Community langchain imports
        try:
            import langchain_community
            from langchain_community.chat_models import ChatOpenAI
            self.assertTrue(True, "LangChain Community imports successful")
        except ImportError as e:
            self.fail(f"LangChain Community import failed: {str(e)}")
            
        # OpenAI langchain imports
        try:
            import langchain_openai
            self.assertTrue(True, "LangChain OpenAI imports successful")
        except ImportError as e:
            self.fail(f"LangChain OpenAI import failed: {str(e)}")
    
    def test_flask_imports(self):
        """Test that all Flask imports are available."""
        try:
            import flask
            from flask import Flask, request, jsonify, render_template
            self.assertTrue(True, "Flask imports successful")
        except ImportError as e:
            self.fail(f"Flask import failed: {str(e)}")
        
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            self.assertTrue(True, "Werkzeug imports successful")
        except ImportError as e:
            self.fail(f"Werkzeug import failed: {str(e)}")
    
    def test_database_imports(self):
        """Test that all database imports are available."""
        try:
            import sqlalchemy
            from sqlalchemy.orm import DeclarativeBase
            self.assertTrue(True, "SQLAlchemy imports successful")
        except ImportError as e:
            self.fail(f"SQLAlchemy import failed: {str(e)}")
        
        try:
            import flask_sqlalchemy
            from flask_sqlalchemy import SQLAlchemy
            self.assertTrue(True, "Flask-SQLAlchemy imports successful")
        except ImportError as e:
            self.fail(f"Flask-SQLAlchemy import failed: {str(e)}")
    
    def test_prometheus_imports(self):
        """Test that Prometheus imports are available."""
        try:
            import prometheus_client
            self.assertTrue(True, "Prometheus Client imports successful")
        except ImportError as e:
            self.fail(f"Prometheus Client import failed: {str(e)}")
            
    def test_project_imports(self):
        """Test that project structure imports work."""
        try:
            from brain.staples_brain import initialize_staples_brain
            from config.agent_constants import (
                PACKAGE_TRACKING_AGENT,
                RESET_PASSWORD_AGENT,
                STORE_LOCATOR_AGENT,
                PRODUCT_INFO_AGENT
            )
            from utils.memory import ConversationMemory
            self.assertTrue(True, "Project imports successful")
        except ImportError as e:
            self.fail(f"Project import failed: {str(e)}")


if __name__ == '__main__':
    unittest.main()