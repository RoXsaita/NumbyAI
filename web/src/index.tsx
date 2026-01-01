// Entry point for widget components
import React from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from './components/Dashboard';

// Mount dashboard component
const dashboardRoot = document.getElementById('dashboard-root');
if (dashboardRoot) {
  createRoot(dashboardRoot).render(<Dashboard />);
}
