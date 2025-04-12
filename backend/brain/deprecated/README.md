# Deprecated Orchestration Components

This directory contains deprecated orchestration components that have been replaced by the native LangGraph implementation in `backend/brain/native_graph/`.

## History

- `orchestrator.py`: The original orchestrator implementation using a traditional approach.
- `conversation_flow_handlers.py`: Handlers for managing conversation flow.

## Current Implementation

These implementations have been replaced by the more robust and flexible architecture in `backend/brain/native_graph/` which:

1. Uses native LangGraph for orchestration
2. Provides improved error handling and recovery
3. Includes state persistence for better reliability
4. Offers clearer separation of concerns
5. Supports more complex agent selection and routing

## Why Deprecated?

These files are kept for reference and historical purposes but should not be used in new code. All code should use the native LangGraph implementation instead.