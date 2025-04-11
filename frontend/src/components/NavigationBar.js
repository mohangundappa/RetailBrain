import React from 'react';
import { Navbar, Nav, Container, Button, Badge } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../context/AppContext';

const NavigationBar = () => {
  const location = useLocation();
  const { systemStatus, startNewConversation } = useAppContext();
  
  // Check if the current path matches a given path
  const isActive = (path) => location.pathname === path;
  
  // Handler for starting a new conversation
  const handleNewChat = () => {
    startNewConversation();
  };
  
  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-3 shadow-sm">
      <Container fluid>
        <Navbar.Brand as={Link} to="/" className="d-flex align-items-center">
          <img
            src="/logo192.png"
            width="30"
            height="30"
            className="d-inline-block align-top me-2"
            alt="Staples Brain Logo"
          />
          <span>Staples Brain</span>
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link 
              as={Link} 
              to="/" 
              active={isActive('/')}
              className="d-flex align-items-center"
            >
              <FeatherIcon icon="message-square" size={16} className="me-1" />
              <span>Chat</span>
            </Nav.Link>
            
            <Nav.Link 
              as={Link} 
              to="/agents" 
              active={isActive('/agents')}
              className="d-flex align-items-center"
            >
              <FeatherIcon icon="users" size={16} className="me-1" />
              <span>Agents</span>
            </Nav.Link>
            
            <Nav.Link 
              as={Link} 
              to="/telemetry" 
              active={isActive('/telemetry')}
              className="d-flex align-items-center"
            >
              <FeatherIcon icon="activity" size={16} className="me-1" />
              <span>Telemetry</span>
            </Nav.Link>
            
            <Nav.Link 
              as={Link} 
              to="/documentation" 
              active={isActive('/documentation')}
              className="d-flex align-items-center"
            >
              <FeatherIcon icon="book" size={16} className="me-1" />
              <span>Documentation</span>
            </Nav.Link>
          </Nav>
          
          <Nav className="d-flex align-items-center">
            <div className="me-3">
              {systemStatus.isHealthy ? (
                <Badge bg="success" className="d-flex align-items-center py-2 px-3">
                  <FeatherIcon icon="check-circle" size={14} className="me-1" />
                  <span>System Healthy</span>
                </Badge>
              ) : (
                <Badge bg="danger" className="d-flex align-items-center py-2 px-3">
                  <FeatherIcon icon="alert-circle" size={14} className="me-1" />
                  <span>System Unhealthy</span>
                </Badge>
              )}
            </div>
            
            <Button 
              variant="outline-light" 
              size="sm" 
              onClick={handleNewChat}
              className="d-flex align-items-center"
            >
              <FeatherIcon icon="plus" size={14} className="me-1" />
              <span>New Chat</span>
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default NavigationBar;