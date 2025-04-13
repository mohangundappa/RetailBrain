import React from 'react';
import { Container, Row, Col, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';

const NotFound = () => {
  return (
    <Container className="text-center py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <div className="mb-4">
            <FeatherIcon icon="alert-circle" size={64} className="text-secondary mb-3" />
            <h1 className="display-4">404</h1>
            <h2 className="mb-4">Page Not Found</h2>
            <p className="lead mb-4">
              The page you are looking for might have been removed, had its name changed,
              or is temporarily unavailable.
            </p>
            <Button as={Link} to="/" variant="primary" className="d-inline-flex align-items-center">
              <FeatherIcon icon="home" size={18} className="me-2" />
              Return to Dashboard
            </Button>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default NotFound;