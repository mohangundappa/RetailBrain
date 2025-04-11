#!/usr/bin/env python
"""
Add icon field to CustomAgent table

This script adds an icon field to the CustomAgent table to support agent icon selection
in the agent builder interface.

Usage:
    python -m db_scripts.add_icon_field
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app import app, db

def add_icon_field():
    """Add the icon field to the CustomAgent table"""
    try:
        # Check if the field already exists
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='custom_agents' AND column_name='icon'"
            ))
            exists = bool(result.fetchone())
            
            if exists:
                print("Icon field already exists in custom_agents table.")
                return
            
            # Add the icon field with default value
            conn.execute(text(
                "ALTER TABLE custom_agents "
                "ADD COLUMN icon VARCHAR(100) DEFAULT 'fas fa-robot'"
            ))
            conn.commit()
            
            print("Successfully added icon field to custom_agents table.")
    except Exception as e:
        print(f"Error adding icon field: {e}")
        raise


if __name__ == "__main__":
    with app.app_context():
        add_icon_field()
        print("Migration completed successfully.")