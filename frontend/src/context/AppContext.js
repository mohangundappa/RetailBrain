import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { chatService, healthService } from '../api/apiService';

// Create context
const AppContext = createContext();

// Custom hook for using the context
export const useAppContext = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  // Chat state
  const [chatState, setChatState] = useState({
    messages: [],
    sessionId: localStorage.getItem('sessionId') || null,
    isLoading: false,
    error: null
  });
  
  // System status state
  const [systemStatus, setSystemStatus] = useState({
    isLoading: true,
    isHealthy: true,
    data: null,
    error: null
  });
  
  // Fetch system status on initial load
  useEffect(() => {
    fetchSystemStatus();
    
    // Poll system status every 60 seconds
    const intervalId = setInterval(fetchSystemStatus, 60000);
    
    return () => {
      clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Load conversation history if session ID exists
  useEffect(() => {
    if (chatState.sessionId) {
      loadConversationHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatState.sessionId]);
  
  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await healthService.getStatus();
      
      if (response.success) {
        setSystemStatus({
          isLoading: false,
          isHealthy: response.data.health === 'healthy',
          data: response.data,
          error: null
        });
      } else {
        throw new Error(response.error || 'Failed to fetch system status');
      }
    } catch (error) {
      console.error('Error fetching system status:', error);
      setSystemStatus({
        isLoading: false,
        isHealthy: false,
        data: null,
        error: error.message
      });
    }
  };
  
  // Load conversation history
  const loadConversationHistory = useCallback(async () => {
    if (!chatState.sessionId) return;
    
    setChatState((prev) => ({
      ...prev,
      isLoading: true,
      error: null
    }));
    
    try {
      const response = await chatService.getChatHistory(chatState.sessionId);
      
      if (response.success && response.data.messages) {
        setChatState((prev) => ({
          ...prev,
          messages: response.data.messages,
          isLoading: false
        }));
      } else {
        throw new Error(response.error || 'Failed to load conversation history');
      }
    } catch (error) {
      console.error('Error loading conversation history:', error);
      setChatState((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message
      }));
    }
  }, [chatState.sessionId]);
  
  // Start new conversation
  const startNewConversation = () => {
    const newSessionId = uuidv4();
    localStorage.setItem('sessionId', newSessionId);
    
    setChatState({
      messages: [],
      sessionId: newSessionId,
      isLoading: false,
      error: null
    });
  };
  
  // Send message
  const sendMessage = async (message) => {
    // Create temporary sessionId if none exists
    const sessionId = chatState.sessionId || uuidv4();
    
    if (!chatState.sessionId) {
      localStorage.setItem('sessionId', sessionId);
      setChatState((prev) => ({
        ...prev,
        sessionId
      }));
    }
    
    // Add user message to state immediately
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    
    setChatState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null
    }));
    
    // Send message to API
    try {
      const response = await chatService.sendMessage(message, sessionId);
      
      if (response.success && response.data) {
        // Add assistant message to state
        const assistantMessage = {
          id: uuidv4(),
          role: 'assistant',
          content: response.data.response,
          metadata: response.data.metadata || null,
          timestamp: new Date().toISOString()
        };
        
        setChatState((prev) => ({
          ...prev,
          messages: [...prev.messages, assistantMessage],
          isLoading: false
        }));
      } else {
        throw new Error(response.error || 'Failed to process message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to chat
      const errorMessage = {
        id: uuidv4(),
        role: 'system',
        content: `Error: ${error.message}. Please try again.`,
        timestamp: new Date().toISOString()
      };
      
      setChatState((prev) => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
        isLoading: false,
        error: error.message
      }));
    }
  };
  
  // Context value to be provided to consumers
  const contextValue = {
    chatState,
    systemStatus,
    loadConversationHistory,
    startNewConversation,
    sendMessage
  };
  
  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};