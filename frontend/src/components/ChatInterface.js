import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Form, Button, Card, Spinner, Alert } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../context/AppContext';
import { formatDistanceToNow } from 'date-fns';

const ChatInterface = () => {
  const { chatState, sendMessage, loadConversationHistory } = useAppContext();
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);
  
  // Load chat history when component mounts
  useEffect(() => {
    loadConversationHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatState.messages]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    
    sendMessage(inputMessage);
    setInputMessage('');
  };
  
  // Format time relative to now (e.g., "5 minutes ago")
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
    } catch (error) {
      return '';
    }
  };
  
  return (
    <Container fluid className="py-3 h-100 d-flex flex-column">
      <Row className="flex-grow-1">
        <Col md={12} className="d-flex flex-column h-100">
          <Card className="flex-grow-1 shadow-sm border-0 mb-3">
            <Card.Header className="bg-dark text-light d-flex justify-content-between align-items-center">
              <div>
                <FeatherIcon icon="message-square" className="me-2" />
                <span>Chat with Staples Brain</span>
              </div>
              <div>
                <span className="badge bg-secondary me-2">
                  Session: {chatState.sessionId?.substring(0, 8)}
                </span>
              </div>
            </Card.Header>
            <Card.Body className="chat-container p-4" style={{ overflowY: 'auto', maxHeight: '60vh' }}>
              {chatState.messages.length === 0 && !chatState.isLoading && (
                <div className="text-center text-muted my-5">
                  <FeatherIcon icon="message-circle" size={48} />
                  <p className="mt-3">Start a conversation with Staples Brain!</p>
                  <p className="small">Ask questions about orders, password reset, store locations, and more.</p>
                </div>
              )}
              
              {chatState.messages.map((message) => (
                <div
                  key={message.id}
                  className={`d-flex ${message.role === 'user' ? 'justify-content-end' : 'justify-content-start'} mb-3`}
                >
                  <div 
                    className={`message-bubble p-3 rounded ${
                      message.role === 'user' 
                        ? 'bg-primary text-white' 
                        : message.role === 'system'
                          ? 'bg-danger text-white' 
                          : 'bg-light'
                    }`}
                    style={{ maxWidth: '75%' }}
                  >
                    <div>{message.content}</div>
                    
                    {message.metadata && (
                      <div className="mt-2 pt-2 border-top small opacity-75">
                        {message.metadata.agent && (
                          <div>Agent: {message.metadata.agent}</div>
                        )}
                        {message.metadata.confidence && (
                          <div>Confidence: {(message.metadata.confidence * 100).toFixed(1)}%</div>
                        )}
                      </div>
                    )}
                    
                    <div className="mt-1 text-end small opacity-75">
                      {formatTimestamp(message.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
              
              {chatState.isLoading && (
                <div className="d-flex justify-content-start mb-3">
                  <div className="message-bubble p-3 rounded bg-light">
                    <Spinner animation="border" size="sm" role="status" className="me-2" />
                    <span>Thinking...</span>
                  </div>
                </div>
              )}
              
              {chatState.error && (
                <Alert variant="danger" className="my-3">
                  Error: {chatState.error}
                </Alert>
              )}
              
              <div ref={messagesEndRef} />
            </Card.Body>
            <Card.Footer className="bg-light border-0 p-3">
              <Form onSubmit={handleSubmit}>
                <Row>
                  <Col md={12}>
                    <div className="input-group">
                      <Form.Control
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        placeholder="Type your message here..."
                        disabled={chatState.isLoading}
                        className="py-2"
                        onKeyPress={(e) => e.key === 'Enter' && handleSubmit(e)}
                      />
                      <Button 
                        variant="primary" 
                        type="submit" 
                        disabled={chatState.isLoading || !inputMessage.trim()}
                      >
                        {chatState.isLoading ? (
                          <Spinner animation="border" size="sm" role="status" />
                        ) : (
                          <FeatherIcon icon="send" size={18} />
                        )}
                      </Button>
                    </div>
                  </Col>
                </Row>
              </Form>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ChatInterface;