/**
 * Main App Component with Routing
 * 
 * Provides routing for chat interface (home), dashboard, and transactions pages
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ChatInterface } from './components/ChatInterface';
import { DashboardWidget } from './widgets/dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';

// Simple wrapper to mount dashboard
const DashboardPage: React.FC = () => {
  return (
    <ErrorBoundary>
      <DashboardWidget />
    </ErrorBoundary>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatInterface />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
