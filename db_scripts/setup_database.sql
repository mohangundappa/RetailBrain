-- Database setup script for Staples Brain
-- Supports setting up databases for different environments (dev, qa, staging, prod)

-- Set environment-specific variables
\set env `echo $APP_ENV`

-- Default to development if no environment specified
\if :'env' = ''
  \set env 'development'
\endif

-- Define database names for each environment
\if :'env' = 'development'
  \set dbname 'staples_brain_dev'
  \set username 'staples_dev'
  \set password 'dev_password'
\elif :'env' = 'testing'
  \set dbname 'staples_brain_test'
  \set username 'staples_test'
  \set password 'test_password'
\elif :'env' = 'qa'
  \set dbname 'staples_brain_qa'
  \set username 'staples_qa'
  \set password 'qa_password'
\elif :'env' = 'staging'
  \set dbname 'staples_brain_staging'
  \set username 'staples_staging'
  \set password 'staging_password'
\elif :'env' = 'production'
  \set dbname 'staples_brain_prod'
  \set username 'staples_prod'
  \set password 'prod_password'
\else
  \set dbname 'staples_brain_custom'
  \set username 'staples_custom'
  \set password 'custom_password'
\endif

-- Display environment being set up
\echo 'Setting up database for environment: ' :env

-- Create database (run as postgres user)
CREATE DATABASE :dbname;
\echo 'Created database: ' :dbname

-- Create user (run as postgres user)
CREATE USER :username WITH PASSWORD :'password';
\echo 'Created user: ' :username

-- Grant privileges (run as postgres user)
GRANT ALL PRIVILEGES ON DATABASE :dbname TO :username;

-- Connect to the new database
\c :dbname

-- Grant schema privileges to the user
GRANT ALL ON SCHEMA public TO :username;

-- After connecting to the database, you can run the create_tables.sql script
-- to create all necessary tables
\echo 'Database setup complete for environment: ' :env
\echo 'Next steps: Run create_tables.sql to create the schema'
\echo 'Example: psql -U ' :username ' -d ' :dbname ' -f create_tables.sql'

-- Set environment variables in your application:
\echo 'Set these environment variables in your .env file:'
\echo 'APP_ENV=' :env
\echo 'DATABASE_URL=postgresql://' :username ':' :password '@localhost/' :dbname
\echo 'PGUSER=' :username
\echo 'PGPASSWORD=' :password
\echo 'PGHOST=localhost'
\echo 'PGDATABASE=' :dbname
\echo 'PGPORT=5432'