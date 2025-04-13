import React, { useEffect, useState } from 'react';
import { Container, Row, Col, Card, Badge, Button, Spinner } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';

// Import services for API calls
import { healthService, agentService } from '../api/apiService';
import useApi from '../hooks/useApi';

// Mock icon component until we install feather-icons-react
const Icon = ({ name, size = 16, className = '' }) => (
  <span className={`icon ${className}`} style={{ fontSize: `${size}px` }}>
    {name === 'book' && '📖'}
    {name === 'layers' && '🔄'}
    {name === 'database' && '💾'}
    {name === 'cpu' && '🧠'}
    {name === 'check-circle' && '✅'}
    {name === 'alert-circle' && '⚠️'}
    {name === 'message-square' && '💬'}
    {name === 'activity' && '📊'}
  </span>
);

// Statistic Card Component
const StatCard = ({ title, value, icon, color = 'primary', loading = false }) => (
  <Card className="stat-card h-100 shadow-sm border-0">
    <Card.Body className="p-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="card-title mb-0">{title}</h5>
        <div className={`rounded-circle bg-${color} bg-opacity-10 p-2`}>
          <Icon name={icon} size={20} className={`text-${color}`} />
        </div>
      </div>
      <div className="d-flex align-items-end">
        {loading ? (
          <Spinner animation="border" variant={color} size="sm" />
        ) : (
          <h3 className="mb-0">{value}</h3>
        )}
      </div>
    </Card.Body>
  </Card>
);

