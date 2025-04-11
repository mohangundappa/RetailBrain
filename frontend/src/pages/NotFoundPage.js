import React from 'react';
import { Container, Row, Col, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';

const NotFoundPage = () => {
  return (
    <Container className="py-5 text-center">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <div className="my-5">
            <FeatherIcon icon="alert-triangle" size={64} className="text-warning mb-4" />
            <h1 className="display-1 fw-bold">404</h1>
            <h2 className="mb-4">Page Not Found</h2>
            <p className="lead mb-5">
              The page you are looking for doesn't exist or has been moved.
            </p>
            <Button as={Link} to="/" variant="primary" size="lg" className="px-5">
              <FeatherIcon icon="home" className="me-2" />
              Go Home
            </Button>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default NotFoundPage;