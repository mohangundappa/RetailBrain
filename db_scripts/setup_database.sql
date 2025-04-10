-- Local Development Database Setup Script for Staples Brain
-- IMPORTANT: This script is FOR LOCAL DEVELOPMENT ONLY
-- In enterprise environments, databases should be created once by DBAs
-- See enterprise_setup.md for real-world enterprise database management guidelines

\echo '================================================================='
\echo '  WARNING: This script is for local development environments only'
\echo '  For enterprise environments, follow the guidelines in:'
\echo '  enterprise_setup.md'
\echo '================================================================='
\echo ''

-- Set environment-specific variables
\set env `echo $APP_ENV`

-- Default to development if no environment specified
\if :'env' = ''
  \set env 'development'
\endif

-- Define database names for each environment (for local development only)
\if :'env' = 'development'
  \set dbname 'staples_brain_dev'
  \set username 'staples_dev'
  \set password 'dev_password'
\elif :'env' = 'testing'
  \set dbname 'staples_brain_test'
  \set username 'staples_test'
  \set password 'test_password'
\else
  \echo 'ERROR: This script should not be used for creating QA, staging, or production databases!'
  \echo 'In enterprise environments, database creation is managed by database administrators.'
  \echo 'See enterprise_setup.md for proper setup guidelines.'
  \echo 'Exiting without making any changes.'
  \q
\endif

-- Display environment being set up
\echo 'Setting up local development database for environment: ' :env

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

\echo ''
\echo '================================================================='
\echo '  REMINDER: For enterprise environments, databases should be'
\echo '  provisioned by database administrators according to'
\echo '  organizational policy. See enterprise_setup.md for details.'
\echo '================================================================='