#!/bin/bash
# Database backup and restore script for Staples Brain

# Set environment variables for database connection
# You can also source these from your .env file
export PGUSER=${PGUSER:-staples_user}
export PGPASSWORD=${PGPASSWORD:-your_secure_password}
export PGHOST=${PGHOST:-localhost}
export PGDATABASE=${PGDATABASE:-staples_brain}
export PGPORT=${PGPORT:-5432}

# Create backup directory if it doesn't exist
BACKUP_DIR="./db_backups"
mkdir -p $BACKUP_DIR

# Function to create a backup
create_backup() {
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  BACKUP_FILE="$BACKUP_DIR/staples_brain_$TIMESTAMP.dump"
  
  echo "Creating backup to $BACKUP_FILE..."
  pg_dump -Fc -f "$BACKUP_FILE"
  
  if [ $? -eq 0 ]; then
    echo "Backup created successfully."
    echo "To restore this backup, run: $0 restore $BACKUP_FILE"
  else
    echo "Error creating backup."
    exit 1
  fi
}

# Function to restore a backup
restore_backup() {
  BACKUP_FILE=$1
  
  if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file $BACKUP_FILE not found."
    exit 1
  fi
  
  echo "WARNING: This will overwrite the existing database. Are you sure? (y/n)"
  read -r confirm
  
  if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "Restoring from $BACKUP_FILE..."
    pg_restore -c -d "$PGDATABASE" "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
      echo "Restore completed successfully."
    else
      echo "Error during restore."
      exit 1
    fi
  else
    echo "Restore canceled."
  fi
}

# Function to list available backups
list_backups() {
  echo "Available backups:"
  ls -lh "$BACKUP_DIR"
}

# Main logic
case "$1" in
  backup)
    create_backup
    ;;
  restore)
    if [ -z "$2" ]; then
      echo "Error: No backup file specified."
      echo "Usage: $0 restore <backup_file>"
      exit 1
    fi
    restore_backup "$2"
    ;;
  list)
    list_backups
    ;;
  *)
    echo "Usage: $0 {backup|restore <backup_file>|list}"
    echo ""
    echo "Examples:"
    echo "  $0 backup        - Create a new backup"
    echo "  $0 list          - List available backups"
    echo "  $0 restore file  - Restore from specified backup file"
    ;;
esac

exit 0