import { apiFetch } from './client';
import type { RemoteSession } from '../types/api';
export function createRemoteSession(conversationId?: number) { return apiFetch<RemoteSession>('/support/remote-sessions/', { method: 'POST', body: JSON.stringify({ conversation_id: conversationId ?? null, mode: 'screen_share' }) }); }
export function joinRemoteSession(code: string) { return apiFetch<RemoteSession>('/support/remote-sessions/join/', { method: 'POST', body: JSON.stringify({ code }) }); }
export function getRemoteSession(id: number) { return apiFetch<RemoteSession>(`/support/remote-sessions/${id}/`); }
export function consentRemoteSession(id: number) { return apiFetch<RemoteSession>(`/support/remote-sessions/${id}/consent/`, { method: 'POST' }); }
export function endRemoteSession(id: number) { return apiFetch<RemoteSession>(`/support/remote-sessions/${id}/end/`, { method: 'POST' }); }
