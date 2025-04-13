import React from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';

/**
 * Global notification system component
 * Displays toast notifications for system events
 */
const Notifications = ({ notifications, onDismiss }) => {
  // Icons for different notification types
  const notificationIcons = {
    success: 'check-circle',
    error: 'alert-circle',
    warning: 'alert-triangle',
    info: 'info'
  };

  return (
    <ToastContainer className="position-fixed p-3" position="top-end">
      {notifications.map((notification) => (
        <Toast 
          key={notification.id}
          onClose={() => onDismiss(notification.id)}
          show={true}
          delay={notification.autoDismiss ? 5000 : null}
          autohide={!!notification.autoDismiss}
          className={`notification notification-${notification.type || 'info'}`}
        >
          <Toast.Header>
            <div className="me-2">
              <FeatherIcon 
                icon={notificationIcons[notification.type] || 'bell'} 
                size={16} 
                className={`text-${notification.type || 'info'}`}
              />
            </div>
            <strong className="me-auto">{notification.title}</strong>
            <small className="text-muted">
              {notification.timestamp ? new Date(notification.timestamp).toLocaleTimeString() : 'just now'}
            </small>
          </Toast.Header>
          <Toast.Body>{notification.message}</Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default Notifications;