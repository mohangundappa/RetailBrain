# Supervisor Database Schema

## Overview

The supervisor-based architecture relies on a database-driven approach to configure and manage agent orchestration. This document details the database schema used to store supervisor configurations and their mappings to agents.

## Tables

### supervisor_configurations

This table stores the core configuration for each supervisor.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Supervisor name |
| description | TEXT | Supervisor description |
| version | INTEGER | Configuration version |
| status | VARCHAR(50) | Status (active, inactive, draft) |
| routing_strategy | VARCHAR(50) | Strategy for agent selection (pattern_match, vector_search, hybrid) |
| model_name | VARCHAR(100) | LLM model used for orchestration |
| temperature | FLOAT | Temperature setting for LLM |
| routing_prompt | TEXT | Prompt template for routing |
| nodes | JSONB | Graph node definitions |
| edges | JSONB | Graph edge definitions |
| edge_conditions | JSONB | Conditional routing rules |
| entry_node | VARCHAR(100) | Starting node for the graph |
| pattern_prioritization | BOOLEAN | Whether to prioritize pattern matching |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| created_by | VARCHAR(255) | Creator identifier |

### supervisor_agent_mappings

This table maps agents to specific nodes within a supervisor's graph.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| supervisor_id | UUID | Foreign key to supervisor_configurations |
| agent_id | UUID | Foreign key to agent_definitions |
| node_id | VARCHAR(100) | Node identifier in the graph |
| execution_order | INTEGER | Order within the node (for multiple agents) |
| config | JSONB | Agent-specific configuration |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

## Schema Relationships

```
supervisor_configurations 1 ──────┐
                                 │
                                 │ has many
                                 │
                                 ▼
          supervisor_agent_mappings ◄──┐
                      │                │
                      │ refers to      │ refers to
                      │                │
                      ▼                │
          agent_definitions ───────────┘
```

## JSON Structure Examples

### nodes

The `nodes` column stores the graph node definitions as a JSON object:

```json
{
  "router": {
    "type": "router",
    "name": "Router",
    "description": "Routes to appropriate agent"
  },
  "agent_executor": {
    "type": "agent",
    "name": "Agent Executor",
    "description": "Executes agent tasks"
  },
  "guardrails": {
    "type": "guardrails",
    "name": "Guardrails",
    "description": "Ensures responses meet policy requirements"
  },
  "memory_store": {
    "type": "memory_store",
    "name": "Memory Store",
    "description": "Manages conversation memory"
  }
}
```

### edges

The `edges` column stores the connections between nodes:

```json
{
  "router": [
    {"target": "agent_executor"}
  ],
  "agent_executor": [
    {"target": "guardrails"}
  ],
  "guardrails": [
    {"target": "memory_store"}
  ],
  "memory_store": [
    {"target": "__end__"}
  ]
}
```

### edge_conditions

The `edge_conditions` column defines conditional routing rules:

```json
{
  "router": {
    "agent_executor": "state.get('confidence', 0) > 0.7",
    "fallback": "state.get('confidence', 0) <= 0.7"
  }
}
```

### config

The `config` column in supervisor_agent_mappings stores agent-specific settings:

```json
{
  "max_tokens": 500,
  "use_pattern_matching": true,
  "custom_prompt": "You are a specialized agent for {agent_type}..."
}
```

## Example SQL Queries

### Creating a New Supervisor

```sql
INSERT INTO supervisor_configurations
(id, name, description, version, status, routing_strategy, model_name, temperature, 
 routing_prompt, nodes, edges, edge_conditions, entry_node, pattern_prioritization, 
 created_at, updated_at, created_by)
VALUES 
(gen_random_uuid(), 'Default Supervisor', 'Main supervisor for agent orchestration', 1, 'active',
 'vector_search', 'gpt-4o', 0.2, 'Route to the most appropriate agent', 
 '{"router": {"type": "router"}, "agent_executor": {"type": "agent"}, "guardrails": {"type": "guardrails"}}',
 '{"router": [{"target": "agent_executor"}], "agent_executor": [{"target": "guardrails"}], "guardrails": [{"target": "__end__"}]}',
 '{}', 'router', true, now(), now(), 'system');
```

### Mapping Agents to a Supervisor

```sql
INSERT INTO supervisor_agent_mappings 
(id, supervisor_id, agent_id, node_id, execution_order, config, created_at, updated_at)
VALUES 
(gen_random_uuid(), 
 (SELECT id FROM supervisor_configurations WHERE name = 'Default Supervisor' LIMIT 1),
 (SELECT id FROM agent_definitions WHERE name = 'General Conversation Agent' LIMIT 1),
 'agent_executor', 1, '{}'::jsonb, now(), now());
```

### Querying Active Supervisors

```sql
SELECT sc.*, 
       COUNT(sam.id) as agent_count
FROM supervisor_configurations sc
LEFT JOIN supervisor_agent_mappings sam ON sc.id = sam.supervisor_id
WHERE sc.status = 'active'
GROUP BY sc.id
ORDER BY sc.created_at DESC;
```

## Migration Considerations

When upgrading from the previous architecture:

1. Create the necessary database tables
2. Configure at least one supervisor with appropriate agent mappings
3. Map existing agents to appropriate nodes in the graph
4. Set the supervisor status to 'active' to enable it

## Best Practices

1. **Version Management**
   - Increment the version number when making changes to a supervisor
   - Consider maintaining multiple versions for testing

2. **Node Naming**
   - Use descriptive node names that reflect their purpose
   - Maintain consistent naming conventions across supervisors

3. **Agent Mapping**
   - Map agents to nodes based on their functional role
   - Consider execution order for multiple agents in the same node

4. **Status Management**
   - Use 'draft' status for supervisors in development
   - Test thoroughly before changing status to 'active'
   - Deactivate supervisors with 'inactive' status rather than deleting