import React from 'react';
import { Container, Row, Col, Card, Nav } from 'react-bootstrap';
import { useAppContext } from '../context/AppContext';

const DocumentationPage = () => {
  const [activeSection, setActiveSection] = React.useState('overview');
  const { actions } = useAppContext();

  // Simulate documentation being loaded from API
  React.useEffect(() => {
    actions.addNotification({
      type: 'info',
      title: 'Documentation',
      message: 'Documentation loaded successfully.',
      autoDismiss: true
    });
  }, [actions]);

  const handleNavClick = (section) => {
    setActiveSection(section);
    // Scroll to section
    document.getElementById(section)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <Container fluid>
      <Row>
        <Col md={3} lg={2} className="doc-sidebar p-3 border-end">
          <h5 className="mb-3">Documentation</h5>
          <Nav className="flex-column">
            <Nav.Link 
              className={activeSection === 'overview' ? 'active' : ''} 
              onClick={() => handleNavClick('overview')}
            >
              Overview
            </Nav.Link>
            <Nav.Link 
              className={activeSection === 'architecture' ? 'active' : ''} 
              onClick={() => handleNavClick('architecture')}
            >
              Architecture
            </Nav.Link>
            <Nav.Link 
              className={activeSection === 'agents' ? 'active' : ''} 
              onClick={() => handleNavClick('agents')}
            >
              Agent System
            </Nav.Link>
            <Nav.Link 
              className={activeSection === 'memory' ? 'active' : ''} 
              onClick={() => handleNavClick('memory')}
            >
              Memory Service
            </Nav.Link>
            <Nav.Link 
              className={activeSection === 'api' ? 'active' : ''} 
              onClick={() => handleNavClick('api')}
            >
              API Documentation
            </Nav.Link>
            <Nav.Link 
              className={activeSection === 'frontend' ? 'active' : ''} 
              onClick={() => handleNavClick('frontend')}
            >
              Frontend Integration
            </Nav.Link>
          </Nav>
        </Col>
        <Col md={9} lg={10} className="doc-content">
          <div id="overview" className="doc-section">
            <h2>Overview</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>Staples Brain</h4>
                <p>
                  Staples Brain is an AI super-brain agent system designed specifically for Staples Customer Engagement 
                  focusing on Sales and Services. It's a comprehensive, integrated platform that combines multiple 
                  specialized agents through a central orchestration system.
                </p>
                <p>
                  The system allows dynamic creation and management of agents through database-driven configurations,
                  eliminating the need for code changes when adding or modifying agents.
                </p>
              </Card.Body>
            </Card>
          </div>
          
          <div id="architecture" className="doc-section">
            <h2>Architecture</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>System Architecture</h4>
                <p>
                  The Staples Brain architecture follows a modular approach with several key components:
                </p>
                <ul>
                  <li><strong>API Gateway</strong>: Entry point for all API interactions</li>
                  <li><strong>Brain Service</strong>: Core orchestration for agent coordination</li>
                  <li><strong>Memory Service</strong>: State persistence across interactions</li>
                  <li><strong>Agent Repository</strong>: Database-driven agent management</li>
                  <li><strong>Telemetry Service</strong>: Comprehensive logging and analytics</li>
                </ul>
              </Card.Body>
            </Card>
          </div>
          
          <div id="agents" className="doc-section">
            <h2>Agent System</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>Database-Driven Agent Configuration</h4>
                <p>
                  Agents in Staples Brain are defined through database configurations rather than hardcoded 
                  implementations. This approach provides several benefits:
                </p>
                <ul>
                  <li>Dynamic creation and modification of agents without code changes</li>
                  <li>Centralized management through admin interfaces</li>
                  <li>Version control and history tracking</li>
                  <li>Ability to enable/disable agents without deployment</li>
                </ul>
                
                <h5 className="mt-4">Available Agents</h5>
                <ul>
                  <li><strong>Order Tracking Agent</strong>: Tracks package status and delivery information</li>
                  <li><strong>Reset Password Agent</strong>: Helps customers reset their passwords</li>
                  <li><strong>Store Locator Agent</strong>: Finds nearest stores and provides information</li>
                  <li><strong>Product Information Agent</strong>: Retrieves product details and recommendations</li>
                  <li><strong>Returns Processing Agent</strong>: Assists with return requests and policies</li>
                </ul>
              </Card.Body>
            </Card>
          </div>
          
          <div id="memory" className="doc-section">
            <h2>Memory Service</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>Multi-tier Memory System</h4>
                <p>
                  The memory system in Staples Brain is designed with multiple tiers for different purposes:
                </p>
                <ul>
                  <li><strong>Working Memory (Redis)</strong>: 5-minute TTL for immediate context</li>
                  <li><strong>Short-term Memory (Redis)</strong>: 1-hour TTL for ongoing sessions</li>
                  <li><strong>Archival Storage (PostgreSQL)</strong>: Persistent storage for analytics and training</li>
                </ul>
                
                <h5 className="mt-4">Memory Architecture</h5>
                <p>
                  The memory system uses a key-value approach with namespace support for isolation.
                  Memory entries can be tagged for efficient retrieval and organized by conversation context.
                </p>
              </Card.Body>
            </Card>
          </div>
          
          <div id="api" className="doc-section">
            <h2>API Documentation</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>API Endpoints</h4>
                <p>
                  The API follows RESTful conventions with consistent response formats.
                  All endpoints are available under the <code>/api/v1</code> prefix.
                </p>
                
                <h5 className="mt-4">Key Endpoints</h5>
                <ul>
                  <li><code>/agents</code> - List available agents</li>
                  <li><code>/chat/sessions</code> - Manage chat sessions</li>
                  <li><code>/chat/messages</code> - Send and receive messages</li>
                  <li><code>/memory/{'{conversationId}'}</code> - Access conversation memory</li>
                  <li><code>/telemetry/sessions</code> - View telemetry sessions</li>
                </ul>
              </Card.Body>
            </Card>
          </div>
          
          <div id="frontend" className="doc-section">
            <h2>Frontend Integration</h2>
            <Card className="mb-4">
              <Card.Body>
                <h4>React Integration</h4>
                <p>
                  The frontend is built with React and includes several key components:
                </p>
                <ul>
                  <li><strong>Chat Interface</strong>: Interactive messaging with agents</li>
                  <li><strong>Dashboard</strong>: System status and performance metrics</li>
                  <li><strong>Observability</strong>: Detailed view of agent interactions</li>
                  <li><strong>Agent Builder</strong>: Interface for creating and managing agents</li>
                </ul>
                
                <h5 className="mt-4">API Hooks</h5>
                <p>
                  Custom hooks like <code>useApi</code> and <code>useChat</code> simplify frontend integration.
                  These hooks provide loading states, error handling, and automatic data refreshing.
                </p>
              </Card.Body>
            </Card>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default DocumentationPage;