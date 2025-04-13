import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import AppLayout from './components/layout/AppLayout';
import HomePage from './pages/HomePage';
import DocumentationPage from './pages/DocumentationPage';
import NotFoundPage from './pages/NotFoundPage';
import './styles/App.css';

// Import future pages (to be implemented)
// import ChatPage from './pages/ChatPage';
// import ObservabilityPage from './pages/ObservabilityPage';
// import AgentBuilderPage from './pages/AgentBuilderPage';
// import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <AppProvider>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/documentation" element={<DocumentationPage />} />
            {/* Future routes */}
            <Route path="/chat" element={<div className="p-5 text-center">Chat Interface (Coming Soon)</div>} />
            <Route path="/observability" element={<div className="p-5 text-center">Observability Dashboard (Coming Soon)</div>} />
            <Route path="/agent-builder" element={<div className="p-5 text-center">Agent Builder Interface (Coming Soon)</div>} />
            <Route path="/settings" element={<div className="p-5 text-center">Settings Page (Coming Soon)</div>} />
            <Route path="/admin/users" element={<div className="p-5 text-center">User Management (Coming Soon)</div>} />
            <Route path="/admin/system" element={<div className="p-5 text-center">System Settings (Coming Soon)</div>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AppLayout>
      </Router>
    </AppProvider>
  );
}

export default App;