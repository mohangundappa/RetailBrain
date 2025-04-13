import React from 'react';
import { Navbar, Container, Button, Form, InputGroup, Nav, Dropdown } from 'react-bootstrap';
import { useAppContext } from '../../context/AppContext';

/**
 * Top navigation bar component
 * Provides global actions, search, and user menu
 */
const TopNavbar = ({ sidebarOpen, toggleSidebar }) => {
  const { state, actions } = useAppContext();
  
  // Mock user data - would come from context in a real app
  const user = state.user || {
    name: 'Demo User',
    avatar: 'https://via.placeholder.com/36',
    role: 'admin'
  };
  
  // Handle logout
  const handleLogout = () => {
    // In a real app, this would call an API and clear auth state
    actions.addNotification({
      type: 'info',
      title: 'Logged Out',
      message: 'You have been logged out successfully.',
      autoDismiss: true
    });
  };
  
  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="border-bottom">
      <Container fluid>
        <Button 
          variant="link" 
          className="me-2 text-white p-0" 
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {/* This would use a proper icon component */}
          <span className="fs-4">☰</span>
        </Button>
        
        <Navbar.Brand href="#" className="me-auto">
          {!sidebarOpen && 'Staples Brain'}
        </Navbar.Brand>
        
        <div className="d-none d-md-flex flex-grow-1 justify-content-center mx-5">
          <InputGroup style={{ maxWidth: '500px' }}>
            <Form.Control
              placeholder="Search..."
              aria-label="Search"
              className="bg-dark text-white border-secondary"
            />
            <Button variant="outline-secondary">
              🔍
            </Button>
          </InputGroup>
        </div>
        
        <Nav className="ms-auto align-items-center">
          <Nav.Link href="#" className="px-2" title="Notifications">
            🔔
          </Nav.Link>
          
          <Nav.Link href="#" className="px-2" title="Help">
            ❓
          </Nav.Link>
          
          <Dropdown align="end">
            <Dropdown.Toggle as="a" className="nav-link dropdown-toggle d-flex align-items-center" id="user-dropdown">
              <img 
                src={user.avatar} 
                alt={user.name} 
                className="rounded-circle me-2" 
                width="36" 
                height="36" 
              />
              <span className="d-none d-lg-inline">{user.name}</span>
            </Dropdown.Toggle>
            
            <Dropdown.Menu>
              <Dropdown.Item href="#">Profile</Dropdown.Item>
              <Dropdown.Item href="#">Settings</Dropdown.Item>
              <Dropdown.Divider />
              <Dropdown.Item onClick={handleLogout}>Logout</Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </Nav>
      </Container>
    </Navbar>
  );
};

export default TopNavbar;