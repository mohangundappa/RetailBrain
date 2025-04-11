# Database Schema

## Overview

This document describes the database schema used by the Staples Brain system. The system uses PostgreSQL with SQLAlchemy as the ORM.

## Tables

### Conversation

Stores conversation history and metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| created_at | Timestamp | Creation timestamp |
| updated_at | Timestamp | Last update timestamp |
| user_id | String | User identifier |
| title | String | Conversation title |
| metadata | JSONB | Additional metadata |

### Message

Stores individual messages within conversations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| conversation_id | UUID | Foreign key to Conversation |
| created_at | Timestamp | Creation timestamp |
| role | String | Message role (user/assistant) |
| content | Text | Message content |
| metadata | JSONB | Additional metadata |

### TelemetrySession

Tracks telemetry sessions for monitoring and analytics.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| created_at | Timestamp | Creation timestamp |
| session_id | String | Session identifier |
| user_id | String | User identifier |
| metadata | JSONB | Session metadata |

### TelemetryEvent

Records individual telemetry events within sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | UUID | Foreign key to TelemetrySession |
| created_at | Timestamp | Creation timestamp |
| event_type | String | Event type identifier |
| event_data | JSONB | Event data payload |

### CustomAgent

Stores custom agent configurations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Agent name |
| description | Text | Agent description |
| created_at | Timestamp | Creation timestamp |
| updated_at | Timestamp | Last update timestamp |
| metadata | JSONB | Additional metadata |
| configuration | JSONB | Agent configuration |

### AgentComponent

Manages agent components.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| agent_id | UUID | Foreign key to CustomAgent |
| component_type | String | Component type |
| configuration | JSONB | Component configuration |
| metadata | JSONB | Additional metadata |

### ComponentConnection

Tracks connections between components.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| source_component_id | UUID | Foreign key to source AgentComponent |
| target_component_id | UUID | Foreign key to target AgentComponent |
| connection_type | String | Connection type |
| metadata | JSONB | Additional metadata |

### ComponentTemplate

Stores component templates.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Template name |
| description | Text | Template description |
| component_type | String | Component type |
| configuration_schema | JSONB | Configuration schema |
| default_configuration | JSONB | Default configuration |

### AgentTemplate

Manages agent templates.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Template name |
| description | Text | Template description |
| components | JSONB | Template components |
| connections | JSONB | Template connections |
| metadata | JSONB | Additional metadata |

## Relationships

- A Conversation has many Messages (one-to-many)
- A TelemetrySession has many TelemetryEvents (one-to-many)
- A CustomAgent has many AgentComponents (one-to-many)
- AgentComponents are connected through ComponentConnections (many-to-many)

## Migrations

Database migrations are handled through SQLAlchemy's AsyncEngine during application startup. The tables are created automatically if they don't exist.