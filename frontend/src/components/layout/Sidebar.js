import React from 'react';
import { Nav } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import { useAppContext } from '../../context/AppContext';

// Import icons
// We'll use a placeholder for now, but this would normally use feather-icons-react
const Icon = ({ name }) => (
  <span className="me-2">
    {name === 'home' && '🏠'}
    {name === 'message-square' && '💬'}
    {name === 'bar-chart-2' && '📊'}
    {name === 'code' && '👨‍💻'}
    {name === 'settings' && '⚙️'}
    {name === 'info' && 'ℹ️'}
    {name === 'users' && '👥'}
    {name === 'server' && '🖥️'}
  </span>
);

/**
 * Sidebar navigation component
 * Provides main navigation links with collapsible behavior
 */
const Sidebar = ({ open }) => {
  const location = useLocation();
  const { state } = useAppContext();
  
  // We can use state.user to show different navigation items based on role
  const isAdmin = state.user?.role === 'admin';
  
  const getNavLinkClass = (path) => {
    return `nav-link d-flex align-items-center ${location.pathname === path ? 'active' : ''}`;
  };

  return (
    <div className={`sidebar bg-dark d-flex flex-column ${open ? '' : 'closed'}`}>
      <div className="sidebar-header d-flex align-items-center justify-content-center p-3">
        <h5 className="m-0 text-white">
          {open ? 'Staples Brain' : 'SB'}
        </h5>
      </div>
      
      <div className="sidebar-content flex-grow-1 p-3">
        <Nav className="flex-column">
          <Nav.Item>
            <Link to="/" className={getNavLinkClass('/')}>
              <Icon name="home" />
              {open && <span>Dashboard</span>}
            </Link>
          </Nav.Item>
          
          <Nav.Item>
            <Link to="/chat" className={getNavLinkClass('/chat')}>
              <Icon name="message-square" />
              {open && <span>Chat</span>}
            </Link>
          </Nav.Item>
          
          <Nav.Item>
            <Link to="/observability" className={getNavLinkClass('/observability')}>
              <Icon name="bar-chart-2" />
              {open && <span>Observability</span>}
            </Link>
          </Nav.Item>
          
          <Nav.Item>
            <Link to="/agent-builder" className={getNavLinkClass('/agent-builder')}>
              <Icon name="code" />
              {open && <span>Agent Builder</span>}
            </Link>
          </Nav.Item>
          
          <Nav.Item>
            <Link to="/documentation" className={getNavLinkClass('/documentation')}>
              <Icon name="info" />
              {open && <span>Documentation</span>}
            </Link>
          </Nav.Item>
          
          <Nav.Item>
            <Link to="/settings" className={getNavLinkClass('/settings')}>
              <Icon name="settings" />
              {open && <span>Settings</span>}
            </Link>
          </Nav.Item>
          
          {isAdmin && (
            <>
              <div className="dropdown-divider my-3"></div>
              <h6 className="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
                <span>{open ? 'Admin' : ''}</span>
              </h6>
              
              <Nav.Item>
                <Link to="/admin/users" className={getNavLinkClass('/admin/users')}>
                  <Icon name="users" />
                  {open && <span>Users</span>}
                </Link>
              </Nav.Item>
              
              <Nav.Item>
                <Link to="/admin/system" className={getNavLinkClass('/admin/system')}>
                  <Icon name="server" />
                  {open && <span>System</span>}
                </Link>
              </Nav.Item>
            </>
          )}
        </Nav>
      </div>
      
      <div className="sidebar-footer p-3 text-center">
        <small className="text-muted">
          {open ? 'v1.0.0' : ''}
        </small>
      </div>
    </div>
  );
};

export default Sidebar;