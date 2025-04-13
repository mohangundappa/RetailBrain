import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Form, Button, Badge } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';
import apiService from '../../api/apiService';
import ChatMessage from './ChatMessage';

const ChatInterface = () => {
  const { 
    agents, 
    setAgents,
    setLoading, 
    addNotification,
    currentConversation,
    setCurrentConversation 
  } = useAppContext();
  
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        
        // Fetch agents if needed
        if (!agents || agents.length === 0) {
          const agentsResponse = await apiService.apiCall(apiService.getAgents);
          if (agentsResponse.success && agentsResponse.agents) {
            setAgents(agentsResponse.agents);
          }
        }
        
        // Start a new conversation if none exists
        if (!currentConversation) {
          const conversationResponse = await apiService.apiCall(apiService.startConversation);
          if (conversationResponse.success && conversationResponse.data) {
            setCurrentConversation(conversationResponse.data);
            
            // Add initial message
            setMessages([
              {
                id: 'welcome',
                role: 'assistant',
                content: 'Hello! I am Staples Brain, your AI assistant. How can I help you today?',
                timestamp: new Date().toISOString()
              }
            ]);
          }
        } else {
          // Fetch existing conversation history
          const historyResponse = await apiService.apiCall(
            apiService.getConversationHistory,
            currentConversation.id
          );
          
          if (historyResponse.success && historyResponse.data) {
            setMessages(historyResponse.data.messages || []);
          }
        }
      } catch (error) {
        console.error('Error initializing chat:', error);
        addNotification({
          title: 'Error',
          message: 'Could not initialize chat. Please try again later.',
          type: 'error'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, [agents, currentConversation, setAgents, setCurrentConversation, setLoading, addNotification]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!messageInput.trim() || !currentConversation) {
      return;
    }
    
    const newMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: messageInput,
      timestamp: new Date().toISOString(),
      pending: true
    };
    
    setMessages(prev => [...prev, newMessage]);
    setMessageInput('');
    setIsSending(true);
    
    try {
      const response = await apiService.apiCall(
        apiService.sendMessage,
        currentConversation.id,
        messageInput
      );
      
      if (response.success && response.data) {
        // Replace temp message with actual message
        setMessages(prev => 
          prev.map(msg => 
            msg.id === newMessage.id 
              ? { ...response.data.userMessage, pending: false } 
              : msg
          )
        );
        
        // Add assistant response
        if (response.data.assistantMessage) {
          setMessages(prev => [...prev, response.data.assistantMessage]);
        }
      } else {
        throw new Error('Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Mark message as failed
      setMessages(prev => 
        prev.map(msg => 
          msg.id === newMessage.id 
            ? { ...msg, pending: false, failed: true } 
            : msg
        )
      );
      
      addNotification({
        title: 'Error',
        message: 'Failed to send message. Please try again.',
        type: 'error'
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Container fluid className="p-4 h-100 d-flex flex-column">
      <Row className="mb-4">
        <Col>
          <h1 className="h3">Chat with Staples Brain</h1>
          <p className="text-muted">
            Ask questions, get assistance, or explore agent capabilities.
          </p>
        </Col>
      </Row>
      
      <Row className="flex-grow-1">
        <Col>
          <Card className="h-100 d-flex flex-column">
            <Card.Header className="bg-transparent py-3">
              <div className="d-flex justify-content-between align-items-center">
                <div className="d-flex align-items-center">
                  <div className="position-relative me-2">
                    <FeatherIcon icon="cpu" className="text-primary" />
                    <span className="position-absolute bottom-0 end-0 translate-middle p-1 bg-success rounded-circle">
                      <span className="visually-hidden">Active</span>
                    </span>
                  </div>
                  <div>
                    <h5 className="mb-0">Staples Brain</h5>
                    <Badge bg="info" className="text-white">Multi-Agent System</Badge>
                  </div>
                </div>
                <div>
                  <Button variant="outline-secondary" size="sm" className="me-2">
                    <FeatherIcon icon="refresh-cw" size={16} />
                  </Button>
                  <Button variant="outline-secondary" size="sm">
                    <FeatherIcon icon="settings" size={16} />
                  </Button>
                </div>
              </div>
            </Card.Header>
            
            <Card.Body className="p-0 overflow-auto flex-grow-1">
              <div className="chat-messages p-3">
                {messages.length > 0 ? (
                  messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))
                ) : (
                  <div className="text-center py-5">
                    <FeatherIcon icon="message-circle" size={48} className="text-muted mb-3" />
                    <h5>No messages yet</h5>
                    <p className="text-muted">
                      Start the conversation by sending a message below.
                    </p>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </Card.Body>
            
            <Card.Footer className="bg-transparent">
              <Form onSubmit={handleSendMessage}>
                <div className="d-flex">
                  <Form.Control
                    type="text"
                    placeholder="Type your message here..."
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    disabled={isSending}
                    className="me-2"
                  />
                  <Button 
                    type="submit" 
                    variant="primary"
                    disabled={!messageInput.trim() || isSending}
                  >
                    {isSending ? (
                      <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    ) : (
                      <FeatherIcon icon="send" size={16} />
                    )}
                  </Button>
                </div>
              </Form>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ChatInterface;