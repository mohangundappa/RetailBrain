import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Badge, Button, Form, Spinner, Tabs, Tab } from 'react-bootstrap';
import FeatherIcon from 'feather-icons-react';
import { Bar } from 'react-chartjs-2';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend 
} from 'chart.js';
import { telemetryService, statsService } from '../api/apiService';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const TelemetryPage = () => {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState({
    sessions: true,
    events: false,
    stats: true
  });
  const [error, setError] = useState({
    sessions: null,
    events: null,
    stats: null
  });
  const [filterDays, setFilterDays] = useState(7);
  
  // Fetch sessions on component mount and when filter changes
  useEffect(() => {
    const fetchSessions = async () => {
      setLoading(prev => ({ ...prev, sessions: true }));
      try {
        const response = await telemetryService.getSessions(20, 0, filterDays);
        if (response.success && response.data.sessions) {
          setSessions(response.data.sessions);
        } else {
          throw new Error(response.error || 'Failed to load sessions');
        }
      } catch (err) {
        setError(prev => ({ ...prev, sessions: err.message }));
        console.error('Error fetching sessions:', err);
      } finally {
        setLoading(prev => ({ ...prev, sessions: false }));
      }
    };
    
    fetchSessions();
  }, [filterDays]);
  
  // Fetch system stats
  useEffect(() => {
    const fetchStats = async () => {
      setLoading(prev => ({ ...prev, stats: true }));
      try {
        const response = await statsService.getStats(filterDays);
        if (response.success) {
          setStats(response.data);
        } else {
          throw new Error(response.error || 'Failed to load stats');
        }
      } catch (err) {
        setError(prev => ({ ...prev, stats: err.message }));
        console.error('Error fetching stats:', err);
      } finally {
        setLoading(prev => ({ ...prev, stats: false }));
      }
    };
    
    fetchStats();
  }, [filterDays]);
  
  // Fetch events for selected session
  const fetchEvents = async (sessionId) => {
    setLoading(prev => ({ ...prev, events: true }));
    try {
      const response = await telemetryService.getSessionEvents(sessionId);
      if (response.success && response.data.events) {
        setEvents(response.data.events);
      } else {
        throw new Error(response.error || 'Failed to load events');
      }
    } catch (err) {
      setError(prev => ({ ...prev, events: err.message }));
      console.error('Error fetching events:', err);
    } finally {
      setLoading(prev => ({ ...prev, events: false }));
    }
  };
  
  // Handle session selection
  const handleSelectSession = (sessionId) => {
    setSelectedSession(sessionId);
    fetchEvents(sessionId);
  };
  
  // Format duration from seconds
  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    
    if (mins === 0) {
      return `${secs} seconds`;
    } else {
      return `${mins} min ${secs} sec`;
    }
  };
  
  // Generate chart data from stats
  const generateChartData = () => {
    if (!stats || !stats.agent_distribution) {
      return {
        labels: [],
        datasets: [{
          label: 'Agent Usage',
          data: [],
          backgroundColor: 'rgba(54, 162, 235, 0.5)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }]
      };
    }
    
    const labels = Object.keys(stats.agent_distribution);
    const data = labels.map(key => stats.agent_distribution[key]);
    
    return {
      labels,
      datasets: [{
        label: 'Agent Usage',
        data,
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    };
  };
  
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Agent Usage Distribution'
      }
    }
  };
  
  // Render sessions table
  const renderSessionsTable = () => {
    if (loading.sessions) {
      return (
        <div className="text-center py-5">
          <Spinner animation="border" role="status" className="mb-3" />
          <p>Loading sessions...</p>
        </div>
      );
    }
    
    if (error.sessions) {
      return (
        <div className="alert alert-danger">
          <FeatherIcon icon="alert-triangle" className="me-2" />
          {error.sessions}
        </div>
      );
    }
    
    if (sessions.length === 0) {
      return (
        <div className="alert alert-info">
          <FeatherIcon icon="info" className="me-2" />
          No telemetry sessions found for the selected time period.
        </div>
      );
    }
    
    return (
      <div className="table-responsive">
        <Table striped hover className="sessions-table">
          <thead className="table-dark">
            <tr>
              <th>Session ID</th>
              <th>Conversations</th>
              <th>Duration</th>
              <th>Agents Used</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.session_id} className={selectedSession === session.session_id ? 'table-active' : ''}>
                <td>{session.session_id.substring(0, 8)}...</td>
                <td>{session.conversation_count}</td>
                <td>{formatDuration(session.duration)}</td>
                <td>
                  {Object.keys(session.agents || {}).map(agent => (
                    <Badge key={agent} bg="info" className="me-1">
                      {agent.split(' ')[0]} ({session.agents[agent]})
                    </Badge>
                  ))}
                </td>
                <td>
                  <Button 
                    variant="outline-primary" 
                    size="sm"
                    onClick={() => handleSelectSession(session.session_id)}
                  >
                    View Details
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    );
  };
  
  // Render events for selected session
  const renderSessionEvents = () => {
    if (!selectedSession) {
      return (
        <div className="alert alert-info">
          <FeatherIcon icon="info" className="me-2" />
          Select a session to view events.
        </div>
      );
    }
    
    if (loading.events) {
      return (
        <div className="text-center py-5">
          <Spinner animation="border" role="status" className="mb-3" />
          <p>Loading events...</p>
        </div>
      );
    }
    
    if (error.events) {
      return (
        <div className="alert alert-danger">
          <FeatherIcon icon="alert-triangle" className="me-2" />
          {error.events}
        </div>
      );
    }
    
    if (events.length === 0) {
      return (
        <div className="alert alert-info">
          <FeatherIcon icon="info" className="me-2" />
          No events found for this session.
        </div>
      );
    }
    
    return (
      <div className="table-responsive">
        <Table striped hover>
          <thead className="table-dark">
            <tr>
              <th>Event Type</th>
              <th>Timestamp</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, index) => (
              <tr key={index}>
                <td>
                  <Badge bg={event.event_type === 'conversation' ? 'success' : 'info'}>
                    {event.event_type}
                  </Badge>
                </td>
                <td>{new Date(event.timestamp).toLocaleString()}</td>
                <td>
                  {event.event_type === 'conversation' ? (
                    <div>
                      <div><strong>User:</strong> {event.data.user_input}</div>
                      <div><strong>Agent:</strong> {event.data.selected_agent}</div>
                      <div><strong>Confidence:</strong> {(event.data.confidence * 100).toFixed(1)}%</div>
                    </div>
                  ) : (
                    <pre className="p-2 bg-light rounded" style={{ maxHeight: '200px', overflow: 'auto' }}>
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    );
  };
  
  // Render stats section
  const renderStats = () => {
    if (loading.stats) {
      return (
        <div className="text-center py-5">
          <Spinner animation="border" role="status" className="mb-3" />
          <p>Loading statistics...</p>
        </div>
      );
    }
    
    if (error.stats) {
      return (
        <div className="alert alert-danger">
          <FeatherIcon icon="alert-triangle" className="me-2" />
          {error.stats}
        </div>
      );
    }
    
    if (!stats) {
      return (
        <div className="alert alert-info">
          <FeatherIcon icon="info" className="me-2" />
          No statistics available.
        </div>
      );
    }
    
    return (
      <div>
        <Row className="mb-4">
          <Col md={6}>
            <Card className="shadow-sm h-100">
              <Card.Header className="bg-dark text-light">
                <FeatherIcon icon="bar-chart-2" className="me-2" />
                Conversation Metrics
              </Card.Header>
              <Card.Body>
                <div className="d-flex flex-column h-100 justify-content-center">
                  <div className="text-center mb-3">
                    <h2 className="display-4">{stats.total_conversations || 0}</h2>
                    <p className="lead">Total Conversations</p>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6}>
            <Card className="shadow-sm h-100">
              <Card.Header className="bg-dark text-light">
                <FeatherIcon icon="pie-chart" className="me-2" />
                Agent Distribution
              </Card.Header>
              <Card.Body>
                <Bar options={chartOptions} data={generateChartData()} />
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };
  
  return (
    <Container className="py-4">
      <h2 className="mb-4">Telemetry Dashboard</h2>
      
      <Row className="mb-4">
        <Col md={6}>
          <Form.Group controlId="filterDays">
            <Form.Label>Time Period</Form.Label>
            <Form.Select
              value={filterDays}
              onChange={(e) => setFilterDays(parseInt(e.target.value))}
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </Form.Select>
          </Form.Group>
        </Col>
      </Row>
      
      <Tabs defaultActiveKey="sessions" className="mb-4">
        <Tab eventKey="sessions" title="Sessions">
          <Card className="shadow-sm mb-4">
            <Card.Header className="bg-dark text-light">
              <FeatherIcon icon="list" className="me-2" />
              Telemetry Sessions
            </Card.Header>
            <Card.Body>
              {renderSessionsTable()}
            </Card.Body>
          </Card>
          
          {selectedSession && (
            <Card className="shadow-sm">
              <Card.Header className="bg-dark text-light">
                <FeatherIcon icon="activity" className="me-2" />
                Session Events: {selectedSession.substring(0, 8)}...
              </Card.Header>
              <Card.Body>
                {renderSessionEvents()}
              </Card.Body>
            </Card>
          )}
        </Tab>
        <Tab eventKey="stats" title="Statistics">
          {renderStats()}
        </Tab>
      </Tabs>
    </Container>
  );
};

export default TelemetryPage;