import React from 'react';
import { Outlet } from 'react-router-dom';
import { Container, Row, Col } from 'react-bootstrap';
import Sidebar from './Sidebar';
import TopNavbar from './TopNavbar';
import Notifications from './Notifications';
import { useAppContext } from '../../context/AppContext';

const AppLayout = () => {
  const { loading } = useAppContext();

  return (
    <div className="app-container d-flex flex-column vh-100">
      <TopNavbar />
      <Container fluid className="flex-grow-1 d-flex p-0">
        <Sidebar />
        <main className="main-content flex-grow-1 p-3">
          {loading ? (
            <div className="d-flex justify-content-center align-items-center h-100">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : (
            <Row className="h-100">
              <Col>
                <Outlet />
              </Col>
            </Row>
          )}
        </main>
      </Container>
      <Notifications />
    </div>
  );
};

export default AppLayout;