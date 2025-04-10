# Database Migrations

This directory contains database migrations for the Staples Brain application. We use Flask-Migrate (based on Alembic) to manage schema changes in a controlled and reversible way.

## Migration Principles

In an enterprise environment like Staples, database changes follow these principles:

1. **All schema changes are versioned** and tracked in source control
2. **Changes are incremental** - we never drop and recreate the entire database
3. **Every change is reversible** with a proper downgrade path
4. **Migrations are tested** before deployment to production
5. **Data integrity is preserved** during schema changes

## Setting Up Migrations

### First-Time Setup

If you're setting up migrations for the first time:

```bash
# Initialize the migrations directory (already done in this repo)
flask db init

# Create the first migration based on current models
flask db migrate -m "Initial migration"

# Apply the migration to create the schema
flask db upgrade
```

### Development Workflow

When making schema changes:

1. Update your model definitions in `models.py`
2. Generate a migration:
   ```bash
   flask db migrate -m "Description of your schema changes"
   ```
3. Review the generated migration script in `migrations/versions/`
4. Apply the migration:
   ```bash
   flask db upgrade
   ```
5. Test thoroughly
6. Commit the migration files to source control

## Deployment Process

In production environments:

1. Never run `flask db migrate` - migrations should be created and tested in development
2. Apply migrations as part of the deployment process:
   ```bash
   flask db upgrade
   ```
3. Have a rollback plan ready in case of issues:
   ```bash
   flask db downgrade
   ```

## Best Practices

- Always review auto-generated migrations before applying them
- Manually adjust migrations that might cause data loss
- Include data migrations when necessary (e.g., populating new columns)
- Test migrations against a copy of production data when possible
- Never make manual schema changes in production

## Migration Commands Reference

- `flask db migrate -m "message"` - Generate a new migration
- `flask db upgrade` - Apply all pending migrations
- `flask db downgrade` - Revert the most recent migration
- `flask db upgrade <revision>` - Upgrade to a specific revision
- `flask db downgrade <revision>` - Downgrade to a specific revision
- `flask db current` - Show current revision
- `flask db history` - Show migration history
- `flask db show <revision>` - Show details for a revision

For more information, see the [Flask-Migrate documentation](https://flask-migrate.readthedocs.io/)