import { apiFetch, getAccessToken } from './client';
import type { FileItem, Paginated } from '../types/api';

export type UploadProgress = {
  loaded: number;
  total: number;
  percent: number;
};

export async function listFiles(search = '') {
  return apiFetch<Paginated<FileItem>>(`/files/items/?search=${encodeURIComponent(search)}`);
}

export function uploadFile(
  file: globalThis.File,
  onProgress?: (p: UploadProgress) => void
): Promise<FileItem> {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}/files/items/`);
    xhr.withCredentials = true;
    const token = getAccessToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.upload.onprogress = event => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress?.({ loaded: event.loaded, total: event.total, percent });
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as FileItem);
        } catch {
          reject(new Error('پاسخ سرور نامعتبر است'));
        }
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new Error(body?.detail ?? 'آپلود ناموفق بود'));
        } catch {
          reject(new Error('آپلود ناموفق بود'));
        }
      }
    };
    xhr.onerror = () => reject(new Error('خطای شبکه هنگام آپلود'));
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

export function filePreviewUrl(id: number, inline = true) {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  return `${API_URL}/files/${id}/download/?inline=${inline ? '1' : '0'}`;
}

export async function downloadFile(id: number, name: string) {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  const headers: HeadersInit = {};
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${API_URL}/files/${id}/download/`, { headers, credentials: 'include' });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? 'دانلود ناموفق بود');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export async function fetchFileBlob(id: number): Promise<Blob> {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  const headers: HeadersInit = {};
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${API_URL}/files/${id}/download/?inline=1`, { headers, credentials: 'include' });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? 'بارگذاری پیش‌نمایش ناموفق بود');
  }
  return response.blob();
}

export function isEditableFile(file: FileItem) {
  return file.type !== 'folder' && /\.(docx?|xlsx?|pptx?|odt|ods|odp|rtf|txt)$/i.test(file.name);
}

export function mediaKind(file: FileItem): 'image' | 'video' | 'audio' | 'pdf' | 'office' | 'other' {
  const n = file.name.toLowerCase();
  if (/\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(n) || file.type === 'image') return 'image';
  if (/\.(mp4|webm|ogg|mov|mkv)$/i.test(n)) return 'video';
  if (/\.(mp3|wav|ogg|m4a|aac)$/i.test(n)) return 'audio';
  if (/\.pdf$/i.test(n) || file.type === 'pdf') return 'pdf';
  if (isEditableFile(file)) return 'office';
  return 'other';
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

export function convertFile(id: number, target: 'pdf' | 'docx') {
  return apiFetch<FileItem>(`/files/${id}/convert/`, {
    method: 'POST',
    body: JSON.stringify({ target }),
  });
}

export function isPdfFile(file: FileItem) {
  return /\.pdf$/i.test(file.name) || file.type === 'pdf';
}

export function isWordFile(file: FileItem) {
  return /\.docx?$/i.test(file.name);
}

export type FolderItem = {
  id: number;
  name: string;
  parent: number | null;
  created_at?: string;
};

export function listFolders() {
  return apiFetch<Paginated<FolderItem> | FolderItem[]>('/files/folders/');
}

export function createFolder(name: string, parent: number | null = null) {
  return apiFetch<FolderItem>('/files/folders/', {
    method: 'POST',
    body: JSON.stringify({ name, parent }),
  });
}

export function renameFolder(id: number, name: string) {
  return apiFetch<FolderItem>(`/files/folders/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  });
}

export function deleteFolder(id: number) {
  return apiFetch<void>(`/files/folders/${id}/`, { method: 'DELETE' });
}

export function renameFile(id: number, name: string) {
  return apiFetch<FileItem>(`/files/items/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  });
}

export function deleteFile(id: number) {
  return apiFetch<void>(`/files/items/${id}/`, { method: 'DELETE' });
}

export type BulkAction =
  | { action: 'rename'; file_ids?: number[]; folder_ids?: number[]; name: string }
  | { action: 'move'; file_ids?: number[]; folder_ids?: number[]; target_folder_id: number | null }
  | { action: 'copy'; file_ids?: number[]; folder_ids?: number[]; target_folder_id: number | null }
  | { action: 'delete'; file_ids?: number[]; folder_ids?: number[] };

export function bulkAction(payload: BulkAction) {
  return apiFetch<Record<string, unknown>>('/files/bulk/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function uploadFileToFolder(
  file: globalThis.File,
  folderId: number | null,
  onProgress?: (p: UploadProgress) => void
): Promise<FileItem> {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}/files/items/`);
    xhr.withCredentials = true;
    const token = getAccessToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.upload.onprogress = event => {
      if (!event.lengthComputable) return;
      onProgress?.({
        loaded: event.loaded,
        total: event.total,
        percent: Math.round((event.loaded / event.total) * 100),
      });
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as FileItem);
        } catch {
          reject(new Error('پاسخ سرور نامعتبر است'));
        }
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new Error(body?.detail ?? 'آپلود ناموفق بود'));
        } catch {
          reject(new Error('آپلود ناموفق بود'));
        }
      }
    };
    xhr.onerror = () => reject(new Error('خطای شبکه هنگام آپلود'));
    const form = new FormData();
    form.append('file', file);
    if (folderId) form.append('folder', String(folderId));
    xhr.send(form);
  });
}

