import { apiFetch } from './client';
import type { QuotaSummary, SupportAgentPermission } from '../types/api';

export type AdminUser = QuotaSummary & {
  role?: string;
  first_name?: string;
  last_name?: string;
  is_staff?: boolean;
};

export type CreateUserPayload = {
  username: string;
  password: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  roles?: string[];
  is_staff?: boolean;
  phone?: string;
  gender?: string;
  quota_gb?: number;
};

export type ProfileData = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  role: string;
  role_label: string;
  quota: QuotaSummary;
  date_joined: string | null;
};

export function getMyQuota() {
  return apiFetch<QuotaSummary>('/account/quota/');
}

export function getProfile() {
  return apiFetch<ProfileData>('/account/profile/');
}

export function updateProfile(data: Partial<{ first_name: string; last_name: string; email: string; password: string }>) {
  return apiFetch<ProfileData>('/account/profile/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export function listAdminUsers() {
  return apiFetch<AdminUser[]>('/admin/users/');
}

export function createAdminUser(payload: CreateUserPayload) {
  return apiFetch('/admin/users/create/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateUserQuota(userId: number, allocatedBytes: number) {
  return apiFetch<QuotaSummary>(`/admin/users/${userId}/quota/`, {
    method: 'PATCH',
    body: JSON.stringify({ allocated_bytes: allocatedBytes }),
  });
}

export function listSupportAgents() {
  return apiFetch<SupportAgentPermission[]>('/admin/support-agents/');
}

export function setSupportReplyPermission(userId: number, canReply: boolean) {
  return apiFetch<SupportAgentPermission>(`/admin/support-agents/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ can_reply: canReply }),
  });
}

export function updateUserRole(userId: number, role: string) {
  return apiFetch(`/admin/roles/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
}

export type RoleDefinition = {
  id: number;
  code: string;
  name: string;
  description: string;
  permissions: Record<string, boolean>;
  is_system: boolean;
};

export function updateAdminUser(userId: number, data: Record<string, unknown>) {
  return apiFetch(`/admin/users/${userId}/update/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export function listRoleDefinitions() {
  return apiFetch<RoleDefinition[]>('/admin/roles-definitions/');
}

export function createRoleDefinition(data: { code: string; name: string; description?: string; permissions?: Record<string, boolean> }) {
  return apiFetch<RoleDefinition>('/admin/roles-definitions/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateRoleDefinition(id: number, data: Partial<RoleDefinition>) {
  return apiFetch<RoleDefinition>(`/admin/roles-definitions/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
