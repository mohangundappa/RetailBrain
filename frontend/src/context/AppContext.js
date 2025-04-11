import React, { createContext, useState, useEffect, useContext } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { checkHealth, chatService } from '../api/apiService';

// Create context
const AppContext = createContext();

// Custom hook for using the context
export const useAppContext = () => useContext(AppContext);

// Provider component
export const AppProvider = ({ children }) => {
  // System state
  const [systemStatus, setSystemStatus] = useState({
    isLoading: true,
    isHealthy: false,
    error: null,
    data: {}
  });

  // Chat state
  const [chatState, setChatState] = useState({
    messages: [],
    isLoading: false,
    error: null,
    sessionId: localStorage.getItem('sessionId') || null
  });

  // Initialize session ID if not exists
  useEffect(() => {
    if (!chatState.sessionId) {
      const newSessionId = uuidv4();
      localStorage.setItem('sessionId', newSessionId);
      setChatState(prevState => ({
        ...prevState,
        sessionId: newSessionId
      }));
    }
  }, [chatState.sessionId]);

  // Check system health when component mounts
  useEffect(() => {
    const checkSystemHealth = async () => {
      try {
        const response = await checkHealth();
        setSystemStatus({
          isLoading: false,
          isHealthy: response.success,
          error: null,
          data: response.data
        });
      } catch (error) {
        setSystemStatus({
          isLoading: false,
          isHealthy: false,
          error: error.message,
          data: {}
        });
      }
    };

    checkSystemHealth();
  }, []);

  // Function to send a message
  const sendMessage = async (message) => {
    if (!message.trim()) return;

    setChatState(prevState => ({
      ...prevState,
      isLoading: true,
      error: null
    }));

    // Add user message to UI immediately
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setChatState(prevState => ({
      ...prevState,
      messages: [...prevState.messages, userMessage]
    }));

    try {
      // Send to API
      const response = await chatService.sendMessage(
        message, 
        chatState.sessionId
      );

      if (response.success) {
        // Add assistant response to UI
        const assistantMessage = {
          id: uuidv4(),
          role: 'assistant',
          content: response.data.message,
          metadata: {
            agent: response.data.agent,
            confidence: response.data.confidence
          },
          timestamp: new Date().toISOString()
        };

        setChatState(prevState => ({
          ...prevState,
          messages: [...prevState.messages, assistantMessage],
          isLoading: false
        }));
      } else {
        throw new Error(response.error || 'Unknown error occurred');
      }
    } catch (error) {
      setChatState(prevState => ({
        ...prevState,
        isLoading: false,
        error: error.message
      }));

      // Add error message to UI
      const errorMessage = {
        id: uuidv4(),
        role: 'system',
        content: `Error: ${error.message}`,
        error: true,
        timestamp: new Date().toISOString()
      };

      setChatState(prevState => ({
        ...prevState,
        messages: [...prevState.messages, errorMessage]
      }));
    }
  };

  // Function to start new conversation
  const startNewConversation = () => {
    const newSessionId = uuidv4();
    localStorage.setItem('sessionId', newSessionId);
    
    setChatState({
      messages: [],
      isLoading: false,
      error: null,
      sessionId: newSessionId
    });
  };

  // Function to load conversation history
  const loadConversationHistory = async () => {
    if (!chatState.sessionId) return;

    setChatState(prevState => ({
      ...prevState,
      isLoading: true,
      error: null
    }));

    try {
      const response = await chatService.getHistory(chatState.sessionId);
      
      if (response.success && response.data.history) {
        // Convert API history format to our message format
        const messages = [];
        
        response.data.history.forEach(conv => {
          conv.messages.forEach(msg => {
            messages.push({
              id: uuidv4(),
              role: msg.role,
              content: msg.content,
              metadata: msg.role === 'assistant' ? {
                agent: conv.selected_agent,
                confidence: conv.confidence
              } : undefined,
              timestamp: msg.timestamp
            });
          });
        });

        setChatState(prevState => ({
          ...prevState,
          messages,
          isLoading: false
        }));
      } else {
        // If no history or error, just clear loading state
        setChatState(prevState => ({
          ...prevState,
          isLoading: false
        }));
      }
    } catch (error) {
      setChatState(prevState => ({
        ...prevState,
        isLoading: false,
        error: error.message
      }));
    }
  };

  // Value object that will be shared with all consumers
  const contextValue = {
    systemStatus,
    chatState,
    sendMessage,
    startNewConversation,
    loadConversationHistory
  };

  // Provide the context value to all children
  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

export default AppContext;