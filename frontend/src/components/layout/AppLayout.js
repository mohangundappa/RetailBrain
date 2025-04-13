import React from 'react';
import { Container } from 'react-bootstrap';
import Sidebar from './Sidebar';
import TopNavbar from './TopNavbar';
import Notifications from '../common/Notifications';
import { useAppContext } from '../../context/AppContext';

/**
 * Main application layout component
 * Includes responsive sidebar, top navigation, and notification system
 */
const AppLayout = ({ children }) => {
  const { state, actions } = useAppContext();
  const { sidebarOpen } = state.ui;

  return (
    <div className="app-container d-flex flex-column vh-100">
      <TopNavbar />
      
      <div className="d-flex flex-grow-1 overflow-hidden">
        {/* Collapsible sidebar */}
        <Sidebar isOpen={sidebarOpen} onToggle={actions.toggleSidebar} />
        
        {/* Main content area */}
        <main className={`main-content flex-grow-1 transition-all ${sidebarOpen ? 'with-sidebar' : ''}`}>
          <Container fluid className="py-3 px-md-4">
            {children}
          </Container>
        </main>
      </div>
      
      {/* Global notification system */}
      <Notifications 
        notifications={state.ui.notifications}
        onDismiss={actions.removeNotification}
      />
    </div>
  );
};

export default AppLayout;