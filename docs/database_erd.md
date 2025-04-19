# Staples Brain Database ERD

Below are Entity-Relationship Diagrams (ERDs) for the Staples Brain database, organized by logical subsystems. These diagrams show the key tables, their primary relationships, and a simplified view of their structures.

## 1. Core Agent System ERD
```
┌─────────────────────────┐          ┌───────────────────────┐
│ agent_definitions       │          │ agent_types           │
├─────────────────────────┤          ├───────────────────────┤
│ id (PK)                 │◄─────────┤ id (PK)               │
│ name                    │          │ name                  │
│ description             │          │ description           │
│ agent_type              │──────────┘ config_schema         │
│ version                 │          └───────────────────────┘
│ status                  │               ▲
│ is_system               │               │
│ created_at              │               │
│ updated_at              │               │ 
│ created_by              │               │
│ workflow_id (FK)───────────────────────┐
│ prompt_config           │               │
└─────────────────────────┘               │
        ▲                                 │
        │                                 │
        │                                 │
        │                                 │
┌───────┴─────────────┐          ┌───────┴─────────────┐
│ agent_patterns      │          │ workflows            │
├─────────────────────┤          ├─────────────────────┤
│ id (PK)             │          │ id (PK)             │
│ agent_id (FK)       │          │ name                │
│ pattern_type        │          │ description         │
│ pattern_value       │          │ version             │
│ priority            │          │ status              │
│ confidence_boost    │          │ created_at          │
│ created_at          │          │ updated_at          │
└─────────────────────┘          └─────────────────────┘
        ▲                                ▲
        │                                │
        │                                │
        │                                │
┌───────┴─────────────┐          ┌───────┴─────────────┐
│ agent_pattern_      │          │ workflow_nodes       │
│ embeddings          │          ├─────────────────────┤
├─────────────────────┤          │ id (PK)             │
│ id (PK)             │          │ workflow_id (FK)    │
│ pattern_id (FK)     │          │ node_id             │
│ embedding           │          │ node_type           │
│ created_at          │          │ config              │
└─────────────────────┘          └─────────────────────┘
                                          ▲
                                          │
                                          │
                                          │
                                 ┌────────┴──────────┐
                                 │ workflow_edges    │
                                 ├───────────────────┤
                                 │ id (PK)           │
                                 │ workflow_id (FK)  │
                                 │ source_node_id    │
                                 │ target_node_id    │
                                 │ conditions        │
                                 └───────────────────┘
```

## 2. Orchestration System ERD
```
┌───────────────────────────┐          ┌─────────────────────────────┐          ┌─────────────────────────┐
│ supervisor_configurations │          │ supervisor_agent_mappings   │          │ agent_definitions       │
├───────────────────────────┤          ├─────────────────────────────┤          ├─────────────────────────┤
│ id (PK)                   │◄─────────┤ id (PK)                     │──────────►│ id (PK)                 │
│ name                      │          │ supervisor_id (FK)          │          │ name                    │
│ description               │          │ agent_id (FK)               │          │ description             │
│ version                   │          │ node_id                     │          │ agent_type              │
│ status                    │          │ execution_order             │          │ version                 │
│ routing_strategy          │          │ config                      │          │ status                  │
│ model_name                │          │ created_at                  │          │ is_system               │
│ temperature               │          │ updated_at                  │          │ created_at              │
│ routing_prompt            │          └─────────────────────────────┘          │ updated_at              │
│ nodes                     │                                                   │ created_by              │
│ edges                     │                                                   │ workflow_id             │
│ edge_conditions           │                                                   │ prompt_config           │
│ entry_node                │                                                   └─────────────────────────┘
│ pattern_prioritization    │                      ┌─────────────────────────┐
│ created_at                │                      │ orchestration_state     │
│ updated_at                │                      ├─────────────────────────┤
│ created_by                │                      │ id (PK)                 │
└───────────────────────────┘                      │ session_id              │
                                                   │ state_data              │
                                                   │ created_at              │
                                                   │ updated_at              │
                                                   └─────────────────────────┘
```

