import React from 'react';
import { Container, Row, Col, Card, Nav, Tab } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';

const DocumentationPage = () => {
  return (
    <Container className="py-4">
      <h2 className="mb-4">Documentation</h2>
      
      <Tab.Container defaultActiveKey="overview">
        <Row>
          <Col md={3} className="mb-4">
            <Card className="shadow-sm">
              <Card.Header className="bg-dark text-light">
                <FeatherIcon icon="book" className="me-2" />
                Documentation
              </Card.Header>
              <Card.Body className="p-0">
                <Nav variant="pills" className="flex-column p-2">
                  <Nav.Item>
                    <Nav.Link eventKey="overview">Overview</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="architecture">Architecture</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="agents">Agents</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="api">API Reference</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="setup">Setup Guide</Nav.Link>
                  </Nav.Item>
                </Nav>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={9}>
            <Card className="shadow-sm">
              <Card.Body>
                <Tab.Content>
                  <Tab.Pane eventKey="overview">
                    <h4>Staples Brain Overview</h4>
                    <p className="lead">
                      Staples Brain is an advanced multi-agent AI orchestration platform designed to provide intelligent
                      system management and dynamic resilience through cutting-edge technological integration.
                    </p>
                    
                    <h5>Core Components</h5>
                    <ul>
                      <li><strong>API Gateway</strong>: Serves as the entry point for all API interactions with standardized request/response format</li>
                      <li><strong>Staples Brain Core</strong>: Central orchestration component that manages agent selection and processing</li>
                      <li><strong>Specialized Agents</strong>: Individual AI agents focused on specific tasks like package tracking, password reset, etc.</li>
                      <li><strong>Telemetry System</strong>: Comprehensive monitoring and analytics for system performance</li>
                      <li><strong>Database Layer</strong>: PostgreSQL with PgVector for efficient vector storage and similarity search</li>
                    </ul>
                    
                    <h5>Key Features</h5>
                    <ul>
                      <li>Intelligent agent selection based on user intent</li>
                      <li>Robust error handling and fallback mechanisms</li>
                      <li>Comprehensive telemetry and monitoring</li>
                      <li>Vector-based similarity search for context retrieval</li>
                      <li>Scalable and extensible architecture</li>
                    </ul>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="architecture">
                    <h4>System Architecture</h4>
                    <p>
                      Staples Brain follows a modern, clean architecture with clear separation between UI and backend components.
                    </p>
                    
                    <h5>Architecture Layers</h5>
                    <div className="p-3 mb-3 border rounded bg-light">
                      <pre className="mb-0">[UI Layer] → [API Gateway] → [Service Layer] → [Staples Brain] → [Orchestrator] → [Agents] → [External APIs]</pre>
                    </div>
                    
                    <h5>Technology Stack</h5>
                    <div className="row">
                      <div className="col-md-6">
                        <h6>Backend</h6>
                        <ul>
                          <li>Python 3.12+</li>
                          <li>FastAPI</li>
                          <li>SQLAlchemy</li>
                          <li>PostgreSQL with PgVector</li>
                          <li>LangChain / LangGraph</li>
                          <li>OpenAI GPT-4o</li>
                        </ul>
                      </div>
                      <div className="col-md-6">
                        <h6>Frontend</h6>
                        <ul>
                          <li>React</li>
                          <li>React Router</li>
                          <li>Bootstrap</li>
                          <li>Axios</li>
                          <li>Chart.js</li>
                          <li>Feather Icons</li>
                        </ul>
                      </div>
                    </div>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="agents">
                    <h4>Agent System</h4>
                    <p>
                      Staples Brain uses a multi-agent architecture where specialized agents handle different types of user requests.
                    </p>
                    
                    <h5>Built-in Agents</h5>
                    <ul>
                      <li>
                        <strong>Package Tracking Agent</strong>
                        <p>Handles order and package tracking requests, extracts tracking numbers, and provides shipping status updates.</p>
                      </li>
                      <li>
                        <strong>Password Reset Agent</strong>
                        <p>Assists users with password reset procedures for various Staples systems and accounts.</p>
                      </li>
                      <li>
                        <strong>Store Locator Agent</strong>
                        <p>Helps users find nearby Staples stores, providing location details, hours, and available services.</p>
                      </li>
                      <li>
                        <strong>Product Information Agent</strong>
                        <p>Provides detailed information about Staples products, specifications, and availability.</p>
                      </li>
                    </ul>
                    
                    <h5>Agent Selection</h5>
                    <p>
                      The Orchestrator component analyzes user input to determine the most appropriate agent using:
                    </p>
                    <ul>
                      <li>Confidence scoring</li>
                      <li>Intent classification</li>
                      <li>Keyword matching</li>
                      <li>Context analysis</li>
                    </ul>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="api">
                    <h4>API Reference</h4>
                    <p>
                      Staples Brain exposes a standardized API for interacting with the system.
                    </p>
                    
                    <h5>Base URL</h5>
                    <code>/api/v1</code>
                    
                    <h5>Authentication</h5>
                    <p>Currently, API endpoints do not require authentication. This will be added in a future update.</p>
                    
                    <h5>Endpoints</h5>
                    <table className="table table-striped">
                      <thead>
                        <tr>
                          <th>Endpoint</th>
                          <th>Method</th>
                          <th>Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><code>/health</code></td>
                          <td>GET</td>
                          <td>System health check</td>
                        </tr>
                        <tr>
                          <td><code>/chat/messages</code></td>
                          <td>POST</td>
                          <td>Send a message to the brain</td>
                        </tr>
                        <tr>
                          <td><code>/chat/history/{session_id}</code></td>
                          <td>GET</td>
                          <td>Get conversation history for a session</td>
                        </tr>
                        <tr>
                          <td><code>/agents</code></td>
                          <td>GET</td>
                          <td>List available agents</td>
                        </tr>
                        <tr>
                          <td><code>/telemetry/sessions</code></td>
                          <td>GET</td>
                          <td>List telemetry sessions</td>
                        </tr>
                        <tr>
                          <td><code>/telemetry/sessions/{session_id}/events</code></td>
                          <td>GET</td>
                          <td>Get events for a telemetry session</td>
                        </tr>
                        <tr>
                          <td><code>/stats</code></td>
                          <td>GET</td>
                          <td>Get system statistics</td>
                        </tr>
                      </tbody>
                    </table>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="setup">
                    <h4>Setup Guide</h4>
                    <p>
                      Follow these steps to set up the Staples Brain system for local development or production deployment.
                    </p>
                    
                    <h5>Prerequisites</h5>
                    <ul>
                      <li>Python 3.12 or higher</li>
                      <li>PostgreSQL database</li>
                      <li>OpenAI API key</li>
                      <li>Node.js and npm (for frontend)</li>
                    </ul>
                    
                    <h5>Installation Steps</h5>
                    <ol>
                      <li>
                        <strong>Clone Repository</strong>
                        <pre>git clone https://github.com/your-org/staples-brain.git</pre>
                      </li>
                      <li>
                        <strong>Install Backend Dependencies</strong>
                        <pre>pip install -r requirements.txt</pre>
                      </li>
                      <li>
                        <strong>Configure Environment Variables</strong>
                        <pre>cp .env.example .env
# Edit .env with your settings</pre>
                      </li>
                      <li>
                        <strong>Initialize Database</strong>
                        <pre>python -m database.db create_tables</pre>
                      </li>
                      <li>
                        <strong>Start API Gateway</strong>
                        <pre>python start_api.py</pre>
                      </li>
                      <li>
                        <strong>Install Frontend Dependencies</strong>
                        <pre>cd frontend
npm install</pre>
                      </li>
                      <li>
                        <strong>Start Frontend Development Server</strong>
                        <pre>npm start</pre>
                      </li>
                    </ol>
                  </Tab.Pane>
                </Tab.Content>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Tab.Container>
    </Container>
  );
};

export default DocumentationPage;