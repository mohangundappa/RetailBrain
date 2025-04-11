-- Database maintenance script for Staples Brain
-- Supports different retention policies based on environment

-- Set environment-specific variables
\set env `echo $APP_ENV`

-- Default to development if no environment specified
\if :'env' = ''
  \set env 'development'
\endif

-- Define retention periods for each environment
\if :'env' = 'development'
  \set retention_days '14 days'
  \echo 'Running maintenance for DEVELOPMENT environment (retention: 14 days)'
\elif :'env' = 'testing'
  \set retention_days '7 days'
  \echo 'Running maintenance for TESTING environment (retention: 7 days)'
\elif :'env' = 'qa'
  \set retention_days '30 days'
  \echo 'Running maintenance for QA environment (retention: 30 days)'
\elif :'env' = 'staging'
  \set retention_days '60 days'
  \echo 'Running maintenance for STAGING environment (retention: 60 days)'
\elif :'env' = 'production'
  \set retention_days '180 days'
  \echo 'Running maintenance for PRODUCTION environment (retention: 180 days)'
\else
  \set retention_days '30 days'
  \echo 'Running maintenance for UNKNOWN environment (retention: 30 days)'
\endif

-- Clean up old conversations based on environment retention policy
\echo 'Cleaning up conversations older than ' :retention_days
DELETE FROM conversation 
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL :'retention_days';

-- Optimize database
VACUUM ANALYZE;

-- Check table sizes
SELECT
  table_name,
  pg_size_pretty(pg_total_relation_size(quote_ident(table_name))),
  pg_total_relation_size(quote_ident(table_name))
FROM
  information_schema.tables
WHERE
  table_schema = 'public'
ORDER BY
  pg_total_relation_size(quote_ident(table_name)) DESC;

-- Enable pg_stat_statements extension for query analysis
-- (Run this as a superuser if not already enabled)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Check slow queries (requires pg_stat_statements extension)
-- SELECT query, calls, total_time, mean_time
-- FROM pg_stat_statements
-- ORDER BY mean_time DESC
-- LIMIT 10;

-- Reset query statistics (if needed)
-- SELECT pg_stat_statements_reset();

-- Check index usage
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS index_scans_count,
    idx_tup_read AS tuples_read_via_index,
    idx_tup_fetch AS tuples_fetched_via_index
FROM
    pg_stat_user_indexes
ORDER BY
    idx_scan DESC;

-- Drop unused indexes (uncomment and modify as needed)
-- DROP INDEX IF EXISTS idx_unused;