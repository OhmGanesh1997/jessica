import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { motion } from 'framer-motion';

// Layout Components
import DashboardLayout from './components/Layout/DashboardLayout';
import AuthLayout from './components/Layout/AuthLayout';

// Authentication Pages
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/RegisterPage';
import OAuthCallback from './pages/Auth/OAuthCallback';

// Main Application Pages
import DashboardPage from './pages/Dashboard/DashboardPage';
import EmailsPage from './pages/Emails/EmailsPage';
import CalendarPage from './pages/Calendar/CalendarPage';
import AnalyticsPage from './pages/Analytics/AnalyticsPage';
import SettingsPage from './pages/Settings/SettingsPage';
import IntegrationsPage from './pages/Integrations/IntegrationsPage';
import CreditsPage from './pages/Credits/CreditsPage';

// Loading Component
const LoadingScreen = () => (
  <div className="min-h-screen bg-gradient-primary flex items-center justify-center">
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center"
    >
      <div className="animate-spin w-12 h-12 border-4 border-white/30 border-t-white rounded-full mx-auto mb-4"></div>
      <h3 className="text-white text-lg font-semibold">Jessica AI Agent</h3>
      <p className="text-white/70 mt-2">Loading your intelligent workspace...</p>
    </motion.div>
  </div>
);

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!user) {
    return <Navigate to="/auth/login" replace />;
  }

  return children;
};

// Public Route Component (redirects if already authenticated)
const PublicRoute = ({ children }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <div className="App">
      <Routes>
        {/* Authentication Routes */}
        <Route path="/auth/*" element={
          <PublicRoute>
            <AuthLayout>
              <Routes>
                <Route path="login" element={<LoginPage />} />
                <Route path="register" element={<RegisterPage />} />
                <Route path="callback" element={<OAuthCallback />} />
                <Route path="*" element={<Navigate to="/auth/login" replace />} />
              </Routes>
            </AuthLayout>
          </PublicRoute>
        } />

        {/* Protected Application Routes */}
        <Route path="/*" element={
          <ProtectedRoute>
            <DashboardLayout>
              <Routes>
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="emails" element={<EmailsPage />} />
                <Route path="calendar" element={<CalendarPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="integrations" element={<IntegrationsPage />} />
                <Route path="credits" element={<CreditsPage />} />
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </DashboardLayout>
          </ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}

export default App;