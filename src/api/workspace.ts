import { apiFetch } from './client';
import type {
  ActivityItem,
  DashboardStats,
  FileShareItem,
  MailItem,
  UserLookup,
} from '../types/api';

export function getDashboardStats() {
  return apiFetch<DashboardStats>('/files/dashboard-stats/');
}

export function listShares(direction: 'received' | 'sent' = 'received') {
  return apiFetch<FileShareItem[]>(`/files/shares/?direction=${direction}`);
}

export function createShare(
  fileId: number,
  sharedWith: number,
  permission: string,
  message = '',
  caps?: { can_download?: boolean; can_edit?: boolean; can_reshare?: boolean }
) {
  return apiFetch<FileShareItem>('/files/shares/', {
    method: 'POST',
    body: JSON.stringify({
      file: fileId,
      shared_with: sharedWith,
      permission,
      message,
      can_download: caps?.can_download ?? false,
      can_edit: caps?.can_edit ?? false,
      can_reshare: caps?.can_reshare ?? false,
    }),
  });
}

export function deleteShare(id: number) {
  return apiFetch<void>(`/files/shares/${id}/`, { method: 'DELETE' });
}

export function listActivity() {
  return apiFetch<ActivityItem[]>('/files/activity/');
}

export function listMail(box: 'inbox' | 'sent' = 'inbox') {
  return apiFetch<MailItem[]>(`/files/mail/?box=${box}`);
}

export function sendMail(recipient: number, subject: string, body: string, priority = 'normal') {
  return apiFetch<MailItem>('/files/mail/', {
    method: 'POST',
    body: JSON.stringify({ recipient, subject, body, priority }),
  });
}

export function getMail(id: number) {
  return apiFetch<MailItem>(`/files/mail/${id}/`);
}

export function lookupUsers(q = '') {
  return apiFetch<UserLookup[]>(`/files/users/lookup/?q=${encodeURIComponent(q)}`);
}
