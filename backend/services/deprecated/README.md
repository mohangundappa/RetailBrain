# Deprecated Brain Services

This directory contains deprecated brain service implementations that have been replaced by `GraphBrainService`.

## History

- `brain_service.py`: The original brain service implementation using a traditional approach.
- `langgraph_brain_service.py`: An intermediate implementation adding LangGraph support.
- `hybrid_brain_service.py`: Another intermediate implementation with hybrid capabilities.

## Current Implementation

All of these implementations have been consolidated into the `GraphBrainService` class which:

1. Uses native LangGraph for orchestration
2. Provides improved error handling and recovery
3. Includes state persistence for better reliability
4. Offers better type safety and architecture

## Why Deprecated?

These files are kept for reference and historical purposes but should not be used in new code. All code should use `GraphBrainService` instead.