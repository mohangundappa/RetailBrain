# Staples Brain Database Scripts

This directory contains SQL scripts and utilities for managing the Staples Brain database.

## Directory Structure

- `setup/` - One-time database setup scripts
  - `001_create_script_tracker.sql` - Creates tracking table for script execution
  - `create_database.sql` - Creates the database and user
  - `create_tables.sql` - Creates all required tables

- `updates/` - Version-specific update scripts
  - `v1.0.0/` - Scripts for version 1.0.0
    - `001_add_agent_fields.sql` - Adds fields to custom_agents table
    - `002_add_template_fields.sql` - Adds fields to agent_templates table

- `data/` - Data management scripts
  - `001_enhanced_package_tracking_template.sql` - Creates or updates the package tracking template
  - `sample_data.sql` - Inserts sample data for development

- `utilities/` - Utility scripts
  - `backup_restore.sh` - Backup and restore utilities
  - `maintenance.sql` - Database maintenance operations

- `run_scripts.py` - Script runner that tracks execution

## Usage

### First-Time Setup

1. Run setup scripts to create database structure:
   ```bash
   python backend/database/scripts/run_scripts.py --type setup
   ```

### Version Updates

Run update scripts for a specific version:
```bash
python backend/database/scripts/run_scripts.py --type updates --version v1.0.0
```

### Data Management

Run data scripts to insert or update master data:
```bash
python backend/database/scripts/run_scripts.py --type data
```

### Specifying Database URL

You can specify a database URL directly:
```bash
python backend/database/scripts/run_scripts.py --type setup --db-url postgresql://user:password@hostname/dbname
```

Or use the DATABASE_URL environment variable:
```bash
export DATABASE_URL=postgresql://user:password@hostname/dbname
python backend/database/scripts/run_scripts.py --type setup
```

## Script Execution Tracking

The system tracks which scripts have been executed to prevent duplicate runs. This is stored in the `db_script_execution` table with the following information:

- `script_name`: Name of the executed script
- `executed_at`: Timestamp when the script was executed
- `version`: Version the script belongs to
- `status`: Execution status ('SUCCESS' or 'FAILED')

## Adding New Scripts

1. For new releases, create a new version directory:
   ```bash
   mkdir -p backend/database/scripts/updates/v1.1.0
   ```

2. Add scripts with numerical prefixes:
   ```
   001_add_new_feature.sql
   002_update_indexes.sql
   ```

3. Run the update scripts for the new version:
   ```bash
   python backend/database/scripts/run_scripts.py --type updates --version v1.1.0
   ```

## Notes

- All scripts are idempotent (can be run multiple times safely)
- Scripts use PostgreSQL-specific features and require PostgreSQL 13+
- Always ensure you have proper backups before performing updates