import React, { useState } from 'react';
import { Container } from 'react-bootstrap';
import Sidebar from './Sidebar';
import TopNavbar from './TopNavbar';
import NotificationsContainer from './NotificationsContainer';
import { useAppContext } from '../../context/AppContext';

/**
 * Main application layout component
 * Provides the overall structure for the application with responsive sidebar
 * and top navigation
 */
const AppLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { state } = useAppContext();
  
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="app-container d-flex flex-column vh-100">
      <TopNavbar 
        sidebarOpen={sidebarOpen} 
        toggleSidebar={toggleSidebar} 
      />
      
      <div className="d-flex flex-grow-1 overflow-hidden">
        <Sidebar open={sidebarOpen} />
        
        <main className={`main-content flex-grow-1 ${sidebarOpen ? 'with-sidebar' : ''}`}>
          <Container fluid className="py-3">
            {children}
          </Container>
        </main>
      </div>
      
      {/* Notifications system */}
      <NotificationsContainer notifications={state.notifications} />
    </div>
  );
};

export default AppLayout;