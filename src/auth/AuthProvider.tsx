import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getMe, login as loginRequest, logout as logoutRequest, refreshAccessToken } from '../api/auth';
import { getAccessToken } from '../api/client';
import type { User } from '../types/api';
type AuthContextValue = { user: User | null; loading: boolean; accessToken: string | null; login: (u: string, p: string) => Promise<void>; logout: () => Promise<void> };
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) { const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true); useEffect(() => { refreshAccessToken().then(getMe).then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []); async function login(u: string, p: string) { await loginRequest(u, p); setUser(await getMe()); } async function logout() { await logoutRequest(); setUser(null); } const value = useMemo(() => ({ user, loading, accessToken: getAccessToken(), login, logout }), [user, loading]); return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>; }
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('useAuth باید داخل AuthProvider استفاده شود'); return value; }
