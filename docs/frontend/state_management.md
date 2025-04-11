# State Management

## Overview

This document describes the state management approach used in the Staples Brain frontend.

## State Management Architecture

The frontend uses a centralized state management approach with the following key components:

1. **Store**: Central repository for application state
2. **Actions**: Events that trigger state changes
3. **Reducers**: Functions that apply state changes
4. **Selectors**: Functions that extract specific parts of the state

## Key State Slices

The application state is divided into the following main slices:

### Authentication State

Manages user authentication status and related data:

- Current user information
- Authentication tokens
- Permission levels

### Conversation State

Manages the current conversation and message history:

- Active conversation ID
- Message history
- Current message draft
- Typing indicators

### Agent State

Manages information about available agents:

- List of available agents
- Currently selected agent
- Agent capabilities and metadata

### UI State

Manages UI-specific state:

- Active UI mode (chat, admin, settings)
- Theme settings
- Layout preferences
- Modal visibility

## State Flow

1. User interaction triggers an action
2. Action is dispatched to the store
3. Reducers process the action and update state
4. Components re-render based on state changes
5. Side effects (API calls, etc.) are triggered by middleware

## Best Practices

- Keep state normalized (avoid duplication)
- Use selectors for derived state
- Handle side effects consistently
- Keep UI and domain state separate
- Use immutable update patterns