/**
 * @typedef {Object} Agent
 * @property {string} id - Unique identifier for the agent
 * @property {string} name - Display name of the agent
 * @property {string} [description] - Optional description of the agent
 * @property {string} [status] - Current status of the agent (active, inactive, etc.)
 * @property {string} [type] - Type of agent
 * @property {string} [version] - Version of the agent
 * @property {string} [created_at] - Creation timestamp
 * @property {boolean} [is_system] - Whether this is a system agent
 * @property {string} [source] - Data source for the agent
 * @property {boolean} [db_driven] - Whether this agent is database-driven
 * @property {boolean} [loaded] - Whether this agent is loaded
 */

/**
 * @typedef {Object} ChatMessage
 * @property {string} id - Unique message identifier
 * @property {string} content - Message content
 * @property {'user'|'system'|'agent'} role - Role of message sender
 * @property {string} timestamp - ISO timestamp when message was sent
 * @property {Object} [metadata] - Additional message metadata
 * @property {string} [agent_id] - ID of the agent that generated the message
 * @property {string} [session_id] - Chat session ID
 */

/**
 * @typedef {Object} ChatSession
 * @property {string} id - Unique session identifier
 * @property {string} [agent_id] - ID of the agent assigned to this session
 * @property {string} created_at - ISO timestamp when session was created
 * @property {string} [updated_at] - ISO timestamp when session was last updated
 * @property {string} [status] - Current status of the session
 */

/**
 * @typedef {Object} TelemetryEvent
 * @property {string} id - Event identifier
 * @property {string} type - Event type
 * @property {string} session_id - Session the event belongs to
 * @property {Object} data - Event data
 * @property {string} timestamp - When the event occurred
 */

/**
 * @typedef {Object} TelemetrySession
 * @property {string} id - Session identifier
 * @property {string} user_id - User who initiated the session
 * @property {string} start_time - When the session started
 * @property {string} [end_time] - When the session ended
 * @property {Object} metadata - Session metadata
 */

/**
 * @typedef {Object} SystemStatus
 * @property {boolean} isHealthy - Whether the system is healthy
 * @property {Object} metrics - System metrics
 * @property {string} [version] - System version
 * @property {Object} [components] - Status of individual components
 */

/**
 * @typedef {Object} User
 * @property {string} id - User identifier
 * @property {string} username - Username
 * @property {string} [email] - User email
 * @property {Object} [preferences] - User preferences
 * @property {string} [role] - User role
 */

/**
 * @typedef {Object} Notification
 * @property {string} id - Notification identifier
 * @property {string} title - Notification title
 * @property {string} message - Notification message
 * @property {'success'|'error'|'warning'|'info'} type - Notification type
 * @property {boolean} [autoDismiss] - Whether to auto-dismiss the notification
 * @property {number} [timestamp] - When the notification was created
 */

/**
 * @typedef {Object} ApiResponse
 * @property {boolean} success - Whether the request was successful
 * @property {Object} [data] - Response data
 * @property {Object} [metadata] - Response metadata
 * @property {string} [error] - Error message if applicable
 */

/**
 * @typedef {Object} MemoryEntry
 * @property {string} id - Memory entry identifier
 * @property {string} key - Memory key
 * @property {Object|string} value - Memory value
 * @property {string} [namespace] - Memory namespace
 * @property {string} [expires_at] - When the memory expires
 */

/**
 * @typedef {Object} AgentObservability
 * @property {string} agent_id - Agent identifier
 * @property {string} conversation_id - Conversation identifier
 * @property {Object} input - User input data
 * @property {Object} reasoning - Agent reasoning process
 * @property {Object} output - Agent output/response
 * @property {Array<Object>} steps - Reasoning steps
 * @property {Object} entities - Extracted entities
 * @property {Object} metrics - Performance metrics
 */