"""
Configuration package for Staples Brain.
"""
from backend.config.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig, get_config

__all__ = ['Config', 'DevelopmentConfig', 'TestingConfig', 'ProductionConfig', 'get_config']