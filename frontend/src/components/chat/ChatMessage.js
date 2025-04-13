import React from 'react';
import { format } from 'date-fns';
import FeatherIcon from 'feather-icons-react';

const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  const isPending = message.pending;
  const isFailed = message.failed;
  
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Just now';
    
    try {
      return format(new Date(timestamp), 'h:mm a');
    } catch (e) {
      return 'Just now';
    }
  };

  return (
    <div className={`chat-message mb-3 ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className={`d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'}`}>
        <div 
          className={`message-content p-3 rounded-3 ${
            isUser 
              ? 'bg-primary text-white' 
              : 'bg-light text-dark'
          }`}
          style={{ maxWidth: '80%' }}
        >
          {isPending && (
            <div className="message-status mb-1">
              <small className="text-white-50 d-flex align-items-center">
                <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                Sending...
              </small>
            </div>
          )}
          
          {isFailed && (
            <div className="message-status mb-1">
              <small className="text-white-50 d-flex align-items-center">
                <FeatherIcon icon="alert-circle" size={12} className="me-1" />
                Failed to send
              </small>
            </div>
          )}
          
          <div className="message-text">{message.content}</div>
          
          <div className="message-meta mt-1">
            <small className={isUser ? 'text-white-50' : 'text-muted'}>
              {formatTimestamp(message.timestamp)}
              {isUser && !isPending && !isFailed && (
                <FeatherIcon icon="check" size={12} className="ms-1" />
              )}
            </small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;