import { apiFetch, getAccessToken } from './client';

export type DeskDevice = {
  desk_id: string;
  token: string;
  alias: string;
  password: string;
  hostname: string;
  os_name: string;
  online: boolean;
  last_seen?: string;
};

export type DeskSession = {
  session_key: string;
  status: string;
  host_desk_id: string;
  client_desk_id: string;
  host_alias?: string;
  client_alias?: string;
  started_at?: string;
};

export type DeskContact = {
  id: number;
  desk_id: string;
  alias: string;
  last_connected?: string;
};

const deskHeaders = (token?: string): HeadersInit => {
  const h: HeadersInit = {};
  if (token) h['X-Desk-Token'] = token;
  return h;
};

export function registerDevice(payload: Partial<DeskDevice> & { token?: string }) {
  return apiFetch<DeskDevice>('/desk/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: deskHeaders(payload.token),
  });
}

export function getMyDevice(token?: string) {
  return apiFetch<DeskDevice>('/desk/me/', { headers: deskHeaders(token) });
}

export function patchMyDevice(data: { alias?: string; rotate_password?: boolean }, token?: string) {
  return apiFetch<DeskDevice>('/desk/me/', {
    method: 'PATCH',
    body: JSON.stringify(data),
    headers: deskHeaders(token),
  });
}

export function lookupDevice(deskId: string) {
  return apiFetch<{ desk_id: string; alias: string; online: boolean }>(`/desk/lookup/${deskId}/`);
}

export function connectRemote(deskId: string, password = '', token?: string) {
  return apiFetch<DeskSession>('/desk/connect/', {
    method: 'POST',
    body: JSON.stringify({ desk_id: deskId, password }),
    headers: deskHeaders(token),
  });
}

export function sessionAction(sessionKey: string, action: 'accept' | 'reject' | 'end', token?: string) {
  return apiFetch<DeskSession>(`/desk/sessions/${sessionKey}/`, {
    method: 'POST',
    body: JSON.stringify({ action }),
    headers: deskHeaders(token),
  });
}

export function listDeskSessions(token?: string) {
  return apiFetch<DeskSession[]>('/desk/sessions/', { headers: deskHeaders(token) });
}

export function listContacts(token?: string) {
  return apiFetch<DeskContact[]>('/desk/contacts/', { headers: deskHeaders(token) });
}

export function addContact(deskId: string, alias = '', token?: string) {
  return apiFetch<DeskContact>('/desk/contacts/', {
    method: 'POST',
    body: JSON.stringify({ desk_id: deskId, alias }),
    headers: deskHeaders(token),
  });
}

export function createConference(title: string, participantIds: string[] = [], token?: string) {
  return apiFetch<{ code: string; title: string }>('/desk/conference/', {
    method: 'POST',
    body: JSON.stringify({ title, participant_ids: participantIds }),
    headers: deskHeaders(token),
  });
}

export function getIceServers() {
  return apiFetch<{ iceServers: RTCIceServer[] }>('/desk/ice/');
}

export function formatDeskId(id?: string) {
  if (!id) return '— — —';
  const d = id.replace(/\D/g, '');
  return d.replace(/(\d{3})(?=\d)/g, '$1 ').trim();
}

export function parseDeskIds(input: string): string[] {
  return input
    .split(/[\s,;]+/)
    .map(s => s.replace(/\D/g, ''))
    .filter(s => s.length === 9);
}

/** WebSocket سیگنالینگ Desk */
export function connectDeskSignal(token: string, handlers: {
  onOpen?: () => void;
  onClose?: () => void;
  onMessage?: (msg: Record<string, unknown>) => void;
}) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const host = location.host;
  let socket: WebSocket | null = null;
  let pingTimer: number | null = null;
  let retry = 0;
  let closed = false;
  let retryTimer: number | null = null;

  function open() {
    if (closed) return;
    // Vite proxy should forward /ws
    // توکن دستگاه فقط از طریق subprotocol ارسال می‌شود (نه query string)
    socket = new WebSocket(`${proto}://${host}/ws/desk/`, ['desk_token', token]);
    socket.onopen = () => {
      retry = 0;
      pingTimer = window.setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'ping' }));
      }, 15000);
      handlers.onOpen?.();
    };
    socket.onmessage = ev => {
      try {
        handlers.onMessage?.(JSON.parse(ev.data));
      } catch { /* */ }
    };
    socket.onclose = () => {
      if (pingTimer) window.clearInterval(pingTimer);
      handlers.onClose?.();
      if (closed) return;
      const wait = Math.min(15000, 1000 * 2 ** retry);
      retry += 1;
      retryTimer = window.setTimeout(open, wait);
    };
  }
  open();
  return {
    send(payload: Record<string, unknown>) {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload));
    },
    close() {
      closed = true;
      if (pingTimer) window.clearInterval(pingTimer);
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    },
  };
}
