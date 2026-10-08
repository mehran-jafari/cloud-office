import { apiFetch } from './client';
import type { SupportAgentPerformance, SupportConversation, SupportMessage } from '../types/api';

export type OnlineAgent = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  avatar_color: string;
  gender?: 'male' | 'female' | 'other';
  avatar_url?: string | null;
};

export function listConversations() {
  return apiFetch<SupportConversation[]>('/support/conversations/');
}
export function createConversation(subject: string, body: string) {
  return apiFetch<SupportConversation>('/support/conversations/', {
    method: 'POST',
    body: JSON.stringify({ subject, body }),
  });
}
export function sendSupportMessage(id: number, body: string) {
  return apiFetch<SupportMessage>(`/support/conversations/${id}/messages/`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
}
export function getConversation(id: number) {
  return apiFetch<SupportConversation>(`/support/conversations/${id}/`);
}
export function listOnlineAgents() {
  return apiFetch<OnlineAgent[]>('/support/online-agents/');
}
export function setSupportOnline(online: boolean) {
  return apiFetch<{ is_support_online: boolean; support_last_seen?: string }>(
    '/support/online-toggle/',
    {
      method: 'POST',
      body: JSON.stringify({ online }),
    },
  );
}
export function sendSupportPresence(online?: boolean) {
  return apiFetch<{ ok: boolean }>('/support/presence/', {
    method: 'POST',
    body: JSON.stringify(online === undefined ? {} : { online }),
  });
}
export function fetchSupportPerformance(days = 30) {
  return apiFetch<{ days: number; agents: SupportAgentPerformance[] }>(
    `/support/reports/performance/?days=${days}`,
  );
}
export function runSupportEscalations() {
  return apiFetch<{ escalated: number; admin_notified: number }>(
    '/support/escalations/run/',
    { method: 'POST', body: '{}' },
  );
}
