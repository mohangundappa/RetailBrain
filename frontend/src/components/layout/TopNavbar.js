import React from 'react';
import { Navbar, Container, Nav, NavDropdown, Form, Button } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';

const TopNavbar = () => {
  const { user, addNotification } = useAppContext();

  const handleSearch = (e) => {
    e.preventDefault();
    const query = e.target.elements.search.value;
    
    if (query.trim()) {
      // Implement search functionality
      addNotification({
        title: 'Search',
        message: `Searching for: ${query}`,
        type: 'info'
      });
    }
  };

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="border-bottom border-secondary">
      <Container fluid>
        <Navbar.Brand href="/" className="d-flex align-items-center">
          <FeatherIcon icon="cpu" className="me-2" />
          <span className="d-none d-sm-inline">Staples Brain</span>
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="navbar-nav" />
        
        <Navbar.Collapse id="navbar-nav">
          <Form className="d-flex mx-auto" style={{ maxWidth: '400px' }} onSubmit={handleSearch}>
            <Form.Control
              type="search"
              placeholder="Search..."
              className="me-2"
              aria-label="Search"
              name="search"
            />
            <Button variant="outline-light" type="submit">
              <FeatherIcon icon="search" size={16} />
            </Button>
          </Form>
          
          <Nav className="ms-auto">
            <Nav.Link href="#notifications" className="position-relative">
              <FeatherIcon icon="bell" />
              <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                2
              </span>
            </Nav.Link>
            
            <NavDropdown 
              title={
                <div className="d-inline-block">
                  <FeatherIcon icon="user" className="me-1" />
                  <span className="d-none d-md-inline">{user?.name || 'Guest'}</span>
                </div>
              } 
              id="user-dropdown"
              align="end"
            >
              <NavDropdown.Item href="#profile">
                <FeatherIcon icon="user" size={16} className="me-2" />
                Profile
              </NavDropdown.Item>
              <NavDropdown.Item href="#settings">
                <FeatherIcon icon="settings" size={16} className="me-2" />
                Settings
              </NavDropdown.Item>
              <NavDropdown.Divider />
              <NavDropdown.Item href="#logout">
                <FeatherIcon icon="log-out" size={16} className="me-2" />
                Logout
              </NavDropdown.Item>
            </NavDropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default TopNavbar;