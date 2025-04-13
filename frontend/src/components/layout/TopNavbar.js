import React, { useState } from 'react';
import { Navbar, Nav, NavDropdown, Form, InputGroup, Button } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';

/**
 * Top navigation bar component
 * Includes search, user profile, and global actions
 */
const TopNavbar = () => {
  const { state, actions } = useAppContext();
  const [searchQuery, setSearchQuery] = useState('');
  
  // Handle search submission
  const handleSearch = (e) => {
    e.preventDefault();
    // Implement global search functionality here
    console.log('Search query:', searchQuery);
    
    // Clear the search input
    setSearchQuery('');
  };
  
  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="px-3 py-2 border-bottom border-secondary">
      <Navbar.Brand href="/" className="me-0 me-md-2 d-flex align-items-center">
        <FeatherIcon icon="cpu" className="me-2" />
        <span className="d-none d-md-inline">Staples Brain</span>
      </Navbar.Brand>
      
      <div className="d-flex flex-grow-1 justify-content-end justify-content-lg-between">
        {/* Global search */}
        <Form className="d-none d-lg-flex mx-4 flex-grow-1" onSubmit={handleSearch}>
          <InputGroup>
            <Form.Control
              type="search"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-dark-subtle border-secondary text-white"
            />
            <Button variant="outline-secondary" type="submit">
              <FeatherIcon icon="search" size={18} />
            </Button>
          </InputGroup>
        </Form>
        
        {/* Right-aligned items */}
        <div className="d-flex align-items-center">
          {/* Theme toggle */}
          <Button 
            variant="link" 
            className="text-white p-1 me-3"
            onClick={() => actions.setTheme(state.ui.theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
          >
            <FeatherIcon icon={state.ui.theme === 'dark' ? 'sun' : 'moon'} size={20} />
          </Button>
          
          {/* Notifications */}
          <NavDropdown
            title={<FeatherIcon icon="bell" size={20} />}
            id="notifications-dropdown"
            align="end"
            className="me-3"
          >
            <NavDropdown.Header>Notifications</NavDropdown.Header>
            <NavDropdown.Item>
              <div className="notification-item">
                <strong>System Status:</strong> All agents operational
                <small className="text-muted d-block">5 min ago</small>
              </div>
            </NavDropdown.Item>
            <NavDropdown.Item>
              <div className="notification-item">
                <strong>New Agent Available:</strong> Store Finder v2
                <small className="text-muted d-block">1 hour ago</small>
              </div>
            </NavDropdown.Item>
            <NavDropdown.Divider />
            <NavDropdown.Item className="text-center">
              <small>View all notifications</small>
            </NavDropdown.Item>
          </NavDropdown>
          
          {/* User profile */}
          <NavDropdown
            title={
              <div className="d-flex align-items-center">
                <div className="profile-avatar me-2 d-flex align-items-center justify-content-center bg-primary rounded-circle" style={{ width: '32px', height: '32px' }}>
                  <span>A</span>
                </div>
                <span className="d-none d-md-inline">Admin</span>
              </div>
            }
            id="profile-dropdown"
            align="end"
          >
            <NavDropdown.Item href="/profile">
              <FeatherIcon icon="user" className="me-2" size={16} />
              Profile
            </NavDropdown.Item>
            <NavDropdown.Item href="/preferences">
              <FeatherIcon icon="settings" className="me-2" size={16} />
              Preferences
            </NavDropdown.Item>
            <NavDropdown.Divider />
            <NavDropdown.Item href="/logout">
              <FeatherIcon icon="log-out" className="me-2" size={16} />
              Sign out
            </NavDropdown.Item>
          </NavDropdown>
        </div>
      </div>
    </Navbar>
  );
};

export default TopNavbar;