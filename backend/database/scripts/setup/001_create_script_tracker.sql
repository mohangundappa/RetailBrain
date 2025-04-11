-- Create a table to track script execution
CREATE TABLE IF NOT EXISTS db_script_execution (
    script_name VARCHAR(255) PRIMARY KEY,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- Add index on version for faster queries
CREATE INDEX IF NOT EXISTS idx_db_script_execution_version ON db_script_execution(version);

-- Add a comment for documentation
COMMENT ON TABLE db_script_execution IS 'Tracks database script execution to prevent duplicate runs';