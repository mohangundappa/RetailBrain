import React from 'react';
import { Nav } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';

/**
 * Application sidebar
 * Responsive collapsible sidebar with navigation links and system information
 */
const Sidebar = ({ isOpen, onToggle }) => {
  const location = useLocation();
  const { state } = useAppContext();
  const { systemStatus } = state;

  // Navigation items - easily extensible for future pages
  const navItems = [
    { 
      path: '/', 
      icon: 'home', 
      label: 'Dashboard',
      exact: true
    },
    { 
      path: '/chat', 
      icon: 'message-square', 
      label: 'Chat Interface' 
    },
    { 
      path: '/observability', 
      icon: 'activity', 
      label: 'Observability' 
    },
    { 
      path: '/agent-builder', 
      icon: 'tool', 
      label: 'Agent Builder' 
    },
    { 
      path: '/documentation', 
      icon: 'book-open', 
      label: 'Documentation' 
    },
    { 
      path: '/settings', 
      icon: 'settings', 
      label: 'Settings' 
    }
  ];

  // Group for admin functions - can be conditionally shown based on permissions
  const adminItems = [
    {
      path: '/admin/users',
      icon: 'users',
      label: 'User Management'
    },
    {
      path: '/admin/system',
      icon: 'server',
      label: 'System Settings'
    }
  ];
  
  return (
    <div className={`sidebar bg-dark text-white ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header d-flex justify-content-between align-items-center p-3 border-bottom border-secondary">
        <div className="d-flex align-items-center">
          <div className="sidebar-logo me-2">
            <FeatherIcon icon="cpu" />
          </div>
          <h5 className={`mb-0 sidebar-title ${isOpen ? 'd-block' : 'd-none'}`}>Staples Brain</h5>
        </div>
        <button 
          className="btn btn-link text-white p-0" 
          onClick={onToggle} 
          aria-label="Toggle sidebar"
        >
          <FeatherIcon icon={isOpen ? 'chevron-left' : 'chevron-right'} />
        </button>
      </div>
      
      <div className="sidebar-content p-2">
        <Nav className="flex-column">
          {navItems.map((item) => (
            <Nav.Item key={item.path}>
              <Nav.Link 
                as={Link} 
                to={item.path}
                className={`d-flex align-items-center py-2 ${location.pathname === item.path ? 'active' : ''}`}
              >
                <FeatherIcon icon={item.icon} className="me-3" />
                <span className={`nav-text ${isOpen ? 'd-block' : 'd-none'}`}>{item.label}</span>
              </Nav.Link>
            </Nav.Item>
          ))}
          
          {/* Admin section - can be conditionally shown */}
          <div className={`mt-4 mb-2 sidebar-section-header ${isOpen ? 'd-block' : 'd-none'}`}>
            <small className="text-muted fw-bold">ADMIN</small>
          </div>
          
          {adminItems.map((item) => (
            <Nav.Item key={item.path}>
              <Nav.Link 
                as={Link} 
                to={item.path}
                className={`d-flex align-items-center py-2 ${location.pathname === item.path ? 'active' : ''}`}
              >
                <FeatherIcon icon={item.icon} className="me-3" />
                <span className={`nav-text ${isOpen ? 'd-block' : 'd-none'}`}>{item.label}</span>
              </Nav.Link>
            </Nav.Item>
          ))}
        </Nav>
      </div>
      
      <div className="sidebar-footer mt-auto p-3 border-top border-secondary">
        <div className="d-flex align-items-center">
          <div className={`status-indicator me-2 ${systemStatus.isHealthy ? 'bg-success' : 'bg-danger'}`} style={{ width: '10px', height: '10px', borderRadius: '50%' }}></div>
          <small className={`${isOpen ? 'd-block' : 'd-none'}`}>
            {systemStatus.isHealthy ? 'All Systems Operational' : 'System Issues Detected'}
          </small>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;