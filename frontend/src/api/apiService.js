import axios from 'axios';

// API base URL
const API_BASE_URL = '/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Handle response
const handleResponse = (response) => {
  if (response.status >= 200 && response.status < 300) {
    return response.data;
  }
  
  throw new Error(response.data?.error || 'Unknown error occurred');
};

// Handle error
const handleError = (error) => {
  if (error.response) {
    // Server responded with error status
    const errorMessage = error.response.data?.error || `Server error: ${error.response.status}`;
    console.error('API error:', errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  } else if (error.request) {
    // Request made but no response received
    console.error('API error: No response received', error.request);
    return {
      success: false,
      error: 'No response from server. Please check your connection.'
    };
  } else {
    // Error setting up request
    console.error('API request error:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
};

// Chat service
export const chatService = {
  // Send a message
  sendMessage: async (message, sessionId, context = null) => {
    try {
      const response = await apiClient.post('/chat/messages', {
        message,
        session_id: sessionId,
        context
      });
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  },
  
  // Get chat history
  getChatHistory: async (sessionId, limit = 50) => {
    try {
      const response = await apiClient.get(`/chat/history/${sessionId}?limit=${limit}`);
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  }
};

// Agent service
export const agentService = {
  // List available agents
  listAgents: async () => {
    try {
      const response = await apiClient.get('/agents');
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  }
};

// Telemetry service
export const telemetryService = {
  // Get telemetry sessions
  getSessions: async (limit = 20, offset = 0, days = 7) => {
    try {
      const response = await apiClient.get(`/telemetry/sessions?limit=${limit}&offset=${offset}&days=${days}`);
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  },
  
  // Get events for a session
  getSessionEvents: async (sessionId) => {
    try {
      const response = await apiClient.get(`/telemetry/sessions/${sessionId}/events`);
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  }
};

// Health service
export const healthService = {
  // Get system status
  getStatus: async () => {
    try {
      const response = await apiClient.get('/health');
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  }
};

// Statistics service
export const statsService = {
  // Get system statistics
  getStats: async (days = 7) => {
    try {
      const response = await apiClient.get(`/stats?days=${days}`);
      return handleResponse(response);
    } catch (error) {
      return handleError(error);
    }
  }
};