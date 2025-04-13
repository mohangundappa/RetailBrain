import React, { useEffect, useState } from 'react';
import { Container, Row, Col, Card, Badge, Button, Table } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';
import apiService from '../../api/apiService';
import axios from 'axios';

// Create direct API client
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

const AgentOverview = () => {
  const { agents, setAgents, setLoading, addNotification } = useAppContext();
  const [selectedAgent, setSelectedAgent] = useState(null);

  // Create reusable fetchAgents function
  const fetchAgents = async () => {
    try {
      console.log('AgentOverview: Fetching agents from API...');
      setLoading(true);
      
      // ADD A DEBUG ALERT FOR IMMEDIATE FEEDBACK
      console.log('DEBUG: Making API call to fetch agents at:', new Date().toISOString());
      
      try {
        // Force a direct API request without using cached data
        const response = await api.get('/agents');
        const responseData = response.data;
        console.log('AgentOverview: API response:', responseData);
        
        if (responseData.success && responseData.agents) {
          console.log('AgentOverview: Setting agents:', responseData.agents);
          // Find system agents for debugging
          const systemAgents = responseData.agents.filter(a => a.is_system);
          console.log('AgentOverview: System agents found:', systemAgents.length, systemAgents);
          
          setAgents(responseData.agents);
          alert('Successfully loaded ' + responseData.agents.length + ' agents including ' + 
                systemAgents.length + ' system agents');
        } else {
          throw new Error('Failed to fetch agents - success flag false');
        }
      } catch (networkError) {
        console.error('Network error details:', networkError);
        if (networkError.response) {
          console.error('Response data:', networkError.response.data);
          console.error('Response status:', networkError.response.status);
          console.error('Response headers:', networkError.response.headers);
        } else if (networkError.request) {
          console.error('Request was made but no response was received');
          console.error('Request details:', networkError.request);
        } else {
          console.error('Error setting up request:', networkError.message);
        }
        throw networkError;
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
      console.log('Error fetching agents stack:', error.stack);
      alert('Error loading agents: ' + error.message);
      addNotification({
        title: 'Error',
        message: 'Failed to load agents. Please try again later. Error: ' + error.message,
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Fetch agents on component mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    fetchAgents();
  }, []);

  const handleAgentSelect = async (agent) => {
    try {
      setLoading(true);
      const response = await apiService.apiCall(apiService.getAgentDetails, agent.id);
      
      if (response.success && response.data) {
        setSelectedAgent(response.data);
      } else {
        throw new Error('Failed to fetch agent details');
      }
    } catch (error) {
      console.error('Error fetching agent details:', error);
      addNotification({
        title: 'Error',
        message: 'Failed to load agent details. Please try again later.',
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <Badge bg="success">Active</Badge>;
      case 'inactive':
        return <Badge bg="secondary">Inactive</Badge>;
      case 'error':
        return <Badge bg="danger">Error</Badge>;
      default:
        return <Badge bg="primary">Unknown</Badge>;
    }
  };

  return (
    <Container fluid className="p-4">
      <h1 className="h3 mb-4">Agent Overview</h1>
      
      <Row>
        <Col md={12} lg={selectedAgent ? 6 : 12}>
          <Card className="mb-4">
            <Card.Header className="bg-transparent d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Available Agents</h5>
              <div>
                <Button 
                  variant="outline-primary" 
                  size="sm" 
                  onClick={fetchAgents}
                >
                  <FeatherIcon icon="refresh-cw" size={16} className="me-1" />
                  Refresh
                </Button>
              </div>
            </Card.Header>
            <Card.Body>
              {agents && agents.length > 0 ? (
                <Table responsive hover>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Category</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((agent, index) => (
                      <tr key={agent.id || index}>
                        <td>
                          {agent.name}
                          {agent.is_system && (
                            <Badge bg="info" className="ms-2">System</Badge>
                          )}
                        </td>
                        <td>{agent.type || 'Standard'}</td>
                        <td>
                          {(() => {
                            const type = agent.type?.toLowerCase() || '';
                            if (type.includes('package') || type.includes('track')) {
                              return 'Package Tracking';
                            } else if (type.includes('password') || type.includes('reset')) {
                              return 'Account Management';
                            } else if (type.includes('store') || type.includes('locat')) {
                              return 'Store Information';
                            } else if (type.includes('product') || type.includes('info')) {
                              return 'Product Support';
                            } else if (type.includes('return')) {
                              return 'Customer Support';
                            } else if (type.includes('policy') || type.includes('guard')) {
                              return 'Policy Enforcement';
                            } else if (type.includes('llm') || type.includes('conversation')) {
                              return 'General Conversation';
                            } else {
                              return 'Other';
                            }
                          })()}
                        </td>
                        <td>{getStatusBadge(agent.status)}</td>
                        <td>
                          <Button 
                            variant="link" 
                            size="sm"
                            className="p-0 me-2"
                            onClick={() => handleAgentSelect(agent)}
                          >
                            <FeatherIcon icon="info" size={16} />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <div className="text-center py-5">
                  <FeatherIcon icon="cpu" size={48} className="text-muted mb-3" />
                  <h5>No agents available</h5>
                  <p className="text-muted">
                    There are currently no agents configured or we couldn't fetch the agent list.
                  </p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
        
        {selectedAgent && (
          <Col md={12} lg={6}>
            <Card className="mb-4">
              <Card.Header className="bg-transparent d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Agent Details</h5>
                <Button 
                  variant="close" 
                  onClick={() => setSelectedAgent(null)}
                />
              </Card.Header>
              <Card.Body>
                <div className="mb-4">
                  <h3 className="mb-1">{selectedAgent.name}</h3>
                  <div className="mb-3">
                    {getStatusBadge(selectedAgent.status)}
                    {selectedAgent.is_system && (
                      <Badge bg="info" className="ms-2">System Agent</Badge>
                    )}
                  </div>
                  
                  <p className="text-muted">{selectedAgent.description || 'No description available'}</p>
                </div>
                
                <h6 className="mb-3">Agent Information</h6>
                <Table bordered size="sm">
                  <tbody>
                    <tr>
                      <th>ID</th>
                      <td>{selectedAgent.id}</td>
                    </tr>
                    <tr>
                      <th>Type</th>
                      <td>{selectedAgent.type || 'N/A'}</td>
                    </tr>
                    <tr>
                      <th>Version</th>
                      <td>{selectedAgent.version || '1.0'}</td>
                    </tr>
                    <tr>
                      <th>Created</th>
                      <td>{selectedAgent.created_at || 'N/A'}</td>
                    </tr>
                    <tr>
                      <th>DB Driven</th>
                      <td>{selectedAgent.db_driven ? 'Yes' : 'No'}</td>
                    </tr>
                  </tbody>
                </Table>
                
                <div className="d-grid gap-2 mt-4">
                  <Button variant="primary">
                    <FeatherIcon icon="message-square" size={16} className="me-2" />
                    Chat with Agent
                  </Button>
                </div>
              </Card.Body>
            </Card>
          </Col>
        )}
      </Row>
    </Container>
  );
};

export default AgentOverview;