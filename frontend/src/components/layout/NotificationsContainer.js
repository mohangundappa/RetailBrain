import React from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';
import { useAppContext } from '../../context/AppContext';

/**
 * Notifications container component
 * Displays global notifications/toasts with auto-dismiss functionality
 */
const NotificationsContainer = ({ notifications = [] }) => {
  const { actions } = useAppContext();

  const handleClose = (id) => {
    actions.removeNotification(id);
  };

  // Get toast header background color based on notification type
  const getHeaderClass = (type) => {
    switch (type) {
      case 'success':
        return 'bg-success text-white';
      case 'error':
        return 'bg-danger text-white';
      case 'warning':
        return 'bg-warning text-dark';
      case 'info':
      default:
        return 'bg-info text-white';
    }
  };

  // Get toast container class based on notification type
  const getToastClass = (type) => {
    return `notification notification-${type}`;
  };

  // Auto-dismiss notifications after specified delay
  const getDelay = (notification) => {
    if (!notification.autoDismiss) return Infinity;
    
    // Different delay based on type
    switch (notification.type) {
      case 'error':
        return 8000; // Errors stay longer
      case 'warning':
        return 6000;
      case 'success':
      case 'info':
      default:
        return 4000;
    }
  };

  return (
    <ToastContainer 
      className="p-3" 
      position="top-end"
      style={{ zIndex: 1060 }}
    >
      {notifications.map((notification) => (
        <Toast
          key={notification.id}
          className={getToastClass(notification.type)}
          onClose={() => handleClose(notification.id)}
          show={true}
          delay={getDelay(notification)}
          autohide={notification.autoDismiss}
        >
          <Toast.Header className={getHeaderClass(notification.type)}>
            <strong className="me-auto">{notification.title}</strong>
            <small>
              {notification.timestamp 
                ? new Date(notification.timestamp).toLocaleTimeString() 
                : 'just now'}
            </small>
          </Toast.Header>
          <Toast.Body>{notification.message}</Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default NotificationsContainer;