// --- Trash ---
export type TrashResponse = {
  files: FileItem[];
  folders: FolderItem[];
};

export function listTrash() {
  return apiFetch<TrashResponse>('/files/trash/');
}

export function restoreTrash(file_ids: number[] = [], folder_ids: number[] = []) {
  return apiFetch<{ restored_files: number; restored_folders: number }>('/files/trash/restore/', {
    method: 'POST',
    body: JSON.stringify({ file_ids, folder_ids }),
  });
}

export function purgeTrash(opts: { file_ids?: number[]; folder_ids?: number[]; empty_all?: boolean } = {}) {
  return apiFetch<{ purged_files: number; purged_folders: number }>('/files/trash/purge/', {
    method: 'POST',
    body: JSON.stringify(opts),
  });
}

// --- Public share links ---
export type PublicShareLink = {
  id: number;
  file: number;
  file_id: number;
  file_name: string;
  token: string;
  permission: 'view' | 'download';
  expires_at: string | null;
  max_downloads: number | null;
  download_count: number;
  is_active: boolean;
  note: string;
  created_at: string;
  is_expired: boolean;
  public_url: string;
  has_password: boolean;
};

export function listPublicLinks(fileId?: number) {
  const q = fileId ? `?file=${fileId}` : '';
  return apiFetch<PublicShareLink[]>(`/files/public-links/${q}`);
}

export function createPublicLink(payload: {
  file: number;
  permission?: 'view' | 'download';
  expires_at?: string | null;
  max_downloads?: number | null;
  password?: string;
  note?: string;
}) {
  return apiFetch<PublicShareLink>('/files/public-links/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function revokePublicLink(id: number) {
  return apiFetch<void>(`/files/public-links/${id}/`, { method: 'DELETE' });
}

export function accessPublicShare(token: string, password = '') {
  return apiFetch<{
    file_id: number;
    file_name: string;
    mime_type: string;
    size_bytes: number;
    permission: string;
    can_download: boolean;
  }>(`/files/public/share/${token}/`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export function publicShareDownloadUrl(token: string, password = '') {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  const q = password ? `?password=${encodeURIComponent(password)}` : '';
  return `${API_URL}/files/public/share/${token}/${q}`;
}

// --- Advanced search ---
export type AdvancedSearchParams = {
  q?: string;
  type?: string;
  folder?: number | null;
  date_from?: string;
  date_to?: string;
  min_size?: number;
  max_size?: number;
  include_shared?: boolean;
  limit?: number;
};

export function advancedSearch(params: AdvancedSearchParams) {
  const sp = new URLSearchParams();
  if (params.q) sp.set('q', params.q);
  if (params.type) sp.set('type', params.type);
  if (params.folder != null) sp.set('folder', String(params.folder));
  if (params.date_from) sp.set('date_from', params.date_from);
  if (params.date_to) sp.set('date_to', params.date_to);
  if (params.min_size != null) sp.set('min_size', String(params.min_size));
  if (params.max_size != null) sp.set('max_size', String(params.max_size));
  if (params.include_shared) sp.set('include_shared', '1');
  if (params.limit) sp.set('limit', String(params.limit));
  return apiFetch<{ count: number; results: FileItem[] }>(`/files/search/?${sp.toString()}`);
}

// --- Audit ---
export type AuditEntry = {
  id: number;
  user?: number;
  username?: string;
  action: string;
  title: string;
  detail?: string;
  target_type?: string;
  target_id?: number;
  created_at: string;
};

export function fetchAudit(params: {
  user?: number | string;
  action?: string;
  date_from?: string;
  date_to?: string;
  q?: string;
  limit?: number;
} = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  });
  return apiFetch<{ results: AuditEntry[]; summary: { action: string; count: number }[]; count: number }>(
    `/files/audit/?${sp.toString()}`
  );
}