## 3. Memory and Conversation System ERD
```
┌───────────────────────┐          ┌───────────────────────┐          ┌───────────────────────┐
│ conversations         │          │ messages              │          │ memory_entry          │
├───────────────────────┤          ├───────────────────────┤          ├───────────────────────┤
│ id (PK)               │◄─────────┤ id (PK)               │          │ id (PK)               │
│ session_id            │          │ conversation_id (FK)  │          │ session_id            │
│ user_input            │          │ content               │          │ conversation_id       │
│ brain_response        │          │ role                  │          │ agent_id              │
│ intent                │          │ created_at            │          │ memory_type           │
│ confidence            │          │ metadata              │          │ role                  │
│ selected_agent        │          └───────────────────────┘          │ content               │
│ created_at            │                                             │ importance            │
│ updated_at            │                                             │ relevance             │
│ user_id               │                                             │ recency               │
│ meta_data             │                                             │ embedding             │
└───────────────────────┘                                             │ meta_data             │
                                                                      │ created_at            │
                                                                      │ expires_at            │
                                                                      └───────────────────────┘
                                                                                ▲
                                                                                │
                                                                                │
                                                                      ┌─────────┴─────────┐
                      ┌───────────────────────┐          ┌───────────┴───────────┐       │
                      │ memory_context        │          │ memory_index          │       │
                      ├───────────────────────┤          ├───────────────────────┤       │
                      │ id (PK)               │          │ id (PK)               │       │
                      │ memory_id (FK)        │──────────┤ memory_id (FK)        │───────┘
                      │ context_type          │          │ index_type            │
                      │ context_value         │          │ index_value           │
                      │ created_at            │          │ created_at            │
                      └───────────────────────┘          └───────────────────────┘
```

## 4. Entity Management System ERD
```
┌─────────────────────────┐          ┌───────────────────────────┐          ┌───────────────────────────┐
│ entity_definitions      │          │ agent_entity_mappings     │          │ agent_definitions         │
├─────────────────────────┤          ├───────────────────────────┤          ├───────────────────────────┤
│ id (PK)                 │◄─────────┤ id (PK)                   │──────────►│ id (PK)                   │
│ name                    │          │ agent_id (FK)             │          │ name                      │
│ display_name            │          │ entity_id (FK)            │          │ description               │
│ description             │          │ is_required               │          │ agent_type                │
│ entity_type             │          │ created_at                │          │ version                   │
│ validation_regex        │          │ updated_at                │          │ status                    │
│ is_required             │          └───────────────────────────┘          │ is_system                 │
│ default_value           │                                                 │ created_at                │
│ created_at              │                                                 │ updated_at                │
│ updated_at              │                                                 │ created_by                │
└─────────────────────────┘                                                 │ workflow_id               │
        ▲                                                                   │ prompt_config             │
        │                                                                   └───────────────────────────┘
        │
        │
┌───────┴─────────────┐          ┌───────────────────────┐
│ entity_enum_values  │          │ entity_extraction_    │
├─────────────────────┤          │ patterns              │
│ id (PK)             │          ├───────────────────────┤
│ entity_id (FK)      │          │ id (PK)               │
│ value               │          │ entity_id (FK)        │
│ display_name        │          │ pattern               │
│ created_at          │          │ priority              │
│ updated_at          │          │ created_at            │
└─────────────────────┘          └───────────────────────┘
```

## 5. Tools and Components System ERD
```
┌─────────────────────┐          ┌─────────────────────┐          ┌───────────────────────┐
│ tools               │          │ agent_tools         │          │ agent_definitions     │
├─────────────────────┤          ├─────────────────────┤          ├───────────────────────┤
│ id (PK)             │◄─────────┤ id (PK)             │──────────►│ id (PK)               │
│ name                │          │ agent_id (FK)       │          │ name                  │
│ description         │          │ tool_id (FK)        │          │ description           │
│ tool_type           │          │ parameters          │          │ agent_type            │
│ schema              │          │ created_at          │          │ version               │
│ url                 │          └─────────────────────┘          │ status                │
│ created_at          │                   ▲                       │ is_system             │
│ updated_at          │                   │                       │ created_at            │
└─────────────────────┘                   │                       │ updated_at            │
        ▲                                 │                       │ created_by            │
        │                                 │                       │ workflow_id           │
        │                                 │                       │ prompt_config         │
        │                                 │                       └───────────────────────┘
┌───────┴─────────────┐                   │
│ tool_calls          │                   │
├─────────────────────┤                   │
│ id (PK)             │                   │
│ tool_id (FK)        │                   │
│ session_id          │                   │
│ parameters          │                   │
│ result              │                   │
│ created_at          │                   │
└─────────────────────┘                   │
                                          │
┌─────────────────────┐                   │
│ tool_usage_stats    │                   │
├─────────────────────┤                   │
│ id (PK)             │                   │
│ tool_id (FK)        │                   │
│ usage_count         │                   │
│ success_rate        │                   │
│ created_at          │                   │
│ updated_at          │                   │
└─────────────────────┘                   │
                                          │
┌─────────────────────────┐               │
│ component_templates     │               │
├─────────────────────────┤               │
│ id (PK)                 │               │
│ name                    │               │
│ component_type          │               │
│ template                │               │
│ created_at              │               │
│ updated_at              │               │
└─────────────────────────┘               │
        ▲                                 │
        │                                 │
        │                                 │
┌───────┴─────────────────┐               │
│ agent_components        │               │
├─────────────────────────┤               │
│ id (PK)                 │─────────────────┐
│ agent_id (FK)           │               │ │
│ component_id (FK)       │               │ │
│ config                  │               │ │
│ created_at              │               │ │
│ updated_at              │               │ │
└─────────────────────────┘               │ │
                                          │ │
┌───────────────────────────┐             │ │
│ component_connections     │             │ │
├───────────────────────────┤             │ │
│ id (PK)                   │             │ │
│ source_component_id (FK)  │─────────────┘ │
│ target_component_id (FK)  │─────────────┐ │
│ connection_type           │             │ │
│ created_at                │             │ │
│ updated_at                │             │ │
└───────────────────────────┘             │ │
                                          │ │
┌───────────────────────────┐             │ │
│ agent_compositions        │             │ │
├───────────────────────────┤             │ │
│ id (PK)                   │             │ │
│ agent_id (FK)             │─────────────┘ │
│ composition_type          │               │
│ config                    │               │
│ created_at                │               │
│ updated_at                │               │
└───────────────────────────┘               │
```

