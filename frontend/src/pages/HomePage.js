import React from 'react';
import { Container, Row, Col, Card, Badge, Button } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../context/AppContext';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const { systemStatus } = useAppContext();

  return (
    <Container fluid className="py-4">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2 className="mb-0">Dashboard</h2>
            <div className="d-flex align-items-center">
              <Badge 
                bg={systemStatus.isHealthy ? "success" : "danger"} 
                className="py-2 px-3 d-flex align-items-center"
              >
                <FeatherIcon 
                  icon={systemStatus.isHealthy ? "check-circle" : "alert-circle"} 
                  size={16} 
                  className="me-2" 
                />
                <span>System {systemStatus.isHealthy ? "Online" : "Offline"}</span>
              </Badge>
            </div>
          </div>
        </Col>
      </Row>

      {/* Overview Section */}
      <Row className="mb-4">
        <Col md={12}>
          <Card className="shadow-sm border-0">
            <Card.Body className="p-4">
              <h4 className="mb-3">Staples Brain</h4>
              <p className="lead mb-4">
                Welcome to Staples Brain - an advanced multi-agent AI orchestration platform designed for
                intelligent, dynamic interactions across complex computational domains.
              </p>
              <div className="d-flex justify-content-start">
                <Button 
                  as={Link} 
                  to="/documentation" 
                  variant="primary" 
                  className="me-2 d-flex align-items-center"
                >
                  <FeatherIcon icon="book" size={16} className="me-2" />
                  View Documentation
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Key Features Section */}
      <Row className="mb-4">
        <Col xs={12}>
          <h4 className="mb-3">Key Features</h4>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="h-100 shadow-sm border-0">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-primary bg-opacity-10 p-3 me-3">
                  <FeatherIcon icon="layers" size={24} className="text-primary" />
                </div>
                <h5 className="mb-0">Modular Architecture</h5>
              </div>
              <p className="card-text">
                Microservices architecture with intelligent routing and comprehensive state tracking.
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="h-100 shadow-sm border-0">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-success bg-opacity-10 p-3 me-3">
                  <FeatherIcon icon="database" size={24} className="text-success" />
                </div>
                <h5 className="mb-0">Memory Management</h5>
              </div>
              <p className="card-text">
                Redis-powered memory system with sophisticated storage and retrieval mechanisms.
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="h-100 shadow-sm border-0">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-info bg-opacity-10 p-3 me-3">
                  <FeatherIcon icon="cpu" size={24} className="text-info" />
                </div>
                <h5 className="mb-0">AI Integration</h5>
              </div>
              <p className="card-text">
                Enhanced reasoning using LangChain/LangGraph with OpenAI GPT-4o integration.
              </p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* System Status Section */}
      <Row>
        <Col xs={12}>
          <h4 className="mb-3">System Status</h4>
        </Col>
        <Col md={6} className="mb-3">
          <Card className="shadow-sm border-0">
            <Card.Body className="p-4">
              <h5 className="card-title mb-3">Current State</h5>
              <div className="d-flex justify-content-between mb-3">
                <span>API Gateway:</span>
                <Badge bg="success">Online</Badge>
              </div>
              <div className="d-flex justify-content-between mb-3">
                <span>Database Connection:</span>
                <Badge bg="success">Connected</Badge>
              </div>
              <div className="d-flex justify-content-between mb-3">
                <span>Memory Service:</span>
                <Badge bg="success">Operational</Badge>
              </div>
              <div className="d-flex justify-content-between">
                <span>Agent System:</span>
                <Badge bg="success">Running</Badge>
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} className="mb-3">
          <Card className="shadow-sm border-0">
            <Card.Body className="p-4">
              <h5 className="card-title mb-3">Available Agents</h5>
              <div className="d-flex justify-content-between mb-3">
                <span>Package Tracking Agent</span>
                <Badge bg="primary">Ready</Badge>
              </div>
              <div className="d-flex justify-content-between mb-3">
                <span>Password Reset Agent</span>
                <Badge bg="primary">Ready</Badge>
              </div>
              <div className="d-flex justify-content-between mb-3">
                <span>Store Locator Agent</span>
                <Badge bg="primary">Ready</Badge>
              </div>
              <div className="d-flex justify-content-between">
                <span>Product Information Agent</span>
                <Badge bg="primary">Ready</Badge>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default HomePage;