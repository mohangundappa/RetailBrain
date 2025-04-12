#!/bin/bash

# Create a unique session ID using date and random number
SESSION_ID="test-session-$(date +%s)-$RANDOM"
echo "Using session ID: $SESSION_ID"

# Base URL for API
BASE_URL="http://localhost:5000/api/v1"
ORIGINAL_CHAT_URL="$BASE_URL/chat"
OPTIMIZED_CHAT_URL="$BASE_URL/optimized/chat"

# Password reset query
QUERY="I forgot my password and need to reset it"

echo -e "\n=== Testing Original Route ==="
echo "Request: POST $ORIGINAL_CHAT_URL"
echo "Payload: {\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

curl -s -X POST $ORIGINAL_CHAT_URL \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

echo -e "\n\n=== Testing Optimized Route ==="
echo "Request: POST $OPTIMIZED_CHAT_URL"
echo "Payload: {\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

curl -s -X POST $OPTIMIZED_CHAT_URL \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

echo -e "\n"