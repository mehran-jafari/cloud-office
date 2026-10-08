const API_URL = import.meta.env.VITE_API_URL ?? '/api';
let accessToken: string | null = null;
let refreshPromise: Promise<string> | null = null;
export function setAccessToken(token: string | null) { accessToken = token; }
export function getAccessToken() { return accessToken; }
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: 'include' });
  if (response.status === 401 && !path.includes('/auth/refresh') && !path.includes('/auth/login')) {
    try {
      refreshPromise ??= import('./auth').then(({ refreshAccessToken }) => refreshAccessToken().then(result => result.access)).finally(() => { refreshPromise = null; });
      const renewed = await refreshPromise;
      const retryHeaders = new Headers(options.headers);
      if (options.body && !retryHeaders.has('Content-Type')) retryHeaders.set('Content-Type', 'application/json');
      retryHeaders.set('Authorization', `Bearer ${renewed}`);
      const retry = await fetch(`${API_URL}${path}`, { ...options, headers: retryHeaders, credentials: 'include' });
      if (retry.ok) return retry.status === 204 ? undefined as T : retry.json() as Promise<T>;
    } catch { /* نشست واقعاً منقضی شده است */ }
    setAccessToken(null); throw new Error('نشست شما منقضی شده است');
  }
  if (response.status === 401) { setAccessToken(null); throw new Error('نشست شما منقضی شده است'); }
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? 'خطایی در ارتباط با سرور رخ داد'); }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
