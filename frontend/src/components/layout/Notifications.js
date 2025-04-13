import React from 'react';
import { Toast, ToastContainer } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';

const getToastIcon = (type) => {
  switch (type) {
    case 'success':
      return <FeatherIcon icon="check-circle" className="text-success" />;
    case 'error':
      return <FeatherIcon icon="alert-circle" className="text-danger" />;
    case 'warning':
      return <FeatherIcon icon="alert-triangle" className="text-warning" />;
    case 'info':
    default:
      return <FeatherIcon icon="info" className="text-info" />;
  }
};

const getToastVariant = (type) => {
  switch (type) {
    case 'success':
      return 'success';
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
    default:
      return 'info';
  }
};

const Notifications = () => {
  const { notifications, removeNotification } = useAppContext();

  return (
    <ToastContainer position="top-end" className="p-3">
      {notifications.map((notification) => (
        <Toast 
          key={notification.id} 
          onClose={() => removeNotification(notification.id)}
          bg={getToastVariant(notification.type)}
          className="mb-2"
        >
          <Toast.Header>
            <span className="me-2">{getToastIcon(notification.type)}</span>
            <strong className="me-auto">{notification.title || 'Notification'}</strong>
            <small>{notification.time || 'Just now'}</small>
          </Toast.Header>
          <Toast.Body className={notification.type === 'error' ? 'text-white' : ''}>
            {notification.message}
          </Toast.Body>
        </Toast>
      ))}
    </ToastContainer>
  );
};

export default Notifications;