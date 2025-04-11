import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding tokens, etc.
api.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed in the future
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle generic errors here
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Health check
const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

// Chat API endpoints
const chatService = {
  // Send a message to the brain
  sendMessage: async (message, sessionId = null, context = null) => {
    try {
      const payload = {
        message,
        session_id: sessionId,
        context: context || undefined,
      };
      
      const response = await api.post('/chat/messages', payload);
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },
  
  // Get conversation history
  getHistory: async (sessionId, limit = 10) => {
    try {
      const response = await api.get(`/chat/history/${sessionId}?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('Error getting chat history:', error);
      throw error;
    }
  }
};

// Agent API endpoints
const agentService = {
  // List available agents
  listAgents: async () => {
    try {
      const response = await api.get('/agents');
      return response.data;
    } catch (error) {
      console.error('Error listing agents:', error);
      throw error;
    }
  }
};

// Telemetry API endpoints
const telemetryService = {
  // Get telemetry sessions
  getSessions: async (limit = 20, offset = 0, days = 7) => {
    try {
      const response = await api.get(
        `/telemetry/sessions?limit=${limit}&offset=${offset}&days=${days}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting telemetry sessions:', error);
      throw error;
    }
  },
  
  // Get events for a session
  getSessionEvents: async (sessionId) => {
    try {
      const response = await api.get(`/telemetry/sessions/${sessionId}/events`);
      return response.data;
    } catch (error) {
      console.error('Error getting session events:', error);
      throw error;
    }
  }
};

// Stats API endpoints
const statsService = {
  // Get system statistics
  getStats: async (days = 7) => {
    try {
      const response = await api.get(`/stats?days=${days}`);
      return response.data;
    } catch (error) {
      console.error('Error getting system stats:', error);
      throw error;
    }
  }
};

export { api, checkHealth, chatService, agentService, telemetryService, statsService };