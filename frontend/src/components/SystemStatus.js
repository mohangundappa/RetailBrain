import React from 'react';
import { Card, Row, Col, ListGroup, Badge } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../context/AppContext';

const SystemStatus = () => {
  const { systemStatus } = useAppContext();
  
  // Check if system information is loading
  if (systemStatus.isLoading) {
    return (
      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-dark text-light">
          <FeatherIcon icon="activity" className="me-2" />
          System Status
        </Card.Header>
        <Card.Body className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-3">Loading system status...</p>
        </Card.Body>
      </Card>
    );
  }
  
  // Prepare status values
  const status = systemStatus.data || {};
  
  // Determine status icons and colors
  const getStatusBadge = (status, label) => {
    if (status === 'healthy' || status === 'connected' || status === 'configured') {
      return (
        <Badge bg="success" className="d-flex align-items-center">
          <FeatherIcon icon="check-circle" size={12} className="me-1" />
          <span>{label || status}</span>
        </Badge>
      );
    } else {
      return (
        <Badge bg="danger" className="d-flex align-items-center">
          <FeatherIcon icon="alert-circle" size={12} className="me-1" />
          <span>{label || status}</span>
        </Badge>
      );
    }
  };
  
  return (
    <Card className="mb-4 shadow-sm">
      <Card.Header className="bg-dark text-light d-flex justify-content-between align-items-center">
        <div>
          <FeatherIcon icon="activity" className="me-2" />
          System Status
        </div>
        {systemStatus.isHealthy ? (
          <Badge bg="success" pill>Healthy</Badge>
        ) : (
          <Badge bg="danger" pill>Unhealthy</Badge>
        )}
      </Card.Header>
      <Card.Body>
        <Row>
          <Col md={6}>
            <ListGroup variant="flush">
              <ListGroup.Item className="d-flex justify-content-between align-items-center">
                <strong>Environment</strong>
                <Badge bg="info">{status.environment || 'Unknown'}</Badge>
              </ListGroup.Item>
              <ListGroup.Item className="d-flex justify-content-between align-items-center">
                <strong>Version</strong>
                <span>{status.version || 'Unknown'}</span>
              </ListGroup.Item>
            </ListGroup>
          </Col>
          <Col md={6}>
            <ListGroup variant="flush">
              <ListGroup.Item className="d-flex justify-content-between align-items-center">
                <strong>Database</strong>
                {getStatusBadge(status.database)}
              </ListGroup.Item>
              <ListGroup.Item className="d-flex justify-content-between align-items-center">
                <strong>OpenAI API</strong>
                {getStatusBadge(status.openai_api)}
              </ListGroup.Item>
            </ListGroup>
          </Col>
        </Row>
        
        {systemStatus.error && (
          <div className="alert alert-danger mt-3">
            <FeatherIcon icon="alert-triangle" className="me-2" />
            {systemStatus.error}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default SystemStatus;