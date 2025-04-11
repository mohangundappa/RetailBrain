# Routing

## Overview

This document describes the routing approach used in the Staples Brain frontend.

## Route Structure

The frontend uses a hierarchical routing structure with the following main routes:

### Public Routes

- `/`: Home page / Landing page
- `/login`: Authentication page
- `/about`: Information about the system

### Authenticated Routes

- `/chat`: Main chat interface
- `/chat/:sessionId`: Specific chat session
- `/history`: Conversation history
- `/profile`: User profile settings

### Admin Routes

- `/admin`: Admin dashboard
- `/admin/telemetry`: Telemetry dashboard
- `/admin/agents`: Agent management
- `/admin/users`: User management
- `/admin/system`: System settings

## Route Guards

Routes are protected using authentication guards:

1. **Public Routes**: Accessible to all users
2. **Authenticated Routes**: Require user login
3. **Admin Routes**: Require admin privileges

## Navigation

Navigation between routes is handled through:

1. **Main Navigation**: Primary navigation component
2. **Breadcrumbs**: Hierarchical navigation within sections
3. **Direct Links**: Within content and components

## Route Parameters

Routes can include parameters for dynamic content:

- `:sessionId`: Chat session identifier
- `:userId`: User identifier
- `:agentId`: Agent identifier

## Route Transitions

Page transitions use animations to provide a smooth user experience:

- Fade transitions between main routes
- Slide transitions for nested routes
- No transition for error states

## Error Handling

1. **404 Not Found**: Custom page for invalid routes
2. **403 Forbidden**: Custom page for unauthorized access
3. **Fallback Route**: Catches all unmatched routes

## Implementation

The routing system is implemented using:

1. **Router Library**: React Router or similar
2. **Route Configuration**: Centralized route definition
3. **Route Components**: Components specific to each route
4. **Layout Components**: Shared layouts for route groups