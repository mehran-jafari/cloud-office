import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
export function ProtectedRoute() { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <div className="loading-screen">در حال بررسی نشست...</div>; if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />; return <Outlet />; }
