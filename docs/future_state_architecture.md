# Staples Brain: Future State Architecture with Cross-Department Context Sharing

## Overview Diagram
```
┌───────────────────────────────────────────────────────────────────────────┐
│                           CUSTOMER TOUCHPOINTS                            │
│                                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Staples.com │  │  Advantage  │  │    Quill    │  │    Other    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                             API GATEWAY LAYER                             │
└───────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         ENTERPRISE ORCHESTRATION                          │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     Enterprise Context Manager                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    ▲                                       │
│                                    │                                       │
│               ┌───────────────────┼───────────────────┐                   │
│               │                   │                   │                   │
│               ▼                   ▼                   ▼                   │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐  │
│  │    Sales Domain     │ │  Customer Service   │ │   Other Domains     │  │
│  │  Orchestration      │ │  Orchestration      │ │   Orchestration     │  │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                 ▲                  ▲                  ▲
                 │                  │                  │
                 ▼                  ▼                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED CUSTOMER CONTEXT REPOSITORY                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                Customer Interaction Context Store                   │  │
│  │                                                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │   Product   │  │  Preference │  │ Interaction │  │ Department  │ │  │
│  │  │   Context   │  │    Context  │  │   History   │  │   Handoffs  │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                 ▲                  ▲                  ▲
                 │                  │                  │
                 ▼                  ▼                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          AGENT ORCHESTRATION LAYER                        │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Context-Aware Agent Router                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    ▲                                       │
│                                    │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        LangGraph Orchestrator                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                            SPECIALIZED AGENTS                             │
│                                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │    Order    │  │   Account   │  │    Store    │  │    Other    │      │
│  │   Tracking  │  │  Management │  │   Locator   │  │    Agents   │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
```

## Customer Journey Flow Diagram

Here's how a customer interaction would flow across departments:

```
┌─────────────────────────────────┐
│       INITIAL INTERACTION       │
│ Customer contacts Sales Dept    │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│      SALES ORCHESTRATION        │
│ Process request with Sales      │
│ domain knowledge                │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│      CONTEXT CAPTURE            │
│ Capture Sales interaction       │
│ context with customer ID        │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│    CONTEXT REPOSITORY STORAGE   │
│ Store in Unified Customer       │
│ Context Repository             │
└─────────────────────────────────┘

          ... Later ...

┌─────────────────────────────────┐
│     SUBSEQUENT INTERACTION      │
│ Same customer contacts          │
│ Customer Service                │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│     CUSTOMER IDENTIFICATION     │
│ Identify customer and retrieve  │
│ cross-department context        │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  CUSTOMER SERVICE ORCHESTRATION │
│ Enrich request with Sales       │
│ context before processing       │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│     CONTEXT-AWARE RESPONSE      │
│ Respond with awareness of       │
│ previous Sales interaction      │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│    UPDATED CONTEXT STORAGE      │
│ Store Customer Service context  │
│ for future department use       │
└─────────────────────────────────┘
```

## Unified Customer Context Repository Design

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       CUSTOMER_CONTEXT Table                              │
├───────────────┬───────────────────────────────────────────────────────────┤
│ customer_id   │ Unique identifier for the customer                        │
├───────────────┼───────────────────────────────────────────────────────────┤
│ context_id    │ Unique identifier for this context entry                  │
├───────────────┼───────────────────────────────────────────────────────────┤
│ timestamp     │ When this context was captured                            │
├───────────────┼───────────────────────────────────────────────────────────┤
│ department    │ The department that captured this context                 │
├───────────────┼───────────────────────────────────────────────────────────┤
│ session_id    │ Session identifier for this interaction                   │
├───────────────┼───────────────────────────────────────────────────────────┤
│ agent_id      │ Agent that processed this interaction                     │
├───────────────┼───────────────────────────────────────────────────────────┤
│ context_data  │ JSON structure containing:                               │
│               │  - products_discussed                                     │
│               │  - detected_intents                                       │
│               │  - customer_preferences                                   │
│               │  - issues_raised                                          │
│               │  - interaction_summary                                    │
├───────────────┼───────────────────────────────────────────────────────────┤
│ expire_at     │ When this context should expire (privacy)                 │
└───────────────┴───────────────────────────────────────────────────────────┘
```

## Cross-Department Context Manager Component

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       CrossDepartmentContextManager                       │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────┐       │
│  │ enrich_request_with_cross_dept_context(request, customer_id, dept)    │
│  │                                                               │       │
│  │  1. Retrieve relevant prior contexts                          │       │
│  │  2. Extract insights from prior contexts                      │       │
│  │  3. Add context metadata to request                           │       │
│  │  4. Return enriched request                                   │       │
│  └───────────────────────────────────────────────────────────────┘       │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────┐       │
│  │ capture_department_context(customer_id, dept, interaction_data)       │
│  │                                                               │       │
│  │  1. Extract key insights from interaction                     │       │
│  │  2. Format context with metadata                              │       │
│  │  3. Store in context repository                               │       │
│  │  4. Publish context update event                              │       │
│  └───────────────────────────────────────────────────────────────┘       │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────┐       │
│  │ generate_context_summary(customer_id, target_department)      │       │
│  │                                                               │       │
│  │  1. Retrieve all department contexts for customer             │       │
│  │  2. Generate cross-department summary                         │       │
│  │  3. Highlight key insights for target department              │       │
│  └───────────────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
```

## Enhanced OrchestrationEngine (Integration Point)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         Enhanced OrchestrationEngine                      │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  - Integrates Cross-Department Context Manager                            │
│  - Adds enhanced process_request() method with customer_id and department │
│  - Provides cross-department context utilities                            │
│  - Maintains backward compatibility with existing implementation          │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Implementation Architecture

The diagram below shows implementation layers and components:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      APPLICATION SERVICES                              │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    API      │  │  Customer   │  │  Session    │  │ Analytics   │    │
│  │  Gateway    │  │   Service   │  │  Manager    │  │  Service    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    OrchestrationEngine                          │   │
│  │                                                                 │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │   Domain      │  │ Cross-Dept    │  │   State       │       │   │
│  │  │  Routing      │  │ Context Mgr   │  │  Persistence  │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENT FRAMEWORK LAYER                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   LangGraphOrchestrator                         │   │
│  │                                                                 │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │    Agent      │  │    Context    │  │   Response    │       │   │
│  │  │  Selection    │  │   Awareness   │  │  Generation   │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                     │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Customer   │  │  Context    │  │   Agent     │  │ Telemetry   │    │
│  │  Database   │  │ Repository  │  │ Repository  │  │  Database   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```
