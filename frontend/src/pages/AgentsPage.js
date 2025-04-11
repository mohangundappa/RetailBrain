import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, ListGroup, Badge, Button, Spinner } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { agentService } from '../api/apiService';

const AgentsPage = () => {
  const [agents, setAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Fetch agents on component mount
  useEffect(() => {
    const fetchAgents = async () => {
      setIsLoading(true);
      try {
        const response = await agentService.listAgents();
        if (response.success && response.data.agents) {
          setAgents(response.data.agents);
        } else {
          throw new Error(response.error || 'Failed to load agents');
        }
      } catch (err) {
        setError(err.message);
        console.error('Error fetching agents:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchAgents();
  }, []);
  
  // Get icon for agent type
  const getAgentIcon = (agent) => {
    const id = agent.id.toLowerCase();
    if (id.includes('package') || id.includes('track')) {
      return 'package';
    } else if (id.includes('password') || id.includes('reset')) {
      return 'key';
    } else if (id.includes('store') || id.includes('locat')) {
      return 'map-pin';
    } else if (id.includes('product') || id.includes('info')) {
      return 'shopping-bag';
    } else if (id.includes('return')) {
      return 'rotate-ccw';
    } else {
      return 'cpu';
    }
  };
  
  // Render loading state
  if (isLoading) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" role="status" className="mb-3" />
        <h4>Loading Agents...</h4>
      </Container>
    );
  }
  
  // Render error state
  if (error) {
    return (
      <Container className="py-5">
        <div className="alert alert-danger">
          <FeatherIcon icon="alert-triangle" className="me-2" />
          {error}
        </div>
        <Button variant="primary" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </Container>
    );
  }
  
  return (
    <Container className="py-4">
      <Row className="mb-4">
        <Col>
          <h2 className="mb-4">AI Agents</h2>
          <p className="lead">
            Staples Brain uses specialized AI agents to handle different types of customer inquiries.
            Each agent is trained on specific domains and capabilities.
          </p>
        </Col>
      </Row>
      
      <Row>
        {agents.map((agent) => (
          <Col key={agent.id} md={6} lg={4} className="mb-4">
            <Card className="h-100 shadow-sm">
              <Card.Header className="bg-dark text-light">
                <div className="d-flex align-items-center">
                  <div className="rounded-circle bg-primary p-2 me-3">
                    <FeatherIcon icon={getAgentIcon(agent)} size={20} />
                  </div>
                  <div>
                    <h5 className="mb-0">{agent.name}</h5>
                    {agent.is_built_in ? (
                      <Badge bg="info" className="mt-1">Built-in</Badge>
                    ) : (
                      <Badge bg="warning" className="mt-1">Custom</Badge>
                    )}
                  </div>
                </div>
              </Card.Header>
              <Card.Body>
                <Card.Text>{agent.description}</Card.Text>
              </Card.Body>
              <ListGroup variant="flush" className="border-top">
                <ListGroup.Item>
                  <strong>ID:</strong> {agent.id}
                </ListGroup.Item>
                {agent.creator && (
                  <ListGroup.Item>
                    <strong>Creator:</strong> {agent.creator}
                  </ListGroup.Item>
                )}
                {agent.created_at && (
                  <ListGroup.Item>
                    <strong>Created:</strong> {new Date(agent.created_at).toLocaleDateString()}
                  </ListGroup.Item>
                )}
              </ListGroup>
            </Card>
          </Col>
        ))}
        
        {agents.length === 0 && (
          <Col md={12}>
            <div className="alert alert-warning">
              <FeatherIcon icon="alert-triangle" className="me-2" />
              No agents found.
            </div>
          </Col>
        )}
      </Row>
    </Container>
  );
};

export default AgentsPage;