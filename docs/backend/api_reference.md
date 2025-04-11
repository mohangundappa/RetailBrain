# API Reference

## Overview

This document provides a reference for the Staples Brain API endpoints, request/response formats, and authentication methods.

## Base URL

All API requests should be prefixed with: `/api/v1`

## Authentication

*To be documented*

## Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API, including a list of available agents.

### Agents

```
GET /agents
```

Returns a list of available agents in the system.

### Telemetry

```
GET /telemetry/sessions
```

Returns a list of telemetry sessions.

```
GET /telemetry/sessions/{session_id}/events
```

Returns events for a specific telemetry session.

### System Stats

```
GET /system/stats
```

Returns system statistics.

## Interactive Documentation

For a complete and interactive API reference, visit the `/docs` endpoint when the application is running.