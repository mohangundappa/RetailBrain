import { useState, useCallback, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import { chatService, agentService } from '../api/apiService';

/**
 * Custom hook for managing chat sessions and interactions with agents
 * Provides a comprehensive interface for chat functionality with automatic history loading
 * 
 * @param {String} initialSessionId - Optional initial session ID
 * @param {String} initialAgentId - Optional initial agent ID
 * @returns {Object} - Chat state and control functions
 */
const useChat = (initialSessionId = null, initialAgentId = null) => {
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(initialAgentId);
  const [agents, setAgents] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  
  const { actions } = useAppContext();

  // Load available agents
  const loadAgents = useCallback(async () => {
    setAgentsLoading(true);
    
    try {
      const result = await agentService.listAgents();
      
      if (result.success && result.agents) {
        setAgents(result.agents);
      } else {
        setError(result.error || 'Failed to load agents');
        actions.addNotification({
          type: 'error',
          title: 'Agent Loading Error',
          message: result.error || 'Failed to load agents',
          autoDismiss: true
        });
      }
    } catch (err) {
      setError(err.message);
      actions.addNotification({
        type: 'error',
        title: 'Agent Loading Error',
        message: err.message,
        autoDismiss: true
      });
    } finally {
      setAgentsLoading(false);
    }
  }, [actions]);

  // Load chat history
  const loadChatHistory = useCallback(async (sid) => {
    if (!sid) return;
    
    setLoading(true);
    
    try {
      const result = await chatService.getChatHistory(sid);
      
      if (result.success && result.data?.messages) {
        setMessages(result.data.messages);
      } else {
        setError(result.error || 'Failed to load chat history');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Start a new chat session
  const startSession = useCallback(async (agentId = null) => {
    setLoading(true);
    
    try {
      const result = await chatService.startSession(agentId || selectedAgent);
      
      if (result.success && result.data?.session_id) {
        setSessionId(result.data.session_id);
        setMessages([]);
        setError(null);
        return result.data.session_id;
      } else {
        setError(result.error || 'Failed to start chat session');
        actions.addNotification({
          type: 'error',
          title: 'Session Error',
          message: result.error || 'Failed to start chat session',
          autoDismiss: true
        });
        return null;
      }
    } catch (err) {
      setError(err.message);
      actions.addNotification({
        type: 'error',
        title: 'Session Error',
        message: err.message,
        autoDismiss: true
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [selectedAgent, actions]);

  // End the current chat session
  const endSession = useCallback(async () => {
    if (!sessionId) return;
    
    setLoading(true);
    
    try {
      const result = await chatService.endSession(sessionId);
      
      if (result.success) {
        setSessionId(null);
        setMessages([]);
      } else {
        setError(result.error || 'Failed to end chat session');
        actions.addNotification({
          type: 'error',
          title: 'Session Error',
          message: result.error || 'Failed to end chat session',
          autoDismiss: true
        });
      }
    } catch (err) {
      setError(err.message);
      actions.addNotification({
        type: 'error',
        title: 'Session Error',
        message: err.message,
        autoDismiss: true
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, actions]);

  // Send a message in the current session
  const sendMessage = useCallback(async (messageText, context = null) => {
    if (!sessionId) {
      // Start a new session if one doesn't exist
      const newSessionId = await startSession();
      if (!newSessionId) return;
    }
    
    setSending(true);
    
    // Optimistically add user message to the UI
    const userMessage = {
      id: Date.now().toString(),
      content: messageText,
      role: 'user',
      timestamp: new Date().toISOString()
    };
    
    setMessages(prevMessages => [...prevMessages, userMessage]);
    
    try {
      const result = await chatService.sendMessage(messageText, sessionId, context);
      
      if (result.success && result.data?.response) {
        // Add system response to messages
        const systemMessage = {
          id: result.data.message_id || Date.now().toString() + '-response',
          content: result.data.response,
          role: 'system',
          timestamp: new Date().toISOString(),
          metadata: result.data.metadata || {}
        };
        
        setMessages(prevMessages => [...prevMessages, systemMessage]);
        setError(null);
        return systemMessage;
      } else {
        setError(result.error || 'Failed to send message');
        actions.addNotification({
          type: 'error',
          title: 'Message Error',
          message: result.error || 'Failed to send message',
          autoDismiss: true
        });
        return null;
      }
    } catch (err) {
      setError(err.message);
      actions.addNotification({
        type: 'error',
        title: 'Message Error',
        message: err.message,
        autoDismiss: true
      });
      return null;
    } finally {
      setSending(false);
    }
  }, [sessionId, startSession, actions]);

  // Select an agent
  const selectAgent = useCallback((agentId) => {
    setSelectedAgent(agentId);
    
    // Reset the session when changing agents
    if (sessionId) {
      endSession().then(() => {
        startSession(agentId);
      });
    }
  }, [sessionId, endSession, startSession]);

  // Load agents on mount
  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  // Load chat history when session ID changes
  useEffect(() => {
    if (sessionId) {
      loadChatHistory(sessionId);
    }
  }, [sessionId, loadChatHistory]);

  return {
    // State
    sessionId,
    messages,
    loading,
    sending,
    error,
    selectedAgent,
    agents,
    agentsLoading,
    
    // Actions
    sendMessage,
    startSession,
    endSession,
    selectAgent,
    loadAgents,
    loadChatHistory,
    
    // Direct state setters
    setMessages,
    setError
  };
};

export default useChat;