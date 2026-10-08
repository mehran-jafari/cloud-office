import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">در حال بررسی دسترسی...</div>;
  const allowed = Boolean(
    user?.permissions?.view_admin ||
      user?.permissions?.manage_users ||
      user?.is_superuser ||
      user?.role === 'owner' ||
      user?.role === 'admin'
  );
  if (!allowed) return <Navigate to="/" replace />;
  return <>{children}</>;
}
