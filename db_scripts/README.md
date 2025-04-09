# Staples Brain Database Scripts

This directory contains SQL scripts and utilities for setting up, managing, and maintaining the Staples Brain database.

## Available Scripts

### Database Setup

- **setup_database.sql**: Creates the database, user, and grants necessary privileges
  ```bash
  # Execute as postgres superuser
  psql -U postgres -f setup_database.sql
  ```

- **create_tables.sql**: Creates all required tables for the application
  ```bash
  # Execute after connecting to the database
  psql -U staples_user -d staples_brain -f create_tables.sql
  ```

### Sample Data

- **sample_data.sql**: Inserts basic sample data for testing
  ```bash
  # Execute after creating tables
  psql -U staples_user -d staples_brain -f sample_data.sql
  ```

- **generate_test_data.py**: Python script to generate larger amounts of test data
  ```bash
  # Generate 20 conversations with related data
  ./generate_test_data.py
  
  # Generate a custom number of conversations
  ./generate_test_data.py --count 50
  
  # Use a custom database URL
  ./generate_test_data.py --database-url postgresql://user:pass@localhost/dbname
  ```

### Maintenance

- **maintenance.sql**: Contains queries for database maintenance and optimization
  ```bash
  # Execute for maintenance operations
  psql -U staples_user -d staples_brain -f maintenance.sql
  ```

- **backup_restore.sh**: Bash script for backing up and restoring the database
  ```bash
  # Create a backup
  ./backup_restore.sh backup
  
  # List available backups
  ./backup_restore.sh list
  
  # Restore from a backup file
  ./backup_restore.sh restore ./db_backups/staples_brain_20250409_123456.dump
  ```

## Common Tasks

### First-Time Setup

1. Create the database and user:
   ```bash
   psql -U postgres -f setup_database.sql
   ```

2. Create tables:
   ```bash
   psql -U staples_user -d staples_brain -f create_tables.sql
   ```

3. (Optional) Add sample data:
   ```bash
   psql -U staples_user -d staples_brain -f sample_data.sql
   ```

### Regular Maintenance

1. Clean up old data and optimize:
   ```bash
   psql -U staples_user -d staples_brain -f maintenance.sql
   ```

2. Create regular backups:
   ```bash
   ./backup_restore.sh backup
   ```

## Notes

- These scripts are designed to work with PostgreSQL 13 or later
- Always ensure you have proper backups before performing maintenance operations
- The test data generation script requires Python 3.8+ and SQLAlchemy

For more detailed documentation, refer to the Setup Guide in the main application.