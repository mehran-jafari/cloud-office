import { Bell, Mail, MessageCircle, Share2, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getUnreadSummary,
  listNotifications,
  markNotificationsRead,
  type AppNotification,
} from '../api/notifications';

const kindIcon = (kind: string) => {
  if (kind === 'share') return Share2;
  if (kind === 'mail') return Mail;
  if (kind === 'support') return MessageCircle;
  return Bell;
};

export function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const [count, setCount] = useState(0);
  const [toast, setToast] = useState<AppNotification | null>(null);
  const lastSeenId = useRef<number | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  async function poll() {
    try {
      const summary = await getUnreadSummary();
      setCount(summary.count);
      if (
        summary.latest_id &&
        lastSeenId.current != null &&
        summary.latest_id > lastSeenId.current &&
        summary.count > 0
      ) {
        setToast({
          id: summary.latest_id,
          kind: summary.latest_kind || 'system',
          title: summary.latest_title || 'اعلان جدید',
          body: summary.latest_body || '',
          link: summary.latest_link || '/',
          is_read: false,
          created_at: summary.latest_at || new Date().toISOString(),
        });
        window.setTimeout(() => setToast(null), 6000);
      }
      if (summary.latest_id) lastSeenId.current = summary.latest_id;
      else if (lastSeenId.current == null) lastSeenId.current = 0;
    } catch {
      /* silent */
    }
  }

  async function loadList() {
    try {
      const data = await listNotifications();
      setItems(data);
      const unread = data.filter(n => !n.is_read).length;
      setCount(unread);
    } catch {
      /* silent */
    }
  }

  useEffect(() => {
    poll();
    const t = window.setInterval(poll, 12000);
    return () => window.clearInterval(t);
  }, []);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      await loadList();
      await markNotificationsRead();
      setCount(0);
      setItems(prev => prev.map(n => ({ ...n, is_read: true })));
    }
  }

  function openItem(n: AppNotification) {
    setOpen(false);
    setToast(null);
    if (n.link) navigate(n.link);
  }

  return (
    <div ref={panelRef} style={{ position: 'relative' }}>
      <button className="icon-button" aria-label="اعلان‌ها" onClick={toggle} style={{ position: 'relative' }}>
        <Bell size={20} />
        {count > 0 && (
          <span
            style={{
              position: 'absolute',
              top: 2,
              left: 2,
              minWidth: 16,
              height: 16,
              borderRadius: 8,
              background: '#e05a5a',
              color: '#fff',
              fontSize: 10,
              display: 'grid',
              placeItems: 'center',
              padding: '0 4px',
              fontWeight: 700,
            }}
          >
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            width: 320,
            maxHeight: 380,
            overflow: 'auto',
            background: '#151c2c',
            border: '1px solid var(--line)',
            borderRadius: 14,
            boxShadow: '0 16px 40px #00000066',
            zIndex: 60,
            padding: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', fontSize: 12, color: 'var(--muted)' }}>
            <b style={{ color: '#e9edf7' }}>اعلان‌ها</b>
            <button type="button" onClick={() => setOpen(false)} style={{ background: 'transparent', border: 0, color: 'var(--muted)', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>
          {items.length === 0 ? (
            <p style={{ padding: 12, fontSize: 12, color: 'var(--muted)', margin: 0 }}>اعلانی نیست</p>
          ) : (
            items.map(n => {
              const Icon = kindIcon(n.kind);
              return (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => openItem(n)}
                  style={{
                    display: 'flex',
                    gap: 10,
                    width: '100%',
                    textAlign: 'right',
                    background: n.is_read ? 'transparent' : '#7667f714',
                    border: 0,
                    color: '#e9edf7',
                    padding: 10,
                    borderRadius: 10,
                    cursor: 'pointer',
                  }}
                >
                  <span style={{ width: 32, height: 32, borderRadius: 10, background: '#ffffff10', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
                    <Icon size={15} />
                  </span>
                  <span style={{ display: 'grid', gap: 2, minWidth: 0 }}>
                    <b style={{ fontSize: 12 }}>{n.title}</b>
                    {n.body && <small style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.body}</small>}
                    <small style={{ color: 'var(--muted)', fontSize: 10 }}>{new Date(n.created_at).toLocaleString('fa-IR')}</small>
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}

      {toast && (
        <div
          role="status"
          style={{
            position: 'fixed',
            top: 20,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 100,
            minWidth: 280,
            maxWidth: 'min(420px, 92vw)',
            background: '#1a2235',
            border: '1px solid #7667f788',
            borderRadius: 16,
            boxShadow: '0 20px 50px #00000088',
            padding: '14px 16px',
            display: 'flex',
            gap: 12,
            alignItems: 'flex-start',
            cursor: 'pointer',
          }}
          onClick={() => openItem(toast)}
        >
          <span style={{ width: 36, height: 36, borderRadius: 12, background: '#7667f733', display: 'grid', placeItems: 'center' }}>
            {(() => { const Icon = kindIcon(toast.kind); return <Icon size={18} />; })()}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <b style={{ fontSize: 13 }}>{toast.title}</b>
            {toast.body && <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>{toast.body}</p>}
            <small style={{ color: '#9e95ff', fontSize: 10 }}>برای مشاهده کلیک کنید</small>
          </div>
          <button
            type="button"
            onClick={e => { e.stopPropagation(); setToast(null); }}
            style={{ background: 'transparent', border: 0, color: 'var(--muted)', cursor: 'pointer' }}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
