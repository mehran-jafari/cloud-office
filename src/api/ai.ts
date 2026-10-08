import { apiFetch, getAccessToken } from './client';

export type AIResult = {
  text?: string;
  tokens_used?: number;
  model?: string;
  remaining_tokens?: number;
  provider?: string;
  tone?: string;
  usable?: boolean;
  results?: Array<{ file_id: number; name: string; score: number; vector_score?: number; preview: string }>;
  provider_configured?: boolean;
  monthly_tokens?: number;
  used_tokens?: number;
  count?: number;
  query?: string;
  features?: Record<string, boolean>;
};

export function aiStatus() {
  return apiFetch<AIResult>('/ai/status/');
}

export function draftMail(
  subject: string,
  notes: string,
  tone: 'formal' | 'friendly' | 'short' = 'formal',
  recipientName = ''
) {
  return apiFetch<AIResult>('/ai/draft-mail/', {
    method: 'POST',
    body: JSON.stringify({ subject, notes, tone, recipient_name: recipientName }),
  });
}

export function summarizeText(text: string, purpose: 'general' | 'support' = 'general') {
  return apiFetch<AIResult>('/ai/summarize/', {
    method: 'POST',
    body: JSON.stringify({ text, purpose }),
  });
}

export function suggestSupportReply(conversation: string) {
  return apiFetch<AIResult>('/ai/support-reply/', {
    method: 'POST',
    body: JSON.stringify({ conversation }),
  });
}

export function meetingSummary(transcript: string, title = 'جلسه') {
  return apiFetch<AIResult>('/ai/meeting-summary/', {
    method: 'POST',
    body: JSON.stringify({ transcript, title }),
  });
}

export function semanticSearch(query: string, limit = 10) {
  return apiFetch<AIResult>('/ai/semantic-search/', {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  });
}

export function indexFile(fileId: number, text = '') {
  return apiFetch<AIResult>('/ai/index-file/', {
    method: 'POST',
    body: JSON.stringify({ file_id: fileId, text }),
  });
}

export async function speechToText(file: Blob, filename = 'audio.webm') {
  const API_URL = import.meta.env.VITE_API_URL ?? '/api';
  const form = new FormData();
  form.append('audio', file, filename);
  const headers: HeadersInit = {};
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/ai/stt/`, {
    method: 'POST',
    headers,
    body: form,
    credentials: 'include',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? 'تبدیل گفتار ناموفق بود');
  }
  return res.json() as Promise<AIResult>;
}

export type CreatedFileInfo = {
  id: number;
  name: string;
  type?: string;
  size?: string;
  updated?: string;
  owner?: string;
  color?: string;
};

export function createFileWithAI(title: string, prompt: string, docType = 'txt', save = true) {
  return apiFetch<AIResult & { file?: CreatedFileInfo; saved?: boolean; content?: string; title?: string }>(
    '/ai/create-file/',
    {
      method: 'POST',
      body: JSON.stringify({ title, prompt, doc_type: docType, save }),
    }
  );
}


export type ProofIssue = {
  original: string;
  suggestion: string;
  reason?: string;
};

export function proofreadText(text: string) {
  return apiFetch<AIResult & { issues?: ProofIssue[]; text?: string }>('/ai/proofread/', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export type ConferenceDocKind = 'minutes' | 'actions' | 'executive' | 'email' | 'transcript_clean';

export function conferenceDoc(transcript: string, docKind: ConferenceDocKind, title = 'جلسه') {
  return apiFetch<AIResult & { doc_kind?: string }>('/ai/conference-doc/', {
    method: 'POST',
    body: JSON.stringify({ transcript, doc_kind: docKind, title }),
  });
}
