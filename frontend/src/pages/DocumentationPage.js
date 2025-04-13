import React from 'react';
import { Container, Row, Col, Card, Nav, Tab, Badge } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';

const DocumentationPage = () => {
  return (
    <Container fluid className="py-4">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2 className="mb-0">Documentation</h2>
            <Badge bg="primary" className="py-2 px-3">v1.0</Badge>
          </div>
          <p className="text-muted mt-2">
            Complete technical documentation for the Staples Brain platform
          </p>
        </Col>
      </Row>
      
      <Tab.Container defaultActiveKey="overview">
        <Row>
          <Col md={3} className="mb-4">
            <Card className="shadow-sm border-0">
              <Card.Header className="bg-dark text-light">
                <div className="d-flex align-items-center">
                  <FeatherIcon icon="book" size={18} className="me-2" />
                  <span className="fw-bold">Documentation</span>
                </div>
              </Card.Header>
              <Card.Body className="p-0">
                <Nav variant="pills" className="flex-column p-2">
                  <Nav.Item>
                    <Nav.Link eventKey="overview" className="d-flex align-items-center">
                      <FeatherIcon icon="info" size={14} className="me-2" />
                      Overview
                    </Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="architecture" className="d-flex align-items-center">
                      <FeatherIcon icon="layers" size={14} className="me-2" />
                      Architecture
                    </Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="memory" className="d-flex align-items-center">
                      <FeatherIcon icon="database" size={14} className="me-2" />
                      Memory System
                    </Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="agents" className="d-flex align-items-center">
                      <FeatherIcon icon="users" size={14} className="me-2" />
                      Agents
                    </Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="api" className="d-flex align-items-center">
                      <FeatherIcon icon="code" size={14} className="me-2" />
                      API Reference
                    </Nav.Link>
                  </Nav.Item>
                </Nav>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={9}>
            <Card className="shadow-sm border-0">
              <Card.Body className="p-4">
                <Tab.Content>
                  <Tab.Pane eventKey="overview">
                    <div className="mb-4 pb-2 border-bottom">
                      <h3 className="mb-3">Overview</h3>
                      <p className="lead">
                        Staples Brain is an advanced multi-agent AI orchestration platform designed for
                        intelligent, dynamic interactions across complex computational domains.
                      </p>
                    </div>
                    
                    <h4 className="mb-3">Core Components</h4>
                    <Row className="mb-4">
                      <Col md={6} className="mb-3">
                        <div className="d-flex">
                          <div className="me-3">
                            <div className="rounded-circle bg-primary bg-opacity-10 p-2">
                              <FeatherIcon icon="server" size={20} className="text-primary" />
                            </div>
                          </div>
                          <div>
                            <h5>API Gateway</h5>
                            <p className="text-muted">
                              Entry point for all API interactions with standardized request/response format
                            </p>
                          </div>
                        </div>
                      </Col>
                      <Col md={6} className="mb-3">
                        <div className="d-flex">
                          <div className="me-3">
                            <div className="rounded-circle bg-primary bg-opacity-10 p-2">
                              <FeatherIcon icon="cpu" size={20} className="text-primary" />
                            </div>
                          </div>
                          <div>
                            <h5>Staples Brain Core</h5>
                            <p className="text-muted">
                              Central orchestration component that manages agent selection and processing
                            </p>
                          </div>
                        </div>
                      </Col>
                      <Col md={6} className="mb-3">
                        <div className="d-flex">
                          <div className="me-3">
                            <div className="rounded-circle bg-primary bg-opacity-10 p-2">
                              <FeatherIcon icon="users" size={20} className="text-primary" />
                            </div>
                          </div>
                          <div>
                            <h5>Specialized Agents</h5>
                            <p className="text-muted">
                              Individual AI agents focused on specific tasks like package tracking, password reset, etc.
                            </p>
                          </div>
                        </div>
                      </Col>
                      <Col md={6} className="mb-3">
                        <div className="d-flex">
                          <div className="me-3">
                            <div className="rounded-circle bg-primary bg-opacity-10 p-2">
                              <FeatherIcon icon="database" size={20} className="text-primary" />
                            </div>
                          </div>
                          <div>
                            <h5>Database Layer</h5>
                            <p className="text-muted">
                              PostgreSQL with PgVector for efficient vector storage and similarity search
                            </p>
                          </div>
                        </div>
                      </Col>
                    </Row>
                    
                    <h4 className="mb-3">Key Features</h4>
                    <div className="p-3 mb-3 border rounded bg-light">
                      <ul className="mb-0">
                        <li className="mb-2">Intelligent agent selection based on user intent</li>
                        <li className="mb-2">Robust error handling and fallback mechanisms</li>
                        <li className="mb-2">Comprehensive telemetry and monitoring</li>
                        <li className="mb-2">Vector-based similarity search for context retrieval</li>
                        <li className="mb-0">Scalable and extensible architecture</li>
                      </ul>
                    </div>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="architecture">
                    <div className="mb-4 pb-2 border-bottom">
                      <h3 className="mb-3">Architecture</h3>
                      <p className="lead">
                        Staples Brain follows a modern, modular architecture with clear separation of concerns
                        and highly decoupled components.
                      </p>
                    </div>
                    
                    <h4 className="mb-3">Architecture Layers</h4>
                    <div className="p-4 mb-4 border rounded bg-light text-center">
                      <div className="d-flex justify-content-between align-items-center flex-wrap">
                        <div className="p-2 bg-primary text-white rounded mb-2">UI Layer</div>
                        <FeatherIcon icon="arrow-right" size={20} className="mx-2 mb-2" />
                        <div className="p-2 bg-primary text-white rounded mb-2">API Gateway</div>
                        <FeatherIcon icon="arrow-right" size={20} className="mx-2 mb-2" />
                        <div className="p-2 bg-primary text-white rounded mb-2">Service Layer</div>
                        <FeatherIcon icon="arrow-right" size={20} className="mx-2 mb-2" />
                        <div className="p-2 bg-primary text-white rounded mb-2">Staples Brain</div>
                        <FeatherIcon icon="arrow-right" size={20} className="mx-2 mb-2" />
                        <div className="p-2 bg-primary text-white rounded mb-2">Orchestrator</div>
                        <FeatherIcon icon="arrow-right" size={20} className="mx-2 mb-2" />
                        <div className="p-2 bg-primary text-white rounded mb-2">Agents</div>
                      </div>
                    </div>
                    
                    <h4 className="mb-3">Technology Stack</h4>
                    <Row>
                      <Col md={6} className="mb-4">
                        <Card className="h-100 border-0 shadow-sm">
                          <Card.Header className="bg-dark text-light">
                            <div className="d-flex align-items-center">
                              <FeatherIcon icon="server" size={16} className="me-2" />
                              <span className="fw-bold">Backend</span>
                            </div>
                          </Card.Header>
                          <Card.Body>
                            <ul className="list-unstyled">
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">Python 3.12+</Badge>
                                <span className="text-muted small">Core programming language</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">FastAPI</Badge>
                                <span className="text-muted small">Web framework</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">PostgreSQL</Badge>
                                <span className="text-muted small">Database with PgVector</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">LangChain</Badge>
                                <span className="text-muted small">LLM framework</span>
                              </li>
                              <li className="d-flex align-items-center">
                                <Badge bg="secondary" className="me-2">OpenAI</Badge>
                                <span className="text-muted small">LLM provider (GPT-4o)</span>
                              </li>
                            </ul>
                          </Card.Body>
                        </Card>
                      </Col>
                      <Col md={6} className="mb-4">
                        <Card className="h-100 border-0 shadow-sm">
                          <Card.Header className="bg-dark text-light">
                            <div className="d-flex align-items-center">
                              <FeatherIcon icon="monitor" size={16} className="me-2" />
                              <span className="fw-bold">Frontend</span>
                            </div>
                          </Card.Header>
                          <Card.Body>
                            <ul className="list-unstyled">
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">React</Badge>
                                <span className="text-muted small">UI framework</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">React Router</Badge>
                                <span className="text-muted small">Client-side routing</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">Bootstrap</Badge>
                                <span className="text-muted small">UI components</span>
                              </li>
                              <li className="d-flex align-items-center mb-2">
                                <Badge bg="secondary" className="me-2">Axios</Badge>
                                <span className="text-muted small">HTTP client</span>
                              </li>
                              <li className="d-flex align-items-center">
                                <Badge bg="secondary" className="me-2">Chart.js</Badge>
                                <span className="text-muted small">Data visualization</span>
                              </li>
                            </ul>
                          </Card.Body>
                        </Card>
                      </Col>
                    </Row>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="memory">
                    <div className="mb-4 pb-2 border-bottom">
                      <h3 className="mb-3">Memory System</h3>
                      <p className="lead">
                        Staples Brain features an advanced memory management system (mem0) that provides both 
                        short-term and long-term storage capabilities.
                      </p>
                    </div>
                    
                    <h4 className="mb-3">Memory Architecture</h4>
                    <Row className="mb-4">
                      <Col lg={6} className="mb-3">
                        <Card className="h-100 shadow-sm border-0">
                          <Card.Header className="bg-success bg-opacity-10 text-success">
                            <div className="d-flex align-items-center">
                              <FeatherIcon icon="zap" size={18} className="me-2" />
                              <span className="fw-bold">Redis Memory</span>
                            </div>
                          </Card.Header>
                          <Card.Body>
                            <p className="card-text">
                              Primary, high-speed storage for working memory and short-term recall.
                            </p>
                            <ul>
                              <li>Working memory (5-minute TTL)</li>
                              <li>Short-term memory (1-hour TTL)</li>
                              <li>Message history</li>
                              <li>Entity tracking</li>
                            </ul>
                          </Card.Body>
                        </Card>
                      </Col>
                      <Col lg={6} className="mb-3">
                        <Card className="h-100 shadow-sm border-0">
                          <Card.Header className="bg-info bg-opacity-10 text-info">
                            <div className="d-flex align-items-center">
                              <FeatherIcon icon="hard-drive" size={18} className="me-2" />
                              <span className="fw-bold">PostgreSQL Memory</span>
                            </div>
                          </Card.Header>
                          <Card.Body>
                            <p className="card-text">
                              Long-term, persistent storage for archival and analytical purposes.
                            </p>
                            <ul>
                              <li>Archival storage</li>
                              <li>Persistent entities</li>
                              <li>Analytics data</li>
                              <li>Searchable history</li>
                            </ul>
                          </Card.Body>
                        </Card>
                      </Col>
                    </Row>
                    
                    <h4 className="mb-3">Memory Operations</h4>
                    <div className="p-3 mb-3 bg-light rounded border">
                      <pre className="mb-0 p-3">
{`# Memory Entry Structure
MemoryEntry(
    namespace: str,        # Categorization context
    key: str,              # Identifier within namespace
    value: Any,            # Stored data
    memory_type: str,      # "working", "short_term", "long_term" 
    ttl: int,              # Time-to-live in seconds
    expires_at: datetime   # Expiration timestamp
)

# Typical Memory Operations
await memory_service.store(namespace, key, value, memory_type)
await memory_service.retrieve(namespace, key, memory_type)
await memory_service.add_message(session_id, message, role)`}
                      </pre>
                    </div>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="agents">
                    <div className="mb-4 pb-2 border-bottom">
                      <h3 className="mb-3">Agent System</h3>
                      <p className="lead">
                        Staples Brain uses a multi-agent architecture where specialized agents
                        handle different types of user requests.
                      </p>
                    </div>
                    
                    <h4 className="mb-3">Built-in Agents</h4>
                    <div className="mb-4">
                      <Row>
                        <Col md={6} className="mb-3">
                          <Card className="h-100 shadow-sm border-0">
                            <Card.Header className="bg-primary bg-opacity-10 text-primary">
                              <div className="d-flex align-items-center">
                                <FeatherIcon icon="package" size={18} className="me-2" />
                                <span className="fw-bold">Package Tracking Agent</span>
                              </div>
                            </Card.Header>
                            <Card.Body>
                              <p>
                                Handles order and package tracking requests, extracts tracking numbers,
                                and provides shipping status updates.
                              </p>
                              <div className="d-flex mt-3">
                                <Badge bg="info" className="me-2">Order Lookup</Badge>
                                <Badge bg="info" className="me-2">Tracking Number</Badge>
                                <Badge bg="info">Status Updates</Badge>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                        <Col md={6} className="mb-3">
                          <Card className="h-100 shadow-sm border-0">
                            <Card.Header className="bg-primary bg-opacity-10 text-primary">
                              <div className="d-flex align-items-center">
                                <FeatherIcon icon="key" size={18} className="me-2" />
                                <span className="fw-bold">Password Reset Agent</span>
                              </div>
                            </Card.Header>
                            <Card.Body>
                              <p>
                                Assists users with password reset procedures for various
                                Staples systems and accounts.
                              </p>
                              <div className="d-flex mt-3">
                                <Badge bg="info" className="me-2">Account Verification</Badge>
                                <Badge bg="info" className="me-2">Reset Link</Badge>
                                <Badge bg="info">Security</Badge>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                        <Col md={6} className="mb-3">
                          <Card className="h-100 shadow-sm border-0">
                            <Card.Header className="bg-primary bg-opacity-10 text-primary">
                              <div className="d-flex align-items-center">
                                <FeatherIcon icon="map-pin" size={18} className="me-2" />
                                <span className="fw-bold">Store Locator Agent</span>
                              </div>
                            </Card.Header>
                            <Card.Body>
                              <p>
                                Helps users find nearby Staples stores, providing location details,
                                hours, and available services.
                              </p>
                              <div className="d-flex mt-3">
                                <Badge bg="info" className="me-2">Location Search</Badge>
                                <Badge bg="info" className="me-2">Store Hours</Badge>
                                <Badge bg="info">Services</Badge>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                        <Col md={6} className="mb-3">
                          <Card className="h-100 shadow-sm border-0">
                            <Card.Header className="bg-primary bg-opacity-10 text-primary">
                              <div className="d-flex align-items-center">
                                <FeatherIcon icon="shopping-bag" size={18} className="me-2" />
                                <span className="fw-bold">Product Information Agent</span>
                              </div>
                            </Card.Header>
                            <Card.Body>
                              <p>
                                Provides detailed information about Staples products,
                                specifications, and availability.
                              </p>
                              <div className="d-flex mt-3">
                                <Badge bg="info" className="me-2">Product Search</Badge>
                                <Badge bg="info" className="me-2">Specifications</Badge>
                                <Badge bg="info">Inventory</Badge>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                      </Row>
                    </div>
                    
                    <h4 className="mb-3">Agent Selection</h4>
                    <p>
                      The Orchestrator component analyzes user input to determine the most appropriate agent using:
                    </p>
                    <div className="d-flex flex-wrap mt-3">
                      <div className="bg-light rounded p-3 me-3 mb-3">
                        <div className="d-flex align-items-center">
                          <FeatherIcon icon="percent" size={16} className="me-2 text-primary" />
                          <strong>Confidence Scoring</strong>
                        </div>
                      </div>
                      <div className="bg-light rounded p-3 me-3 mb-3">
                        <div className="d-flex align-items-center">
                          <FeatherIcon icon="target" size={16} className="me-2 text-primary" />
                          <strong>Intent Classification</strong>
                        </div>
                      </div>
                      <div className="bg-light rounded p-3 me-3 mb-3">
                        <div className="d-flex align-items-center">
                          <FeatherIcon icon="tag" size={16} className="me-2 text-primary" />
                          <strong>Keyword Matching</strong>
                        </div>
                      </div>
                      <div className="bg-light rounded p-3 mb-3">
                        <div className="d-flex align-items-center">
                          <FeatherIcon icon="link-2" size={16} className="me-2 text-primary" />
                          <strong>Context Analysis</strong>
                        </div>
                      </div>
                    </div>
                  </Tab.Pane>
                  
                  <Tab.Pane eventKey="api">
                    <div className="mb-4 pb-2 border-bottom">
                      <h3 className="mb-3">API Reference</h3>
                      <p className="lead">
                        Staples Brain exposes a standardized API for interacting with the system.
                      </p>
                    </div>
                    
                    <div className="mb-4">
                      <h4 className="mb-3">Base URL</h4>
                      <div className="bg-dark text-light p-3 rounded">
                        <code className="user-select-all">/api/v1</code>
                      </div>
                    </div>
                    
                    <div className="mb-4">
                      <h4 className="mb-3">Authentication</h4>
                      <div className="alert alert-warning">
                        <div className="d-flex align-items-center">
                          <FeatherIcon icon="alert-triangle" size={18} className="me-2" />
                          <div>
                            <p className="mb-0">
                              <strong>Note:</strong> Currently, API endpoints do not require authentication.
                              This will be added in a future update.
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <h4 className="mb-3">Core Endpoints</h4>
                    <table className="table table-striped border">
                      <thead className="table-dark">
                        <tr>
                          <th style={{ width: "30%" }}>Endpoint</th>
                          <th style={{ width: "15%" }}>Method</th>
                          <th>Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>
                            <code className="user-select-all">/health</code>
                          </td>
                          <td>
                            <Badge bg="success">GET</Badge>
                          </td>
                          <td>Check system health status</td>
                        </tr>
                        <tr>
                          <td>
                            <code className="user-select-all">/chat/messages</code>
                          </td>
                          <td>
                            <Badge bg="primary">POST</Badge>
                          </td>
                          <td>Send a message to Staples Brain</td>
                        </tr>
                        <tr>
                          <td>
                            <code className="user-select-all">/chat/history/{'{session_id}'}</code>
                          </td>
                          <td>
                            <Badge bg="success">GET</Badge>
                          </td>
                          <td>Retrieve conversation history</td>
                        </tr>
                        <tr>
                          <td>
                            <code className="user-select-all">/agents</code>
                          </td>
                          <td>
                            <Badge bg="success">GET</Badge>
                          </td>
                          <td>List all available agents</td>
                        </tr>
                        <tr>
                          <td>
                            <code className="user-select-all">/agents/{'{agent_id}'}</code>
                          </td>
                          <td>
                            <Badge bg="success">GET</Badge>
                          </td>
                          <td>Get details for a specific agent</td>
                        </tr>
                        <tr>
                          <td>
                            <code className="user-select-all">/stats</code>
                          </td>
                          <td>
                            <Badge bg="success">GET</Badge>
                          </td>
                          <td>Get system statistics and metrics</td>
                        </tr>
                      </tbody>
                    </table>
                    
                    <div className="mt-4 text-center">
                      <p className="text-muted">
                        Complete API documentation is available through the Swagger UI at <code>/docs</code>
                      </p>
                    </div>
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