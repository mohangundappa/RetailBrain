#!/bin/bash

# Create a unique session ID
SESSION_ID=$(uuidgen)
echo "Using session ID: $SESSION_ID"

# Base URL for API
BASE_URL="http://localhost:8000/api/v1"
ORIGINAL_CHAT_URL="$BASE_URL/chat"
OPTIMIZED_CHAT_URL="$BASE_URL/optimized/chat"

# Password reset query
QUERY="I forgot my password and need to reset it"

echo -e "\n=== Testing Original Route ==="
echo "Request: POST $ORIGINAL_CHAT_URL"
echo "Payload: {\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

curl -s -X POST $ORIGINAL_CHAT_URL \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}" | jq

echo -e "\n=== Testing Optimized Route ==="
echo "Request: POST $OPTIMIZED_CHAT_URL"
echo "Payload: {\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}"

curl -s -X POST $OPTIMIZED_CHAT_URL \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}" | jq

echo -e "\n=== Testing with different password reset phrasings ==="

QUERIES=(
  "How do I reset my password?"
  "I can't log in to my account"
  "I need a new password for my Staples account"
  "Reset password please"
  "Forgot my login credentials"
)

for QUERY in "${QUERIES[@]}"; do
  echo -e "\n--- Query: \"$QUERY\" ---"
  
  # Create a new session ID for each query
  SESSION_ID=$(uuidgen)
  
  echo "Optimized Route:"
  curl -s -X POST $OPTIMIZED_CHAT_URL \
       -H "Content-Type: application/json" \
       -d "{\"message\": \"$QUERY\", \"session_id\": \"$SESSION_ID\"}" | jq '.agent, .confidence, .metadata.selection_time'
done

echo -e "\n=== Completed Tests ==="