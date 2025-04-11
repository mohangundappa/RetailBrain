#!/usr/bin/env python
"""
Database script runner for Staples Brain

This script runs SQL scripts for database setup, updates, and data management.
It tracks script execution to prevent duplicate runs.

Usage:
    python run_scripts.py --type setup
    python run_scripts.py --type updates --version v1.0.0
    python run_scripts.py --type data
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database_scripts')

# Base directory for scripts
SCRIPT_BASE_DIR = Path(__file__).parent


def ensure_script_tracking_table(conn):
    """
    Ensure the script execution tracking table exists
    
    Args:
        conn: Database connection
    """
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS db_script_execution (
            script_name VARCHAR(255) PRIMARY KEY,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL
        );
        """)
    conn.commit()
    logger.info("Ensured script tracking table exists")


def script_already_executed(conn, script_name, version):
    """
    Check if a script has already been executed successfully
    
    Args:
        conn: Database connection
        script_name: Name of the script
        version: Version the script belongs to
        
    Returns:
        bool: True if already executed successfully, False otherwise
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM db_script_execution WHERE script_name = %s",
            (script_name,)
        )
        result = cur.fetchone()
        
    if result and result[0] == 'SUCCESS':
        return True
    return False


def record_script_execution(conn, script_name, version, status):
    """
    Record script execution in the tracking table
    
    Args:
        conn: Database connection
        script_name: Name of the script
        version: Version the script belongs to
        status: Execution status ('SUCCESS' or 'FAILED')
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO db_script_execution (script_name, version, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (script_name) 
            DO UPDATE SET executed_at = CURRENT_TIMESTAMP, version = %s, status = %s
            """,
            (script_name, version, status, version, status)
        )
    conn.commit()
    logger.info(f"Recorded execution of {script_name}: {status}")


def run_scripts(conn, directory, version):
    """
    Run all SQL scripts in a directory in order by filename
    
    Args:
        conn: Database connection
        directory: Directory containing SQL scripts
        version: Version these scripts belong to
    """
    if not os.path.exists(directory):
        logger.error(f"Directory does not exist: {directory}")
        return
        
    files = sorted([f for f in os.listdir(directory) if f.endswith('.sql')])
    
    if not files:
        logger.warning(f"No SQL scripts found in {directory}")
        return
        
    logger.info(f"Found {len(files)} scripts in {directory}")
    
    for file in files:
        script_path = os.path.join(directory, file)
        
        # Skip if already executed successfully
        if script_already_executed(conn, file, version):
            logger.info(f"Skipping {file} (already executed successfully)")
            continue
            
        logger.info(f"Running {file}...")
        
        try:
            with open(script_path, 'r') as f:
                sql = f.read()
                with conn.cursor() as cur:
                    cur.execute(sql)
            conn.commit()
            logger.info(f"Completed {file}")
            
            # Record successful execution
            record_script_execution(conn, file, version, 'SUCCESS')
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error executing {file}: {str(e)}")
            
            # Record failed execution
            record_script_execution(conn, file, version, 'FAILED')
            
            # Exit if a script fails
            sys.exit(1)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run database scripts')
    parser.add_argument(
        '--type', 
        choices=['setup', 'updates', 'data'],
        required=True,
        help='Type of scripts to run'
    )
    parser.add_argument(
        '--version', 
        help='Version directory to run scripts from (required for updates)'
    )
    parser.add_argument(
        '--db-url',
        help='Database URL (defaults to DATABASE_URL environment variable)'
    )
    
    args = parser.parse_args()
    
    # Check if version is provided for updates
    if args.type == 'updates' and not args.version:
        logger.error("--version is required when --type is 'updates'")
        sys.exit(1)
    
    # Use provided database URL or environment variable
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("Database URL not provided. Use --db-url or set DATABASE_URL environment variable")
        sys.exit(1)
    
    try:
        # Connect to database
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Ensure tracking table exists
        ensure_script_tracking_table(conn)
        
        # Run scripts based on type
        if args.type == 'setup':
            directory = SCRIPT_BASE_DIR / 'setup'
            logger.info(f"Running setup scripts from {directory}")
            run_scripts(conn, directory, 'setup')
            
        elif args.type == 'updates':
            directory = SCRIPT_BASE_DIR / 'updates' / args.version
            logger.info(f"Running update scripts for version {args.version} from {directory}")
            run_scripts(conn, directory, args.version)
            
        elif args.type == 'data':
            directory = SCRIPT_BASE_DIR / 'data'
            logger.info(f"Running data scripts from {directory}")
            run_scripts(conn, directory, 'data')
        
        logger.info(f"Completed running {args.type} scripts")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
        
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    main()