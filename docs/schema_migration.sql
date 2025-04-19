-- Database Schema Migration for Staples Brain
-- This script organizes existing tables into logical schemas

-- Create schemas
CREATE SCHEMA IF NOT EXISTS agent_core;
CREATE SCHEMA IF NOT EXISTS orchestration;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS entity;
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS tools;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS domain;

-- Move tables to appropriate schemas
-- 1. Agent Core System
ALTER TABLE agent_definitions SET SCHEMA agent_core;
ALTER TABLE agent_types SET SCHEMA agent_core;
ALTER TABLE agent_config SET SCHEMA agent_core;
ALTER TABLE agent_patterns SET SCHEMA agent_core;
ALTER TABLE agent_pattern_embeddings SET SCHEMA agent_core;
ALTER TABLE agent_response_templates SET SCHEMA agent_core;
ALTER TABLE custom_agents SET SCHEMA agent_core;
ALTER TABLE llm_agent_configurations SET SCHEMA agent_core;
ALTER TABLE retrieval_agent_configurations SET SCHEMA agent_core;
ALTER TABLE rule_agent_configurations SET SCHEMA agent_core;
ALTER TABLE system_prompts SET SCHEMA agent_core;

-- 2. Supervisor/Orchestration System
ALTER TABLE supervisor_configurations SET SCHEMA orchestration;
ALTER TABLE supervisor_agent_mappings SET SCHEMA orchestration;
ALTER TABLE orchestration_state SET SCHEMA orchestration;

-- 3. Memory and Conversation System
ALTER TABLE memory_entry SET SCHEMA memory;
ALTER TABLE memory_index SET SCHEMA memory;
ALTER TABLE memory_context SET SCHEMA memory;
ALTER TABLE conversations SET SCHEMA memory;
ALTER TABLE conversations_new SET SCHEMA memory;
ALTER TABLE message SET SCHEMA memory;
ALTER TABLE messages SET SCHEMA memory;

-- 4. Entity Management System
ALTER TABLE entity_definitions SET SCHEMA entity;
ALTER TABLE entity_enum_values SET SCHEMA entity;
ALTER TABLE entity_extraction_patterns SET SCHEMA entity;
ALTER TABLE entity_transformations SET SCHEMA entity;
ALTER TABLE agent_entity_mappings SET SCHEMA entity;

-- 5. Workflow System
ALTER TABLE workflows SET SCHEMA workflow;
ALTER TABLE workflow_nodes SET SCHEMA workflow;
ALTER TABLE workflow_edges SET SCHEMA workflow;

-- 6. Tools and Components System
ALTER TABLE tools SET SCHEMA tools;
ALTER TABLE tool_calls SET SCHEMA tools;
ALTER TABLE tool_usage_stats SET SCHEMA tools;
ALTER TABLE agent_tools SET SCHEMA tools;
ALTER TABLE component_templates SET SCHEMA tools;
ALTER TABLE component_template SET SCHEMA tools;
ALTER TABLE agent_components SET SCHEMA tools;
ALTER TABLE agent_component SET SCHEMA tools;
ALTER TABLE component_connections SET SCHEMA tools;
ALTER TABLE component_connection SET SCHEMA tools;
ALTER TABLE service_registry SET SCHEMA tools;
ALTER TABLE service_dependencies SET SCHEMA tools;

-- 7. Analytics and Telemetry System
ALTER TABLE telemetry_events SET SCHEMA analytics;
ALTER TABLE telemetry_sessions SET SCHEMA analytics;
ALTER TABLE analytics_data SET SCHEMA analytics;

-- 8. Domain-Specific Tables
ALTER TABLE package_tracking SET SCHEMA domain;
ALTER TABLE password_reset SET SCHEMA domain;
ALTER TABLE product_info SET SCHEMA domain;
ALTER TABLE store_locator SET SCHEMA domain;

-- Add documentation comments to core tables
COMMENT ON SCHEMA agent_core IS 'Core agent system tables';
COMMENT ON SCHEMA orchestration IS 'Supervisor and orchestration system tables';
COMMENT ON SCHEMA memory IS 'Memory and conversation history tables';
COMMENT ON SCHEMA entity IS 'Entity definition and management tables';
COMMENT ON SCHEMA workflow IS 'Workflow definition and management tables';
COMMENT ON SCHEMA tools IS 'Tools and component definition tables';
COMMENT ON SCHEMA analytics IS 'Analytics and telemetry tables';
COMMENT ON SCHEMA domain IS 'Domain-specific functionality tables';

-- Document key tables
COMMENT ON TABLE agent_core.agent_definitions IS 'Core definitions of agents in the system';
COMMENT ON TABLE orchestration.supervisor_configurations IS 'Definitions of supervisors that orchestrate agent interactions';
COMMENT ON TABLE memory.memory_entry IS 'Individual memory entries for conversation context';
COMMENT ON TABLE entity.entity_definitions IS 'Definitions of entities that can be extracted from user messages';
COMMENT ON TABLE workflow.workflows IS 'Definitions of workflows that can be executed by agents';
COMMENT ON TABLE tools.tools IS 'Definitions of tools that can be used by agents';

-- Tables to consolidate
-- These could be handled in a separate migration to avoid data loss
-- Example consolidation:
/*
-- Create a consolidated agent_components table
CREATE TABLE tools.agent_components_new (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agent_core.agent_definitions(id),
    component_id UUID NOT NULL REFERENCES tools.component_templates(id),
    config JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Migrate data from both tables
INSERT INTO tools.agent_components_new (id, agent_id, component_id, config, created_at, updated_at)
SELECT id, agent_id, component_id, config, created_at, updated_at
FROM tools.agent_components;

INSERT INTO tools.agent_components_new (id, agent_id, component_id, created_at, updated_at)
SELECT id, agent_id, component_id, created_at, COALESCE(updated_at, created_at)
FROM tools.agent_component
ON CONFLICT (id) DO NOTHING;

-- Drop old tables and rename new table
DROP TABLE tools.agent_components;
DROP TABLE tools.agent_component;
ALTER TABLE tools.agent_components_new RENAME TO agent_components;
*/