## 6. Analytics and Telemetry System ERD
```
┌───────────────────────┐          ┌───────────────────────┐
│ telemetry_events      │          │ telemetry_sessions    │
├───────────────────────┤          ├───────────────────────┤
│ id (PK)               │          │ id (PK)               │
│ session_id (FK)       │──────────►│ session_id            │
│ event_type            │          │ user_id               │
│ event_data            │          │ start_time            │
│ timestamp             │          │ end_time              │
│ created_at            │          │ status                │
└───────────────────────┘          │ metadata              │
                                   └───────────────────────┘
                                            ▲
                                            │
                                            │
                                   ┌────────┴──────────┐
                                   │ analytics_data    │
                                   ├───────────────────┤
                                   │ id (PK)           │
                                   │ session_id (FK)   │
                                   │ data_type         │
                                   │ data_value        │
                                   │ timestamp         │
                                   │ created_at        │
                                   └───────────────────┘
```

## 7. Domain-Specific Tables ERD
```
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│ package_tracking    │          │ password_reset      │          │ product_info        │          │ store_locator       │
├─────────────────────┤          ├─────────────────────┤          ├─────────────────────┤          ├─────────────────────┤
│ id (PK)             │          │ id (PK)             │          │ id (PK)             │          │ id (PK)             │
│ tracking_number     │          │ user_id             │          │ product_id          │          │ store_id            │
│ status              │          │ reset_token         │          │ name                │          │ name                │
│ carrier             │          │ email               │          │ description         │          │ address             │
│ last_update         │          │ created_at          │          │ price               │          │ city                │
│ delivery_date       │          │ expires_at          │          │ category            │          │ state               │
│ created_at          │          │ used                │          │ inventory           │          │ zip                 │
│ updated_at          │          │ updated_at          │          │ created_at          │          │ phone               │
└─────────────────────┘          └─────────────────────┘          │ updated_at          │          │ hours               │
                                                                  └─────────────────────┘          │ created_at          │
                                                                                                   │ updated_at          │
                                                                                                   └─────────────────────┘
```

## Legend
- **PK**: Primary Key
- **FK**: Foreign Key
- ◄───►: One-to-Many relationship
- ◄─────►: Many-to-Many relationship

## Notes
1. These diagrams focus on key relationships and may not show every column or table.
2. Foreign key relationships are indicated with arrows.
3. Similar/duplicate tables (like agent_component/agent_components) are represented by the more complete version.
4. This representation is a simplified view to aid understanding; actual database schema may have additional details.

## Database Schema Organization Recommendation

With this visual understanding, here's how your database could be organized into logical schemas:

```
staples_brain
├── agent_core
│   ├── agent_definitions
│   ├── agent_types
│   ├── agent_patterns
│   ├── agent_pattern_embeddings
│   ├── ...
├── orchestration
│   ├── supervisor_configurations
│   ├── supervisor_agent_mappings
│   ├── orchestration_state
│   ├── ...
├── memory
│   ├── memory_entry
│   ├── memory_index
│   ├── memory_context
│   ├── conversations
│   ├── messages
│   ├── ...
├── entity
│   ├── entity_definitions
│   ├── entity_enum_values
│   ├── entity_extraction_patterns
│   ├── agent_entity_mappings
│   ├── ...
├── workflow
│   ├── workflows
│   ├── workflow_nodes
│   ├── workflow_edges
│   ├── ...
├── tools
│   ├── tools
│   ├── tool_calls
│   ├── agent_tools
│   ├── component_templates
│   ├── agent_components
│   ├── ...
├── analytics
│   ├── telemetry_events
│   ├── telemetry_sessions
│   ├── analytics_data
│   ├── ...
└── domain
    ├── package_tracking
    ├── password_reset
    ├── product_info
    ├── store_locator
    ├── ...
```