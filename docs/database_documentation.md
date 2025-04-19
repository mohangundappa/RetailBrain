# Staples Brain Database Documentation

## Database Overview

The Staples Brain database consists of 51 tables that can be logically grouped into the following categories:

1. **Agent Core System**: Tables managing agent definitions and configurations
2. **Supervisor/Orchestration System**: Tables managing supervisors and agent routing
3. **Memory and Conversation System**: Tables storing conversational memory and history
4. **Entity Management System**: Tables defining entities and their properties
5. **Workflow System**: Tables defining workflows and their components
6. **Tools and Components System**: Tables defining tools and agent components
7. **Analytics and Telemetry System**: Tables tracking usage and performance metrics
8. **Domain-Specific Tables**: Tables for specific business functions (package tracking, password reset, etc.)

## Table Categories

### 1. Agent Core System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| agent_definitions | Core table defining agents | id, name, description, agent_type, version, status, is_system |
| agent_types | Defines types of agents | (id, name, description) |
| agent_config | Stores agent configurations | (agent_id, config_key, config_value) |
| agent_patterns | Pattern-matching rules for routing messages to agents | agent_id, pattern_type, pattern_value, priority |
| agent_pattern_embeddings | Vector embeddings for semantic pattern matching | pattern_id, embedding |
| agent_response_templates | Templates for agent responses | agent_id, template_name, template_content |
| agent_tools | Tools associated with agents | agent_id, tool_id |
| custom_agents | User-created agent definitions | id, name, config |
| llm_agent_configurations | LLM-specific configurations for agents | agent_id, model_name, temperature |
| retrieval_agent_configurations | Configurations for retrieval-augmented agents | agent_id, retrieval_config |
| rule_agent_configurations | Configurations for rule-based agents | agent_id, rules |

### 2. Supervisor/Orchestration System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| supervisor_configurations | Defines supervisor configurations | id, name, description, routing_strategy, model_name |
| supervisor_agent_mappings | Maps agents to supervisors | supervisor_id, agent_id, node_id, execution_order |
| orchestration_state | Stores state of orchestration processes | session_id, state_data |

### 3. Memory and Conversation System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| memory_entry | Stores individual memory entries | id, session_id, conversation_id, memory_type, content |
| memory_index | Indexes for memory retrieval | memory_id, index_type, index_value |
| memory_context | Context information for memory retrieval | memory_id, context_type, context_value |
| conversations | Stores conversation history | id, session_id, user_input, brain_response, selected_agent |
| conversations_new | Newer version of conversations table | id, session_id, user_id, metadata |
| message | Individual messages in conversations | id, conversation_id, content, role |
| messages | Alternative message storage | id, conversation_id, content, role |

### 4. Entity Management System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| entity_definitions | Defines entities and their properties | id, name, display_name, entity_type, validation_regex |
| entity_enum_values | Enumeration values for entity types | entity_id, value, display_name |
| entity_transformations | Transformation rules for entities | entity_id, transformation_type, transformation_rule |
| entity_extraction_patterns | Patterns for extracting entities | entity_id, pattern, priority |
| agent_entity_mappings | Maps entities to agents | agent_id, entity_id, is_required |

### 5. Workflow System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| workflows | Defines workflows | id, name, description, version |
| workflow_nodes | Defines nodes in a workflow | workflow_id, node_id, node_type, config |
| workflow_edges | Defines connections between workflow nodes | workflow_id, source_node_id, target_node_id |

### 6. Tools and Components System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| tools | Defines tools available to agents | id, name, description, tool_type |
| tool_calls | Records of tool calls | id, tool_id, session_id, parameters, result |
| tool_usage_stats | Usage statistics for tools | tool_id, usage_count, success_rate |
| component_templates | Templates for reusable components | id, name, component_type, template |
| component_template | Older version of component templates | id, name, template |
| agent_components | Components used by agents | agent_id, component_id, config |
| agent_component | Older version of agent components | agent_id, component_id |
| component_connections | Connections between components | source_component_id, target_component_id |
| component_connection | Older version of component connections | source_id, target_id |
| service_registry | Registry of available services | id, name, endpoint, service_type |
| service_dependencies | Dependencies between services | service_id, dependency_id |

### 7. Analytics and Telemetry System

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| telemetry_events | Records telemetry events | id, event_type, event_data, timestamp |
| telemetry_sessions | Records session-level telemetry | id, session_id, user_id, metadata |
| analytics_data | Stores analytics information | id, data_type, data_value, timestamp |

### 8. Domain-Specific Tables

| Table Name | Description | Key Columns |
|------------|-------------|-------------|
| package_tracking | Package tracking information | id, tracking_number, status |
| password_reset | Password reset information | id, user_id, reset_token |
| product_info | Product information | id, product_id, name, description |
| store_locator | Store location information | id, store_id, name, address |

## Key Relationships

1. **Agent Hierarchy**:
   - `agent_definitions` is the central table for agents
   - `agent_patterns` links to `agent_definitions` via `agent_id`
   - `agent_tools` links agents to available tools
   - `agent_entity_mappings` connects agents to entities they can handle

