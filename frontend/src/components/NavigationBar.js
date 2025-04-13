import React from 'react';
import { Navbar, Nav, Container, Badge } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../context/AppContext';

const NavigationBar = () => {
  const location = useLocation();
  const { systemStatus } = useAppContext();
  
  // Check if the current path matches a given path
  const isActive = (path) => location.pathname === path;
  
  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-3 shadow-sm">
      <Container fluid>
        <Navbar.Brand as={Link} to="/" className="d-flex align-items-center">
          <FeatherIcon icon="activity" size={24} className="me-2 text-primary" />
          <span className="fw-bold">Staples Brain</span>
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
              <FeatherIcon icon="home" size={16} className="me-1" />
              <span>Home</span>
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
                  <span>System Online</span>
                </Badge>
              ) : (
                <Badge bg="danger" className="d-flex align-items-center py-2 px-3">
                  <FeatherIcon icon="alert-circle" size={14} className="me-1" />
                  <span>System Offline</span>
                </Badge>
              )}
            </div>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default NavigationBar;