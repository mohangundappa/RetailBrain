import { useState, useEffect, useCallback } from 'react';
import { useAppContext } from '../context/AppContext';
import apiService from '../api/apiService';

/**
 * Custom hook for chat functionality
 * 
 * @returns {Object} Chat utilities and state
 */
const useChat = () => {
  const { setLoading, addNotification, currentConversation, setCurrentConversation } = useAppContext();
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  
  /**
   * Load conversation history from API
   */
  const loadConversation = useCallback(async (conversationId) => {
    if (!conversationId && !currentConversation?.id) {
      return false;
    }
    
    const targetId = conversationId || currentConversation.id;
    
    try {
      setLoading(true);
      const response = await apiService.apiCall(
        apiService.getConversationHistory,
        targetId
      );
      
      if (response.success && response.data) {
        setMessages(response.data.messages || []);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error loading conversation:', error);
      addNotification({
        title: 'Error',
        message: 'Failed to load conversation history',
        type: 'error'
      });
      return false;
    } finally {
      setLoading(false);
    }
  }, [currentConversation, setLoading, addNotification]);

  /**
   * Start a new conversation
   */
  const startConversation = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.apiCall(apiService.startConversation);
      
      if (response.success && response.data) {
        setCurrentConversation(response.data);
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: 'Hello! I am Staples Brain, your AI assistant. How can I help you today?',
            timestamp: new Date().toISOString()
          }
        ]);
        return response.data;
      }
      throw new Error('Failed to start conversation');
    } catch (error) {
      console.error('Error starting conversation:', error);
      addNotification({
        title: 'Error',
        message: 'Failed to start a new conversation',
        type: 'error'
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [setCurrentConversation, setLoading, addNotification]);

  /**
   * Send a message in the current conversation
   */
  const sendMessage = useCallback(async (content) => {
    if (!content.trim() || !currentConversation?.id) {
      return false;
    }
    
    const tempMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      pending: true
    };
    
    setMessages(prev => [...prev, tempMessage]);
    setIsSending(true);
    
    try {
      const response = await apiService.apiCall(
        apiService.sendMessage,
        currentConversation.id,
        content
      );
      
      if (response.success && response.data) {
        // Update temp message with real message
        setMessages(prev => 
          prev.map(msg => 
            msg.id === tempMessage.id 
              ? { ...response.data.userMessage, pending: false } 
              : msg
          )
        );
        
        // Add assistant response if available
        if (response.data.assistantMessage) {
          setMessages(prev => [...prev, response.data.assistantMessage]);
        }
        
        return true;
      }
      
      throw new Error('Failed to send message');
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Mark message as failed
      setMessages(prev => 
        prev.map(msg => 
          msg.id === tempMessage.id 
            ? { ...msg, pending: false, failed: true } 
            : msg
        )
      );
      
      addNotification({
        title: 'Error',
        message: 'Failed to send message',
        type: 'error'
      });
      
      return false;
    } finally {
      setIsSending(false);
    }
  }, [currentConversation, addNotification]);

  // Initialize chat when hook is first used
  useEffect(() => {
    if (currentConversation?.id) {
      loadConversation();
    } else {
      startConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    messages,
    isSending,
    sendMessage,
    startConversation,
    loadConversation,
    currentConversation
  };
};

export default useChat;