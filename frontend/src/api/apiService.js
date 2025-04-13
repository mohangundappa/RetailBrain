import axios from 'axios';

// API base URL - easily configurable for different environments
const API_BASE_URL = '/api/v1';

// Configurable request timeout
const REQUEST_TIMEOUT = 30000; // 30 seconds

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Add request interceptor for authentication, logging, etc.
apiClient.interceptors.request.use(
  (config) => {
    // Add request timestamp for performance tracking
    config.metadata = { startTime: new Date() };
    
    // Could add auth token here
    // if (localStorage.getItem('authToken')) {
    //   config.headers.Authorization = `Bearer ${localStorage.getItem('authToken')}`;
    // }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for global error handling, analytics, etc.
apiClient.interceptors.response.use(
  (response) => {
    // Calculate request duration for analytics
    const requestDuration = new Date() - response.config.metadata.startTime;
    console.debug(`API call to ${response.config.url} took ${requestDuration}ms`);
    
    return response;
  },
  (error) => {
    // Calculate duration even for errors
    if (error.config && error.config.metadata) {
      const requestDuration = new Date() - error.config.metadata.startTime;
      console.debug(`Failed API call to ${error.config.url} took ${requestDuration}ms`);
    }
    
    // Handle specific error cases here (authentication errors, etc.)
    if (error.response && error.response.status === 401) {
      // Handle authentication errors
      console.error('Authentication error:', error.response.data);
      // Could dispatch auth error action or redirect to login
    }
    
    return Promise.reject(error);
  }
);

// Handle successful response
const handleResponse = (response) => {
  if (response.status >= 200 && response.status < 300) {
    return response.data;
  }
  
  throw new Error(response.data?.error || 'Unknown error occurred');
};

// Handle error response
const handleError = (error) => {
  if (error.response) {
    // Server responded with error status
    const errorMessage = error.response.data?.error || `Server error: ${error.response.status}`;
    console.error('API error:', errorMessage);
    return {
      success: false,
      error: errorMessage,
      status: error.response.status
    };
  } else if (error.request) {
    // Request made but no response received
    console.error('API error: No response received', error.request);
    return {
      success: false,
      error: 'No response from server. Please check your connection.',
      status: 0
    };
  } else {
    // Error setting up request
    console.error('API request error:', error.message);
    return {
      success: false,
      error: error.message,
      status: 0
    };
  }
};

// Helper method for making API calls with consistent error handling
const apiCall = async (method, endpoint, data = null, params = null) => {
  try {
    const config = {
      method,
      url: endpoint
    };
    
    if (data) config.data = data;
    if (params) config.params = params;
    
    const response = await apiClient(config);
    return handleResponse(response);
  } catch (error) {
    return handleError(error);
  }
};

// Chat service - for user interactions with agents
export const chatService = {
  // Start a new chat session
  startSession: async (agentId = null) => {
    return apiCall('post', '/chat/sessions', { agent_id: agentId });
  },
  
  // Send a message in a chat session
  sendMessage: async (message, sessionId, context = null) => {
    return apiCall('post', '/chat/messages', {
      message,
      session_id: sessionId,
      context
    });
  },
  
  // Get chat history for a session
  getChatHistory: async (sessionId, limit = 50) => {
    return apiCall('get', `/chat/history/${sessionId}`, null, { limit });
  },
  
  // Get active chat sessions
  getActiveSessions: async () => {
    return apiCall('get', '/chat/sessions');
  },
  
  // End a chat session
  endSession: async (sessionId) => {
    return apiCall('delete', `/chat/sessions/${sessionId}`);
  }
};

// Agent service - for managing and interacting with agents
export const agentService = {
  // List all available agents
  listAgents: async (includeDetails = true) => {
    return apiCall('get', '/agents', null, { details: includeDetails });
  },
  
  // Get details for a specific agent
  getAgentDetails: async (agentId) => {
    return apiCall('get', `/agents/${agentId}`);
  },
  
  // Get agent capabilities/schema
  getAgentCapabilities: async (agentId) => {
    return apiCall('get', `/agents/${agentId}/capabilities`);
  },
  
  // For agent builder/management
  createAgent: async (agentData) => {
    return apiCall('post', '/agents', agentData);
  },
  
  updateAgent: async (agentId, agentData) => {
    return apiCall('put', `/agents/${agentId}`, agentData);
  },
  
  deleteAgent: async (agentId) => {
    return apiCall('delete', `/agents/${agentId}`);
  }
};

// Telemetry service - for observability and analytics
export const telemetryService = {
  // Get all telemetry sessions with pagination
  getSessions: async (limit = 20, offset = 0, days = 7) => {
    return apiCall('get', '/telemetry/sessions', null, { limit, offset, days });
  },
  
  // Get events for a specific session
  getSessionEvents: async (sessionId) => {
    return apiCall('get', `/telemetry/sessions/${sessionId}/events`);
  },
  
  // Get system-wide metrics
  getMetrics: async (timeframe = 'day') => {
    return apiCall('get', '/telemetry/metrics', null, { timeframe });
  },
  
  // Get agent performance metrics
  getAgentMetrics: async (agentId, timeframe = 'day') => {
    return apiCall('get', `/telemetry/agents/${agentId}/metrics`, null, { timeframe });
  },
  
  // Log custom event (for frontend analytics)
  logEvent: async (eventData) => {
    return apiCall('post', '/telemetry/events', eventData);
  }
};

// Health service - for system status and diagnostics
export const healthService = {
  // Get overall system health status
  getStatus: async () => {
    return apiCall('get', '/health');
  },
  
  // Get detailed component status
  getComponentStatus: async (component) => {
    return apiCall('get', `/health/${component}`);
  },
  
  // Run system diagnostics
  runDiagnostics: async () => {
    return apiCall('post', '/health/diagnostics');
  }
};

// Statistics service - for reporting and dashboards
export const statsService = {
  // Get system-wide statistics
  getStats: async (days = 7) => {
    return apiCall('get', '/stats', null, { days });
  },
  
  // Get usage statistics
  getUsageStats: async (timeframe = 'week') => {
    return apiCall('get', '/stats/usage', null, { timeframe });
  },
  
  // Get agent usage statistics
  getAgentStats: async (agentId, timeframe = 'week') => {
    return apiCall('get', `/stats/agents/${agentId}`, null, { timeframe });
  },
  
  // Get performance statistics
  getPerformanceStats: async (timeframe = 'day') => {
    return apiCall('get', '/stats/performance', null, { timeframe });
  }
};

// Memory service - for managing conversation memory
export const memoryService = {
  // Get memory for a specific conversation
  getMemory: async (conversationId) => {
    return apiCall('get', `/memory/${conversationId}`);
  },
  
  // Search memory for specific content
  searchMemory: async (query, conversationId = null) => {
    const params = { query };
    if (conversationId) params.conversation_id = conversationId;
    
    return apiCall('get', '/memory/search', null, params);
  },
  
  // Clear memory for a specific conversation
  clearMemory: async (conversationId) => {
    return apiCall('delete', `/memory/${conversationId}`);
  }
};

// Configuration service - for system settings
export const configService = {
  // Get system configuration
  getConfig: async () => {
    return apiCall('get', '/config');
  },
  
  // Update system configuration
  updateConfig: async (configData) => {
    return apiCall('patch', '/config', configData);
  },
  
  // Reset configuration to defaults
  resetConfig: async () => {
    return apiCall('post', '/config/reset');
  }
};