2. **Supervisor Orchestration**:
   - `supervisor_configurations` defines supervisors
   - `supervisor_agent_mappings` connects supervisors to agents
   - This creates the agent orchestration hierarchy

3. **Memory and Conversations**:
   - `conversations` stores high-level conversation information
   - `message`/`messages` store individual messages
   - `memory_entry` stores processed memory information
   - `memory_index` and `memory_context` provide retrieval capabilities

4. **Workflows**:
   - `workflows` defines workflows
   - `workflow_nodes` defines steps in workflows
   - `workflow_edges` defines the flow between steps
   - `agent_definitions` can reference workflows via `workflow_id`

## Organization Recommendations

### 1. Schema Organization

To better organize your database tables, consider implementing schemas:

```sql
-- Core agent system
CREATE SCHEMA agent_core;
-- Supervisors and orchestration
CREATE SCHEMA orchestration;
-- Memory and conversations
CREATE SCHEMA memory;
-- Entities and their definitions
CREATE SCHEMA entity;
-- Tools and components
CREATE SCHEMA tools;
-- Analytics and telemetry
CREATE SCHEMA analytics;
-- Domain-specific functionality
CREATE SCHEMA domain;
```

Then move tables to appropriate schemas:

```sql
-- Example
ALTER TABLE agent_definitions SET SCHEMA agent_core;
ALTER TABLE supervisor_configurations SET SCHEMA orchestration;
ALTER TABLE memory_entry SET SCHEMA memory;
```

### 2. Standardize Naming Conventions

1. **Table Naming**: Use singular nouns (e.g., `agent_definition` instead of `agent_definitions`)
2. **Primary Keys**: Always use `id` as the primary key name
3. **Foreign Keys**: Use `[table_name]_id` format (e.g., `agent_id`)
4. **Timestamps**: Include `created_at` and `updated_at` in all tables
5. **Junction Tables**: Use both table names (e.g., `agent_tool` for the junction of agents and tools)

### 3. Consolidate Redundant Tables

Several tables appear to have duplicate functionality:
- `agent_component` and `agent_components`
- `component_template` and `component_templates`
- `component_connection` and `component_connections`
- `message` and `messages`
- `conversations` and `conversations_new`

Consolidate these into single tables with a clear migration path.

### 4. Enhanced Documentation

For each table, maintain:
1. **Table Comment**: Document purpose and lifecycle
2. **Column Comments**: Document each column's purpose
3. **Constraint Documentation**: Document the purpose of each constraint

Example:

```sql
COMMENT ON TABLE agent_core.agent_definition IS 'Core definition of agents in the system';
COMMENT ON COLUMN agent_core.agent_definition.id IS 'Unique identifier for the agent';
```

### 5. Version Control Database Changes

Implement database migrations using a tool like Alembic to track schema changes over time.

### 6. Database Diagram

Create and maintain an up-to-date Entity-Relationship Diagram (ERD) that shows the relationships between key tables.

## Query Examples

### Common Query Patterns

#### Find all Agents managed by a Supervisor:

```sql
SELECT a.name, a.description, a.agent_type 
FROM agent_definitions a
JOIN supervisor_agent_mappings sm ON sm.agent_id = a.id
WHERE sm.supervisor_id = '[supervisor_id]';
```

#### Retrieve Conversation History with Agent Selection:

```sql
SELECT c.user_input, c.brain_response, c.selected_agent, a.name as agent_name
FROM conversations c
LEFT JOIN agent_definitions a ON c.selected_agent = a.id::text
WHERE c.session_id = '[session_id]'
ORDER BY c.created_at;
```

#### Get Entity Definitions for an Agent:

```sql
SELECT e.name, e.display_name, e.entity_type
FROM entity_definitions e
JOIN agent_entity_mappings aem ON e.id = aem.entity_id
WHERE aem.agent_id = '[agent_id]';
```

## Performance Considerations

1. **Indexes**: Ensure indexes on frequently queried columns:
   - `session_id` in `conversations` and `memory_entry`
   - `agent_id` in junction tables
   - `created_at` for time-based queries

2. **Partitioning**: Consider partitioning large tables:
   - `memory_entry` by time ranges
   - `conversations` by time ranges
   - `telemetry_events` by event types and time

3. **Materialized Views**: Create materialized views for complex, frequently-accessed data:
   - Agent performance metrics
   - Conversation statistics
   - Memory usage patterns

## Next Steps for Database Evolution

1. **Regular Maintenance**:
   - Implement regular vacuum and analyze operations 
   - Monitor and optimize slow queries
   - Review and update indexes based on query patterns

2. **Data Lifecycle Management**:
   - Implement data retention policies
   - Archive old conversations and memory entries
   - Implement row-level security for sensitive data

3. **Scalability Planning**:
   - Prepare for horizontal scaling needs
   - Consider read replicas for reporting
   - Evaluate connection pooling configurations