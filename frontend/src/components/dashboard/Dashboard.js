import React, { useEffect, useState } from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import FeatherIcon from 'feather-icons-react';
import { useAppContext } from '../../context/AppContext';
import apiService from '../../api/apiService';

const Dashboard = () => {
  const { setAgents, setLoading, addNotification } = useAppContext();
  const [stats, setStats] = useState({
    agents: 0,
    conversations: 0,
    successRate: 0,
    activeUsers: 0
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch agents
        const agentsResponse = await apiService.apiCall(apiService.getAgents);
        if (agentsResponse.success && agentsResponse.agents) {
          setAgents(agentsResponse.agents);
          setStats(prev => ({ ...prev, agents: agentsResponse.agents.length }));
        }

        // For now we'll use dummy stats until we implement those APIs
        setStats(prev => ({
          ...prev,
          conversations: 28,
          successRate: 94,
          activeUsers: 124
        }));

      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        addNotification({
          title: 'Error',
          message: 'Failed to load dashboard data. Please try again later.',
          type: 'error'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [setAgents, setLoading, addNotification]);

  const statCards = [
    {
      title: 'Total Agents',
      value: stats.agents,
      icon: 'cpu',
      color: 'primary',
      link: '/agents'
    },
    {
      title: 'Conversations',
      value: stats.conversations,
      icon: 'message-square',
      color: 'success',
      link: '/conversations'
    },
    {
      title: 'Success Rate',
      value: `${stats.successRate}%`,
      icon: 'bar-chart-2',
      color: 'info',
      link: '/analytics'
    },
    {
      title: 'Active Users',
      value: stats.activeUsers,
      icon: 'users',
      color: 'warning',
      link: '/users'
    }
  ];

  return (
    <Container fluid className="p-4">
      <h1 className="h3 mb-4">Dashboard</h1>
      
      <Row>
        {statCards.map((card, index) => (
          <Col key={index} xs={12} md={6} lg={3} className="mb-4">
            <Card className="h-100 shadow-sm">
              <Card.Body className="d-flex flex-column">
                <div className="d-flex align-items-center mb-3">
                  <div className={`p-3 rounded-circle bg-${card.color} bg-opacity-10 me-3`}>
                    <FeatherIcon icon={card.icon} className={`text-${card.color}`} />
                  </div>
                  <div>
                    <h6 className="mb-0">{card.title}</h6>
                    <h3 className="mb-0">{card.value}</h3>
                  </div>
                </div>
                <p className="text-muted small mb-0 mt-auto">
                  Updated just now
                </p>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Row className="mb-4">
        <Col xs={12} lg={8} className="mb-4 mb-lg-0">
          <Card className="h-100">
            <Card.Header className="bg-transparent">
              <h5 className="mb-0">Recent Activity</h5>
            </Card.Header>
            <Card.Body>
              <div className="text-center py-5">
                <FeatherIcon icon="activity" size={48} className="text-muted mb-3" />
                <h5>Activity data will appear here</h5>
                <p className="text-muted">
                  When users interact with agents, their activity will be displayed here.
                </p>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col xs={12} lg={4}>
          <Card className="h-100">
            <Card.Header className="bg-transparent">
              <h5 className="mb-0">Quick Actions</h5>
            </Card.Header>
            <Card.Body>
              <div className="d-grid gap-2">
                <Button as={Link} to="/chat" variant="primary" className="d-flex align-items-center justify-content-center">
                  <FeatherIcon icon="message-square" size={18} className="me-2" />
                  Start New Chat
                </Button>
                <Button as={Link} to="/agents" variant="outline-secondary" className="d-flex align-items-center justify-content-center">
                  <FeatherIcon icon="cpu" size={18} className="me-2" />
                  View Agents
                </Button>
                <Button as={Link} to="/analytics" variant="outline-secondary" className="d-flex align-items-center justify-content-center">
                  <FeatherIcon icon="bar-chart-2" size={18} className="me-2" />
                  View Analytics
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Dashboard;