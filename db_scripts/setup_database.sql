-- Database setup script for Staples Brain

-- Create database (run as postgres user)
CREATE DATABASE staples_brain;

-- Create user (run as postgres user)
CREATE USER staples_user WITH PASSWORD 'your_secure_password';

-- Grant privileges (run as postgres user)
GRANT ALL PRIVILEGES ON DATABASE staples_brain TO staples_user;

-- Connect to the new database
\c staples_brain

-- Grant schema privileges to the user
GRANT ALL ON SCHEMA public TO staples_user;

-- After connecting to the database, you can run the create_tables.sql script
-- to create all necessary tables