import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import NavigationBar from './components/NavigationBar';
import HomePage from './pages/HomePage';
import DocumentationPage from './pages/DocumentationPage';
import NotFoundPage from './pages/NotFoundPage';

function App() {
  return (
    <AppProvider>
      <Router>
        <div className="d-flex flex-column vh-100">
          <NavigationBar />
          <main className="flex-grow-1 bg-body">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/documentation" element={<DocumentationPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </main>
          <footer className="bg-dark text-white text-center py-3">
            <div className="container">
              <span>Staples Brain &copy; {new Date().getFullYear()} | Advanced Multi-Agent AI Orchestration Platform</span>
            </div>
          </footer>
        </div>
      </Router>
    </AppProvider>
  );
}

export default App;