import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

/** گزارش Audit فقط برای owner / admin / auditor / superuser (بک‌اند هم همین را اعمال می‌کند). */
const AUDIT_ROLES = ['owner', 'admin', 'auditor'];

export function canViewAudit(user: { role?: string; roles?: string[]; is_superuser?: boolean } | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const codes = user.roles?.length ? user.roles : user.role ? [user.role] : [];
  return codes.some(code => AUDIT_ROLES.includes(code));
}

export function AuditRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">در حال بررسی دسترسی...</div>;
  if (!canViewAudit(user)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