const HomePage = () => {
  const { state, actions } = useAppContext();
  const [agents, setAgents] = useState([]);
  const [components, setComponents] = useState({
    api: { status: 'online', label: 'Online' },
    database: { status: 'connected', label: 'Connected' },
    memory: { status: 'operational', label: 'Operational' },
    agentSystem: { status: 'running', label: 'Running' }
  });
  
  // API calls using our custom hook
  const { data: healthData, loading: healthLoading, execute: checkHealth } = useApi(
    healthService.getStatus,
    [],
    true
  );
  
  const { data: agentsData, loading: agentsLoading, execute: fetchAgents } = useApi(
    agentService.listAgents,
    [],
    true
  );
  
  // Update system status when health data is available
  useEffect(() => {
    if (healthData && healthData.success) {
      actions.updateSystemStatus({
        isHealthy: healthData.data?.isHealthy || true,
        lastCheck: Date.now()
      });
      
      // If component-specific status is available
      if (healthData.data?.components) {
        setComponents(healthData.data.components);
      }
    }
  }, [healthData, actions]);
  
  // Update agents when data is available
  useEffect(() => {
    if (agentsData && agentsData.success && agentsData.agents) {
      setAgents(agentsData.agents);
    }
  }, [agentsData]);
  
  // Refresh data periodically
  useEffect(() => {
    if (state.preferences.autoRefresh) {
      const intervalId = setInterval(() => {
        checkHealth();
        fetchAgents();
      }, state.preferences.refreshInterval);
      
      return () => clearInterval(intervalId);
    }
  }, [state.preferences, checkHealth, fetchAgents]);
  
  // Show a notification if system is unhealthy
  useEffect(() => {
    if (healthData && !healthData.data?.isHealthy) {
      actions.addNotification({
        type: 'warning',
        title: 'System Status Warning',
        message: 'Some system components may be experiencing issues.',
        autoDismiss: true
      });
    }
  }, [healthData, actions]);

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">Dashboard</h2>
        <div className="d-flex align-items-center">
          <Badge 
            bg={state.systemStatus.isHealthy ? "success" : "danger"} 
            className="py-2 px-3 d-flex align-items-center"
          >
            <Icon 
              name={state.systemStatus.isHealthy ? "check-circle" : "alert-circle"} 
              size={16} 
              className="me-2" 
            />
            <span>System {state.systemStatus.isHealthy ? "Online" : "Offline"}</span>
          </Badge>
        </div>
      </div>

      {/* Stats Overview */}
      <Row className="mb-4">
        <Col md={3} sm={6} className="mb-3 mb-md-0">
          <StatCard 
            title="Agents" 
            value={agentsLoading ? '...' : agents.length || 0} 
            icon="layers" 
            color="primary"
            loading={agentsLoading} 
          />
        </Col>
        <Col md={3} sm={6} className="mb-3 mb-md-0">
          <StatCard 
            title="Active Sessions" 
            value="12" 
            icon="message-square" 
            color="success" 
          />
        </Col>
        <Col md={3} sm={6} className="mb-3 mb-md-0">
          <StatCard 
            title="Conversations" 
            value="87" 
            icon="message-square" 
            color="info" 
          />
        </Col>
        <Col md={3} sm={6}>
          <StatCard 
            title="Response Time" 
            value="1.2s" 
            icon="activity" 
            color="warning" 
          />
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
                Staples Customer Engagement focusing on Sales and Services.
              </p>
              <div className="d-flex justify-content-start">
                <Button 
                  as={Link} 
                  to="/documentation" 
                  variant="primary" 
                  className="me-2 d-flex align-items-center"
                >
                  <Icon name="book" size={16} className="me-2" />
                  View Documentation
                </Button>
                <Button 
                  as={Link} 
                  to="/chat" 
                  variant="outline-primary" 
                  className="d-flex align-items-center"
                >
                  <Icon name="message-square" size={16} className="me-2" />
                  Start Chat
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
          <Card className="h-100 shadow-sm border-0 card-hover">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-primary bg-opacity-10 p-3 me-3">
                  <Icon name="layers" size={24} className="text-primary" />
                </div>
                <h5 className="mb-0">Modular Architecture</h5>
              </div>
              <p className="card-text">
                Centralized orchestration system for specialized agents (Order Tracking, Reset Password, Store Locator) with LangChain and LangGraph integration.
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="h-100 shadow-sm border-0 card-hover">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-success bg-opacity-10 p-3 me-3">
                  <Icon name="database" size={24} className="text-success" />
                </div>
                <h5 className="mb-0">Dynamic Agent Creation</h5>
              </div>
              <p className="card-text">
                Database-driven agent configurations for flexible agent management without code changes. Deploy and modify agents through the dashboard.
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4} className="mb-3">
          <Card className="h-100 shadow-sm border-0 card-hover">
            <Card.Body className="p-4">
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-info bg-opacity-10 p-3 me-3">
                  <Icon name="cpu" size={24} className="text-info" />
                </div>
                <h5 className="mb-0">Advanced Memory System</h5>
              </div>
              <p className="card-text">
                Redis for working memory (5-min TTL) and short-term memory (1-hour TTL), with PostgreSQL for archival storage and analytics.
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
              <h5 className="card-title mb-3">Component Status</h5>
              {healthLoading ? (
                <div className="d-flex justify-content-center py-4">
                  <Spinner animation="border" variant="primary" />
                </div>
              ) : (
                <>
                  <div className="d-flex justify-content-between mb-3">
                    <span>API Gateway:</span>
                    <Badge bg="success">{components.api?.label || 'Online'}</Badge>
                  </div>
                  <div className="d-flex justify-content-between mb-3">
                    <span>Database Connection:</span>
                    <Badge bg="success">{components.database?.label || 'Connected'}</Badge>
                  </div>
                  <div className="d-flex justify-content-between mb-3">
                    <span>Memory Service:</span>
                    <Badge bg="success">{components.memory?.label || 'Operational'}</Badge>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span>Agent System:</span>
                    <Badge bg="success">{components.agentSystem?.label || 'Running'}</Badge>
                  </div>
                </>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} className="mb-3">
          <Card className="shadow-sm border-0">
            <Card.Body className="p-4">
              <h5 className="card-title mb-3">Available Agents</h5>
              {agentsLoading ? (
                <div className="d-flex justify-content-center py-4">
                  <Spinner animation="border" variant="primary" />
                </div>
              ) : agents.length > 0 ? (
                agents.slice(0, 5).map((agent, index) => (
                  <div key={agent.id || index} className="d-flex justify-content-between mb-3">
                    <span>{agent.name}</span>
                    <Badge bg="primary">Ready</Badge>
                  </div>
                ))
              ) : (
                <>
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
                </>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HomePage;