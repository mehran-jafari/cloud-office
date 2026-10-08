import { apiFetch, setAccessToken } from './client';
import type { AuthResponse, User } from '../types/api';
export async function login(username: string, password: string) { const result = await apiFetch<AuthResponse>('/auth/login/', { method: 'POST', body: JSON.stringify({ username, password }) }); setAccessToken(result.access); return result; }
export async function refreshAccessToken() { const result = await apiFetch<AuthResponse>('/auth/refresh/', { method: 'POST' }); setAccessToken(result.access); return result; }
export async function getMe() { return apiFetch<User>('/auth/me/'); }
export async function logout() { await apiFetch<void>('/auth/logout/', { method: 'POST' }); setAccessToken(null); }
