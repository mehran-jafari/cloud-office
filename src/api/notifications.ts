import { apiFetch } from './client';

export type AppNotification = {
  id: number;
  kind: 'share' | 'mail' | 'support' | 'system' | string;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  created_at: string;
};

export type UnreadSummary = {
  count: number;
  latest_id: number | null;
  latest_title: string | null;
  latest_body: string;
  latest_link: string;
  latest_kind: string | null;
  latest_at: string | null;
};

export function listNotifications() {
  return apiFetch<AppNotification[]>('/files/notifications/');
}

export function getUnreadSummary() {
  return apiFetch<UnreadSummary>('/files/notifications/unread-count/');
}

export function markNotificationsRead(ids?: number[]) {
  return apiFetch<{ marked: number }>('/files/notifications/mark-read/', {
    method: 'POST',
    body: JSON.stringify(ids ? { ids } : {}),
  });
}
