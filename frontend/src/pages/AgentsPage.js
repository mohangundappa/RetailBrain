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
  const [workflowData, setWorkflowData] = useState(null);
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(false);
  const [workflowError, setWorkflowError] = useState(null);
  
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
    
    // Fetch workflow data for this agent
    fetchWorkflowData(agent.id);
  };
  
  // Fetch workflow data for an agent
  const fetchWorkflowData = async (agentId) => {
    setIsLoadingWorkflow(true);
    setWorkflowError(null);
    try {
      const data = await workflowService.getWorkflowInfo(agentId);
      console.log('Workflow data:', data);
      setWorkflowData(data);
    } catch (err) {
      console.error('Error fetching workflow data:', err);
      setWorkflowError('Failed to load workflow data');
    } finally {
      setIsLoadingWorkflow(false);
    }
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
                <Button 
                  variant="outline-light" 
                  size="sm"
                  onClick={() => handleEditClick(agent)}
                >
                  <FeatherIcon icon={isEditable ? "edit-2" : "info"} size={16} />
                </Button>
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
  
  // Render workflow content
  const renderWorkflowContent = () => {
    if (isLoadingWorkflow) {
      return (
        <div className="text-center p-4">
          <Spinner animation="border" size="sm" className="me-2" />
          Loading workflow data...
        </div>
      );
    }
    
    if (workflowError) {
      return (
        <div className="alert alert-warning">
          <FeatherIcon icon="alert-triangle" className="me-2" />
          {workflowError}
        </div>
      );
    }
    
    if (!workflowData) {
      return (
        <div className="alert alert-info">
          <FeatherIcon icon="info" className="me-2" />
          No workflow data available for this agent.
        </div>
      );
    }
    
    return (
      <div>
        <h5>{workflowData.name}</h5>
        {workflowData.description && (
          <p className="text-muted">{workflowData.description}</p>
        )}
        
        <div className="mt-3">
          <h6>Workflow Nodes</h6>
          {Object.keys(workflowData.nodes).length > 0 ? (
            <ListGroup>
              {Object.entries(workflowData.nodes).map(([nodeId, node]) => (
                <ListGroup.Item key={nodeId} className="mb-2">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <Badge bg={nodeId === workflowData.entry_node ? 'success' : 'secondary'}>
                      {nodeId} {nodeId === workflowData.entry_node ? '(Entry)' : ''}
                    </Badge>
                    <Badge bg="info">{node.type}</Badge>
                  </div>
                  
                  {node.type === 'prompt' && node.prompt && (
                    <div className="mt-2">
                      <h6>Prompt Template:</h6>
                      <pre className="bg-dark text-light p-2 rounded small" style={{maxHeight: '200px', overflow: 'auto'}}>
                        {node.prompt}
                      </pre>
                    </div>
                  )}
                  
                  {node.config && Object.keys(node.config).length > 0 && (
                    <div className="mt-2">
                      <h6>Configuration:</h6>
                      <pre className="bg-dark text-light p-2 rounded small">
                        {JSON.stringify(node.config, null, 2)}
                      </pre>
                    </div>
                  )}
                </ListGroup.Item>
              ))}
            </ListGroup>
          ) : (
            <p className="text-muted">No workflow nodes defined</p>
          )}
        </div>
        
        {workflowData.edges && Object.keys(workflowData.edges).length > 0 && (
          <div className="mt-3">
            <h6>Workflow Edges</h6>
            <ListGroup>
              {Object.entries(workflowData.edges).map(([sourceId, targets]) => (
                <ListGroup.Item key={sourceId}>
                  <div>
                    <strong>From:</strong> {sourceId}
                  </div>
                  <div>
                    <strong>To:</strong> {targets.map(t => t.target).join(', ')}
                  </div>
                  {targets.some(t => t.condition) && (
                    <div className="mt-1">
                      <strong>Conditions:</strong>
                      <ul className="mb-0">
                        {targets.filter(t => t.condition).map((t, i) => (
                          <li key={i}>{t.target}: {t.condition}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </ListGroup.Item>
              ))}
            </ListGroup>
          </div>
        )}
      </div>
    );
  };

  // Render modal for editing agent
  const renderEditModal = () => (
    <Modal show={showEditModal} onHide={handleCloseModal} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Edit Agent: {selectedAgent?.name}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {selectedAgent && (
          <Tabs defaultActiveKey="details" className="mb-3">
            <Tab eventKey="details" title="Details">
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
              </Form>
            </Tab>
            
            <Tab eventKey="workflow" title="Workflow">
              {renderWorkflowContent()}
            </Tab>
            
            {selectedAgent.persona && (
              <Tab eventKey="persona" title="Persona">
                <pre className="bg-dark text-light p-3 rounded">
                  {JSON.stringify(selectedAgent.persona, null, 2)}
                </pre>
              </Tab>
            )}
            
            {selectedAgent.tools && (
              <Tab eventKey="tools" title="Tools">
                <pre className="bg-dark text-light p-3 rounded">
                  {JSON.stringify(selectedAgent.tools, null, 2)}
                </pre>
              </Tab>
            )}
          </Tabs>
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