"""
Script to update the database schema.
This script adds the entity_definitions column to the custom_agents table.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    # Import from app
    from app import db, app

    # Run within the application context
    with app.app_context():
        # Execute the SQL query to add the missing column if it doesn't exist
        db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='custom_agents' AND column_name='entity_definitions'
            ) THEN
                ALTER TABLE custom_agents ADD COLUMN entity_definitions TEXT;
            END IF;
        END $$;
        """))
        
        # Commit the changes
        db.session.commit()
        
        print("Added entity_definitions column to custom_agents table successfully!")
        
except Exception as e:
    print(f"Error updating database schema: {e}")