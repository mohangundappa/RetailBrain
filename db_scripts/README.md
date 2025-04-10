# Staples Brain Database Scripts

This directory contains SQL scripts and utilities for managing the Staples Brain database.

## Enterprise Database Management

For real-world enterprise environments like Staples, databases are typically managed following established practices:

- **Enterprise Guidelines**: See [enterprise_setup.md](enterprise_setup.md) for the recommended approach to database management in production environments.

## Development Scripts

The following scripts are provided for **local development environments only**:

### Local Database Setup

- **setup_database.sql**: Creates a local development database, user, and grants necessary privileges
  ```bash
  # Set the environment and execute as postgres superuser
  # Development environment (default)
  export APP_ENV=development
  psql -U postgres -f setup_database.sql
  
  # Testing environment
  export APP_ENV=testing
  psql -U postgres -f setup_database.sql
  ```
  
  > **IMPORTANT**: This script is designed for local development only. For QA, staging, and production environments, database provisioning should be handled by database administrators according to organizational policy.

- **create_tables.sql**: Creates all required tables for the application
  ```bash
  # Execute after connecting to the database
  # Replace username and dbname with the values for your environment
  # For example, for the development environment:
  psql -U staples_dev -d staples_brain_dev -f create_tables.sql
  
  # For the production environment:
  psql -U staples_prod -d staples_brain_prod -f create_tables.sql
  ```

### Sample Data

- **sample_data.sql**: Inserts basic sample data for testing
  ```bash
  # Execute after creating tables, using appropriate user and database for your environment
  # For development:
  psql -U staples_dev -d staples_brain_dev -f sample_data.sql
  
  # For QA:
  psql -U staples_qa -d staples_brain_qa -f sample_data.sql
  ```

- **generate_test_data.py**: Python script to generate larger amounts of test data
  ```bash
  # Generate 20 conversations with related data (set env var for your environment)
  export APP_ENV=development
  ./generate_test_data.py
  
  # Generate a custom number of conversations
  ./generate_test_data.py --count 50
  
  # Use a custom database URL for your environment
  ./generate_test_data.py --database-url postgresql://staples_dev:dev_password@localhost/staples_brain_dev
  
  # For QA environment
  ./generate_test_data.py --database-url postgresql://staples_qa:qa_password@localhost/staples_brain_qa
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

### Schema Updates

- **update_schema.py**: Adds the wizard_completed column to the custom_agents table
  ```bash
  # Run the script to update the schema
  python db_scripts/update_schema.py
  ```

- **add_icon_field.py**: Adds the icon field to the custom_agents table
  ```bash
  # Run the script to add the icon field
  python db_scripts/add_icon_field.py
  ```

- **add_entity_definitions_column.py**: Adds the entity_definitions column to the custom_agents table
  ```bash
  # Run the script to add the entity_definitions column
  python db_scripts/add_entity_definitions_column.py
  ```

- **add_template_fields.py**: Adds additional fields to the agent_templates table
  ```bash
  # Run the script to add template fields
  python db_scripts/add_template_fields.py
  ```

## Common Tasks

### First-Time Setup

1. Choose your environment and create the database and user:
   ```bash
   # Set environment (development, qa, staging, or production)
   export APP_ENV=development
   
   # Create database for chosen environment
   psql -U postgres -f setup_database.sql
   ```

2. Create tables (use appropriate credentials for your environment):
   ```bash
   # For development
   psql -U staples_dev -d staples_brain_dev -f create_tables.sql
   
   # For production
   psql -U staples_prod -d staples_brain_prod -f create_tables.sql
   ```

3. (Optional) Add sample data (for non-production environments only):
   ```bash
   # For development
   psql -U staples_dev -d staples_brain_dev -f sample_data.sql
   
   # For QA
   psql -U staples_qa -d staples_brain_qa -f sample_data.sql
   ```

### Regular Maintenance

1. Clean up old data and optimize (use credentials for your environment):
   ```bash
   # For development
   psql -U staples_dev -d staples_brain_dev -f maintenance.sql
   
   # For production
   psql -U staples_prod -d staples_brain_prod -f maintenance.sql
   ```

2. Create regular backups (specify environment):
   ```bash
   # For development environment
   ./backup_restore.sh backup development
   
   # For production environment
   ./backup_restore.sh backup production
   ```

## Notes

- These scripts are designed to work with PostgreSQL 13 or later
- Always ensure you have proper backups before performing maintenance operations
- The test data generation script requires Python 3.8+ and SQLAlchemy

For more detailed documentation, refer to the Setup Guide in the main application.