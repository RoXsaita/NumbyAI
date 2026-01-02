/**
 * Main App Component - Simple Automatic Workflow
 * 
 * Just upload a statement and get your dashboard. No chat UI needed!
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SimpleUpload } from './components/SimpleUpload';
import { DashboardWidget } from './widgets/dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';

// Simple dashboard page (for direct access)
const DashboardPage: React.FC = () => {
  return (
    <ErrorBoundary>
      <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
        <h1 style={{ marginBottom: '24px', fontSize: '28px', fontWeight: 700, color: '#1a202c' }}>
          Financial Dashboard
        </h1>
        <DashboardWidget />
      </div>
    </ErrorBoundary>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SimpleUpload />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
