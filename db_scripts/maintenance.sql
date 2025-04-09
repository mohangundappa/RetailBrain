-- Database maintenance script for Staples Brain

-- Clean up old conversations (older than 30 days)
DELETE FROM conversation 
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

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