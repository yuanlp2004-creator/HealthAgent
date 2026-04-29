import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { Spin } from 'antd';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, initialized } = useAuth();
  const location = useLocation();

  if (!initialized) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
        <Spin />
      </div>
    );
  }
  if (!user) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }
  return <>{children}</>;
}
