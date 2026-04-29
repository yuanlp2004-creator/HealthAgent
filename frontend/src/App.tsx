import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import MePage from './pages/MePage';
import BpRecordForm from './pages/BpRecordForm';
import BpRecordList from './pages/BpRecordList';
import BpDashboard from './pages/BpDashboard';
import ChatPage from './pages/ChatPage';
import { RequireAuth } from './components/RequireAuth';
import ErrorBoundary from './components/ErrorBoundary';
import { useAuth } from './store/auth';
import { theme, ROUTE_META } from './theme';

function DocumentTitle() {
  const location = useLocation();
  useEffect(() => {
    const match = Object.entries(ROUTE_META).find(([p]) =>
      location.pathname.startsWith(p),
    );
    const title = match?.[1].title;
    document.title = title ? `${title} · HealthAgent` : 'HealthAgent';
  }, [location.pathname]);
  return null;
}

export default function App() {
  const bootstrap = useAuth((s) => s.bootstrap);
  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <ErrorBoundary>
        <BrowserRouter>
          <DocumentTitle />
          <Routes>
            <Route path="/" element={<Navigate to="/bp/dashboard" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/me"
              element={
                <RequireAuth>
                  <MePage />
                </RequireAuth>
              }
            />
            <Route
              path="/bp/new"
              element={
                <RequireAuth>
                  <BpRecordForm />
                </RequireAuth>
              }
            />
            <Route
              path="/bp/list"
              element={
                <RequireAuth>
                  <BpRecordList />
                </RequireAuth>
              }
            />
            <Route
              path="/bp/dashboard"
              element={
                <RequireAuth>
                  <BpDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/chat"
              element={
                <RequireAuth>
                  <ChatPage />
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to="/bp/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </ConfigProvider>
  );
}
