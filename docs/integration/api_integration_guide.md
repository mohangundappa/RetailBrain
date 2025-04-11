# API Integration Guide

## Overview

This guide explains how to integrate frontend applications with the Staples Brain backend API.

## Authentication

*To be documented*

## Base URL

All API requests should be prefixed with: `/api/v1`

## Common Request Patterns

### Starting a Conversation

1. Make a POST request to `/api/v1/chat/session` to create a new session
2. Receive a session ID in the response
3. Use this session ID for all subsequent messages

### Sending Messages

1. Make a POST request to `/api/v1/chat/message` with:
   - Session ID
   - Message content
   - Any relevant metadata
2. Receive a response with the agent's reply

### Retrieving Conversation History

1. Make a GET request to `/api/v1/chat/sessions/{session_id}/messages`
2. Receive a list of messages in the conversation

## API Response Format

All API responses follow a standard format:

```json
{
  "success": true,
  "data": { ... },
  "metadata": { ... },
  "error": null
}
```

- `success`: Boolean indicating if the request was successful
- `data`: Response data (varies by endpoint)
- `metadata`: Additional metadata (optional)
- `error`: Error message if applicable (null if successful)

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad request
- 401: Unauthorized
- 404: Not found
- 500: Server error

## Rate Limiting

*To be documented*

## Examples

### Example: Sending a Message

```javascript
// Example frontend code for sending a message
async function sendMessage(sessionId, message) {
  const response = await fetch('/api/v1/chat/message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      content: message,
    }),
  });
  
  return await response.json();
}
```