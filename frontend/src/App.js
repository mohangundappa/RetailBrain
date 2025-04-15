import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './components/dashboard/Dashboard';
import ChatInterface from './components/chat/ChatInterface';
import AgentOverview from './components/dashboard/AgentOverview';
import AgentsPage from './pages/AgentsPage';
import NotFound from './components/common/NotFound';

function App() {
  return (
    <AppProvider>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<ChatInterface />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="agent-overview" element={<AgentOverview />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </AppProvider>
  );
}

export default App;