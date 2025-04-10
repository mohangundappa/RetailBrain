"""
Script to add new fields to the agent_templates table.
"""
import os
import sys

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import Column, String, Boolean, Integer, Float, Text

def update_agent_templates_schema():
    """Update the agent_templates table schema with new fields."""
    with app.app_context():
        conn = db.engine.connect()
        inspector = db.inspect(db.engine)
        
        table_name = 'agent_templates'
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        # Add tags column if it doesn't exist
        if 'tags' not in columns:
            print("Adding 'tags' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN tags TEXT"))
        
        # Add is_featured column if it doesn't exist
        if 'is_featured' not in columns:
            print("Adding 'is_featured' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN is_featured BOOLEAN DEFAULT FALSE"))
        
        # Add downloads column if it doesn't exist
        if 'downloads' not in columns:
            print("Adding 'downloads' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN downloads INTEGER DEFAULT 0"))
        
        # Add rating column if it doesn't exist
        if 'rating' not in columns:
            print("Adding 'rating' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN rating FLOAT DEFAULT 0.0"))
        
        # Add rating_count column if it doesn't exist
        if 'rating_count' not in columns:
            print("Adding 'rating_count' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN rating_count INTEGER DEFAULT 0"))
        
        # Add screenshot column if it doesn't exist
        if 'screenshot' not in columns:
            print("Adding 'screenshot' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN screenshot VARCHAR(255)"))
            
        # Add author column if it doesn't exist
        if 'author' not in columns:
            print("Adding 'author' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN author VARCHAR(100)"))
            
        # Add author_email column if it doesn't exist
        if 'author_email' not in columns:
            print("Adding 'author_email' column to agent_templates table...")
            conn.execute(db.text("ALTER TABLE agent_templates ADD COLUMN author_email VARCHAR(100)"))
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        print("Schema update completed successfully.")

if __name__ == "__main__":
    update_agent_templates_schema()