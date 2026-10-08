import { useEffect } from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

export type ToastKind = 'success' | 'error' | 'info';

export type ToastMessage = {
  id: number;
  kind: ToastKind;
  title: string;
  body?: string;
};

type Props = {
  toast: ToastMessage | null;
  onClose: () => void;
  durationMs?: number;
};

export function Toast({ toast, onClose, durationMs = 3500 }: Props) {
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(onClose, durationMs);
    return () => window.clearTimeout(t);
  }, [toast, onClose, durationMs]);

  if (!toast) return null;

  const Icon = toast.kind === 'success' ? CheckCircle2 : AlertCircle;
  const accent =
    toast.kind === 'success' ? 'var(--ok, #35b982)' :
    toast.kind === 'error' ? 'var(--danger, #e05a5a)' :
    'var(--accent, #3489f5)';

  return (
    <div
      className="app-toast glass"
      role="status"
      style={{
        position: 'fixed',
        bottom: 24,
        left: 24,
        zIndex: 100,
        minWidth: 260,
        maxWidth: 360,
        padding: '12px 14px',
        borderRadius: 14,
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
        boxShadow: '0 10px 30px rgba(0,0,0,0.12)',
        borderInlineStart: `3px solid ${accent}`,
      }}
    >
      <Icon size={18} style={{ color: accent, marginTop: 2, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <b style={{ fontSize: 13, display: 'block' }}>{toast.title}</b>
        {toast.body && (
          <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>{toast.body}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="بستن"
        style={{ background: 'transparent', border: 0, cursor: 'pointer', padding: 2, color: 'var(--muted)' }}
      >
        <X size={16} />
      </button>
    </div>
  );
}

let _seq = 1;
export function makeToast(kind: ToastKind, title: string, body?: string): ToastMessage {
  return { id: _seq++, kind, title, body };
}
