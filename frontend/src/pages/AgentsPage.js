import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, ListGroup, Badge, Button, Spinner, Tabs, Tab, Modal, Form } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { agentService } from '../api/apiService';
import workflowService from '../services/workflow-service';

const AgentsPage = () => {
  const [agents, setAgents] = useState([]);
  const [builderAgents, setBuilderAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isBuilderLoading, setIsBuilderLoading] = useState(true);
  const [error, setError] = useState(null);
  const [builderError, setBuilderError] = useState(null);
  const [activeTab, setActiveTab] = useState('agents');
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  
  // Fetch standard agents on component mount
  useEffect(() => {
    const fetchAgents = async () => {
      setIsLoading(true);
      try {
        const response = await agentService.listAgents();
        if (response.success && response.data && response.data.agents) {
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
  
  // Fetch agent builder agents when builder tab is selected
  useEffect(() => {
    const fetchBuilderAgents = async () => {
      if (activeTab === 'builder') {
        setIsBuilderLoading(true);
        try {
          const response = await agentService.listAgentBuilderAgents();
          if (response.success && response.agents) {
            setBuilderAgents(response.agents);
          } else {
            throw new Error(response.error || 'Failed to load agent builder data');
          }
        } catch (err) {
          setBuilderError(err.message);
          console.error('Error fetching agent builder data:', err);
        } finally {
          setIsBuilderLoading(false);
        }
      }
    };
    
    fetchBuilderAgents();
  }, [activeTab]);
  
  // Get icon for agent type
  const getAgentIcon = (agent) => {
    const name = agent.name.toLowerCase();
    const type = (agent.type || agent.agent_type || '').toLowerCase();
    
    if (name.includes('package') || name.includes('track') || type.includes('package') || type.includes('track')) {
      return 'package';
    } else if (name.includes('password') || name.includes('reset') || type.includes('password') || type.includes('reset')) {
      return 'key';
    } else if (name.includes('store') || name.includes('locat') || type.includes('store') || type.includes('locat')) {
      return 'map-pin';
    } else if (name.includes('product') || name.includes('info') || type.includes('product') || type.includes('info')) {
      return 'shopping-bag';
    } else if (name.includes('return') || type.includes('return')) {
      return 'rotate-ccw';
    } else if (name.includes('guardrail') || type.includes('guardrail')) {
      return 'shield';
    } else if (name.includes('general') || name.includes('conversation') || type.includes('small_talk')) {
      return 'message-circle';
    } else {
      return 'cpu';
    }
  };
  
  // Handle tab change
  const handleTabChange = (key) => {
    setActiveTab(key);
  };
  
  // Handle edit click
  const handleEditClick = (agent) => {
    setSelectedAgent(agent);
    setShowEditModal(true);
  };
  
  // Handle modal close
  const handleCloseModal = () => {
    setShowEditModal(false);
    setSelectedAgent(null);
  };
  
  // Handle save changes
  const handleSaveChanges = async () => {
    // Implement save functionality here
    try {
      await agentService.updateAgentBuilderAgent(selectedAgent.id, selectedAgent);
      // Refresh the agents list after update
      const response = await agentService.listAgentBuilderAgents();
      if (response.success && response.agents) {
        setBuilderAgents(response.agents);
      }
      setShowEditModal(false);
      setSelectedAgent(null);
    } catch (err) {
      console.error('Error updating agent:', err);
      // Show error in modal
    }
  };
  
  // Render loading state
  const renderLoading = (message = 'Loading Agents...') => (
    <Container className="py-5 text-center">
      <Spinner animation="border" role="status" className="mb-3" />
      <h4>{message}</h4>
    </Container>
  );
  
  // Render error state
  const renderError = (errorMessage, retryAction) => (
    <Container className="py-5">
      <div className="alert alert-danger">
        <FeatherIcon icon="alert-triangle" className="me-2" />
        {errorMessage}
      </div>
      <Button variant="primary" onClick={retryAction}>
        Retry
      </Button>
    </Container>
  );
  
  // Render agent cards
  const renderAgentCards = (agentList, isEditable = false) => (
    <Row>
      {agentList.map((agent) => (
        <Col key={agent.id} md={6} lg={4} className="mb-4">
          <Card className="h-100 shadow-sm">
            <Card.Header className="bg-dark text-light">
              <div className="d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center">
                  <div className="rounded-circle bg-primary p-2 me-3">
                    <FeatherIcon icon={getAgentIcon(agent)} size={20} />
                  </div>
                  <div>
                    <h5 className="mb-0">{agent.name}</h5>
                    {agent.is_system ? (
                      <Badge bg="info" className="mt-1">System</Badge>
                    ) : (
                      <Badge bg="warning" className="mt-1">Custom</Badge>
                    )}
                  </div>
                </div>
                {isEditable && (
                  <Button 
                    variant="outline-light" 
                    size="sm"
                    onClick={() => handleEditClick(agent)}
                  >
                    <FeatherIcon icon="edit-2" size={16} />
                  </Button>
                )}
              </div>
            </Card.Header>
            <Card.Body>
              <Card.Text>{agent.description}</Card.Text>
            </Card.Body>
            <ListGroup variant="flush" className="border-top">
              <ListGroup.Item>
                <strong>ID:</strong> {agent.id}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Type:</strong> {agent.type || agent.agent_type || 'Unknown'}
              </ListGroup.Item>
              <ListGroup.Item>
                <strong>Status:</strong> {agent.status || 'Active'}
              </ListGroup.Item>
              {agent.created_at && (
                <ListGroup.Item>
                  <strong>Created:</strong> {new Date(agent.created_at).toLocaleDateString()}
                </ListGroup.Item>
              )}
            </ListGroup>
          </Card>
        </Col>
      ))}
      
      {agentList.length === 0 && (
        <Col md={12}>
          <div className="alert alert-warning">
            <FeatherIcon icon="alert-triangle" className="me-2" />
            No agents found.
          </div>
        </Col>
      )}
    </Row>
  );
  
  // Render modal for editing agent
  const renderEditModal = () => (
    <Modal show={showEditModal} onHide={handleCloseModal} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Edit Agent: {selectedAgent?.name}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {selectedAgent && (
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control 
                type="text" 
                value={selectedAgent.name}
                onChange={(e) => setSelectedAgent({...selectedAgent, name: e.target.value})}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control 
                as="textarea" 
                rows={3}
                value={selectedAgent.description}
                onChange={(e) => setSelectedAgent({...selectedAgent, description: e.target.value})}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Type</Form.Label>
              <Form.Control 
                type="text"
                value={selectedAgent.type || selectedAgent.agent_type}
                onChange={(e) => setSelectedAgent({
                  ...selectedAgent, 
                  type: e.target.value,
                  agent_type: e.target.value
                })}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Status</Form.Label>
              <Form.Select 
                value={selectedAgent.status}
                onChange={(e) => setSelectedAgent({...selectedAgent, status: e.target.value})}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
              </Form.Select>
            </Form.Group>
            
            {/* Additional fields can be added here based on the agent schema */}
          </Form>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleCloseModal}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSaveChanges}>
          Save Changes
        </Button>
      </Modal.Footer>
    </Modal>
  );
  
  return (
    <Container className="py-4">
      <Row className="mb-4">
        <Col>
          <h2 className="mb-4">AI Agents</h2>
          <p className="lead">
            Staples Brain uses specialized AI agents to handle different types of customer inquiries.
            Each agent is trained on specific domains and capabilities.
          </p>
          
          <Tabs
            activeKey={activeTab}
            onSelect={handleTabChange}
            className="mb-4"
          >
            <Tab eventKey="agents" title="All Agents">
              {isLoading ? (
                renderLoading()
              ) : error ? (
                renderError(error, () => window.location.reload())
              ) : (
                renderAgentCards(agents)
              )}
            </Tab>
            
            <Tab eventKey="builder" title="Agent Builder">
              <div className="d-flex justify-content-between mb-4">
                <h4>Agent Builder</h4>
                <Button variant="primary">
                  <FeatherIcon icon="plus" className="me-2" size={16} />
                  Create New Agent
                </Button>
              </div>
              
              {isBuilderLoading ? (
                renderLoading('Loading Agent Builder...')
              ) : builderError ? (
                renderError(builderError, () => {
                  setActiveTab('builder');
                  setIsBuilderLoading(true);
                  agentService.listAgentBuilderAgents()
                    .then(response => {
                      if (response.success && response.agents) {
                        setBuilderAgents(response.agents);
                        setBuilderError(null);
                      }
                    })
                    .catch(err => setBuilderError(err.message))
                    .finally(() => setIsBuilderLoading(false));
                })
              ) : (
                renderAgentCards(builderAgents, true)
              )}
            </Tab>
          </Tabs>
        </Col>
      </Row>
      
      {/* Edit Modal */}
      {renderEditModal()}
    </Container>
  );
};

export default AgentsPage;