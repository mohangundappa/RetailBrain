import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    // Handle specific error cases (like 401 unauthorized)
    if (error.response && error.response.status === 401) {
      // Clear local storage and redirect to login page if needed
      localStorage.removeItem('authToken');
      // Use window.location or router to redirect
    }
    return Promise.reject(error);
  }
);

// API service functions
const apiService = {
  // Agent endpoints
  async getAgents() {
    console.log('Making API call to /agents endpoint');
    const response = await api.get('/agents', {
      params: { t: new Date().getTime() } // Add cache buster
    });
    console.log('Response received from /agents:', response.data);
    return response.data;
  },

  async getAgentDetails(agentId) {
    const response = await api.get(`/agents/${agentId}`);
    return response.data;
  },

  // Chat endpoints
  async startConversation() {
    const response = await api.post('/chat/conversations');
    return response.data;
  },

  async sendMessage(conversationId, message) {
    const response = await api.post(`/chat/conversations/${conversationId}/messages`, {
      content: message,
    });
    return response.data;
  },

  async getConversationHistory(conversationId) {
    const response = await api.get(`/chat/conversations/${conversationId}/messages`);
    return response.data;
  },

  async getConversations() {
    const response = await api.get('/chat/conversations');
    return response.data;
  },

  // Telemetry endpoints
  async getTelemetry(timeRange = '24h') {
    const response = await api.get(`/telemetry?timeRange=${timeRange}`);
    return response.data;
  },

  // Error handling wrapper
  async apiCall(apiFunction, ...args) {
    try {
      return await apiFunction(...args);
    } catch (error) {
      console.error('API Error:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        const errorData = error.response.data.error || 'Server error occurred';
        throw new Error(errorData);
      } else if (error.request) {
        // The request was made but no response was received
        throw new Error('No response from server. Please try again later.');
      } else {
        // Something happened in setting up the request that triggered an Error
        throw error;
      }
    }
  }
};

export default apiService;