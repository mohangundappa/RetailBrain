import React from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import ChatInterface from '../components/ChatInterface';
import SystemStatus from '../components/SystemStatus';

const HomePage = () => {
  return (
    <Container fluid className="mt-3">
      <Row>
        <Col lg={8}>
          <ChatInterface />
        </Col>
        <Col lg={4}>
          <SystemStatus />
          
          <div className="card shadow-sm mb-4">
            <div className="card-header bg-dark text-light">
              <i className="feather-info me-2"></i>
              About Staples Brain
            </div>
            <div className="card-body">
              <h5 className="card-title">Advanced Multi-Agent AI Orchestration Platform</h5>
              <p className="card-text">
                Staples Brain is a sophisticated AI orchestration system that routes user requests to specialized agents.
                The platform handles package tracking, password resets, store location queries, product information, and more.
              </p>
              <p className="card-text">
                <small className="text-muted">
                  Powered by OpenAI GPT-4o, LangChain, and advanced agent-based architecture.
                </small>
              </p>
            </div>
          </div>
        </Col>
      </Row>
    </Container>
  );
};

export default HomePage;