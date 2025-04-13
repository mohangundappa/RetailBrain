import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Nav } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';

const Sidebar = () => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const toggleSidebar = () => {
    setCollapsed(!collapsed);
  };

  const navItems = [
    { path: '/', icon: 'home', label: 'Dashboard' },
    { path: '/chat', icon: 'message-square', label: 'Chat' },
    { path: '/agents', icon: 'cpu', label: 'Agents' },
    { path: '/analytics', icon: 'bar-chart-2', label: 'Analytics' },
    { path: '/settings', icon: 'settings', label: 'Settings' }
  ];

  return (
    <div className={`sidebar bg-dark ${collapsed ? 'collapsed' : ''}`} style={{ width: collapsed ? '60px' : '240px', transition: 'width 0.3s' }}>
      <div className="d-flex justify-content-between align-items-center p-3 border-bottom border-secondary">
        {!collapsed && <h5 className="m-0 text-light">Staples Brain</h5>}
        <button className="btn btn-sm btn-dark" onClick={toggleSidebar}>
          <FeatherIcon icon={collapsed ? 'chevron-right' : 'chevron-left'} size={16} />
        </button>
      </div>
      <Nav className="flex-column mt-2">
        {navItems.map((item) => (
          <Nav.Item key={item.path}>
            <Nav.Link
              as={Link}
              to={item.path}
              className={`d-flex align-items-center py-2 ${location.pathname === item.path ? 'active text-white' : 'text-light'}`}
            >
              <FeatherIcon icon={item.icon} size={18} className="me-3" />
              {!collapsed && <span>{item.label}</span>}
            </Nav.Link>
          </Nav.Item>
        ))}
      </Nav>
      <div className="mt-auto p-3 border-top border-secondary">
        {!collapsed && (
          <div className="d-flex align-items-center">
            <FeatherIcon icon="info" size={18} className="text-info me-2" />
            <small className="text-light">v1.0.0</small>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;