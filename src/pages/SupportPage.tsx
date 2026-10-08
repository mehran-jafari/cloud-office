import { Bot, Headphones, MessageCircle, Send } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthProvider';
import {
  createConversation,
  listConversations,
  listOnlineAgents,
  sendSupportMessage,
  sendSupportPresence,
  setSupportOnline,
  type OnlineAgent,
} from '../api/support';
import type { SupportConversation } from '../types/api';
import { speechToText, suggestSupportReply, summarizeText } from '../api/ai';
import { AIAssist } from '../components/AIAssist';

const STATUS_LABEL: Record<string, string> = {
  open: 'باز',
  waiting_agent: 'در انتظار پشتیبان',
  waiting_user: 'در انتظار شما',
  ai_handling: 'پاسخ هوشمند',
  escalated: 'پیگیری ویژه',
  closed: 'بسته',
};

export function SupportPage() {
  const { user } = useAuth();
  const canReply = Boolean(user?.permissions?.reply_support);
  const isAdmin = Boolean(user?.permissions?.view_admin || user?.role === 'owner' || user?.role === 'admin');
  const [conversations, setConversations] = useState<SupportConversation[]>([]);
  const [agents, setAgents] = useState<OnlineAgent[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [body, setBody] = useState('');
  const [subject, setSubject] = useState('درخواست پشتیبانی');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [online, setOnline] = useState(Boolean(user?.is_support_online));
  const listRef = useRef<HTMLDivElement>(null);

  function refresh() {
    listConversations()
      .then(items => {
        setConversations(items);
        if (selected == null && items[0]) setSelected(items[0].id);
      })
      .catch(e => setError(e instanceof Error ? e.message : 'خطا'))
      .finally(() => setLoading(false));
    listOnlineAgents().then(setAgents).catch(() => setAgents([]));
  }

  useEffect(() => {
    refresh();
    const t = window.setInterval(() => {
      listConversations().then(setConversations).catch(() => {});
      listOnlineAgents().then(setAgents).catch(() => {});
    }, 8000);
    return () => window.clearInterval(t);
  }, []);

  // heartbeat حضور پشتیبان هر ۴۵ ثانیه وقتی آنلاین است
  useEffect(() => {
    if (!canReply || !online) return;
    const beat = () => {
      sendSupportPresence(true).catch(() => {});
    };
    beat();
    const t = window.setInterval(beat, 45000);
    return () => window.clearInterval(t);
  }, [canReply, online]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [selected, conversations]);

  const current = useMemo(
    () => conversations.find(c => c.id === selected) || null,
    [conversations, selected],
  );

  function pipelineInfo(pipeline?: SupportConversation['pipeline'] | SupportConversation['messages'][0]['pipeline']) {
    if (!pipeline || typeof pipeline !== 'object') return;
    const ai = (pipeline as { ai?: { replied?: boolean; needs_human?: boolean; confidence?: number } }).ai;
    if (ai?.replied && !ai.needs_human) {
      setInfo('پاسخ خودکار ثبت شد. در صورت نیاز می‌توانید ادامه دهید.');
    } else if (ai?.needs_human) {
      setInfo('پیام ثبت شد و برای پشتیبان انسانی ارسال گردید.');
    } else if ((pipeline as { notify?: { mode?: string } }).notify?.mode === 'offline_broadcast') {
      setInfo('در حال حاضر پشتیبان آنلاین نیست؛ پیام شما ثبت و به کارشناسان اطلاع داده شد.');
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSending(true);
    setError('');
    setInfo('');
    try {
      const conv = await createConversation(subject, body.trim());
      setConversations(prev => [conv, ...prev.filter(c => c.id !== conv.id)]);
      setSelected(conv.id);
      setBody('');
      pipelineInfo(conv.pipeline);
      // رفرش برای دیدن پیام AI اگر اضافه شده
      const fresh = await listConversations();
      setConversations(fresh);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ارسال ناموفق');
    } finally {
      setSending(false);
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!selected || !body.trim()) return;
    setSending(true);
    setError('');
    setInfo('');
    try {
      const msg = await sendSupportMessage(selected, body.trim());
      pipelineInfo(msg.pipeline);
      const fresh = await listConversations();
      setConversations(fresh);
      setBody('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ارسال ناموفق');
    } finally {
      setSending(false);
    }
  }

  async function toggleOnline() {
    try {
      const res = await setSupportOnline(!online);
      setOnline(res.is_support_online);
      if (res.is_support_online) {
        await sendSupportPresence(true);
      }
      listOnlineAgents().then(setAgents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'تغییر وضعیت ناموفق');
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">مرکز پشتیبانی</span>
          <h1>چت پشتیبانی</h1>
          <p>
            پیام‌ها ذخیره می‌شوند؛ در نبود پشتیبان، دستیار هوشمند پاسخ اولیه می‌دهد و در صورت نیاز شما را به کارشناس وصل می‌کند.
          </p>
        </div>
        {canReply && (
          <button className={online ? 'primary' : 'ghost'} onClick={() => void toggleOnline()}>
            <Headphones size={16} />
            {online ? 'آنلاین — برای آفلاین شدن کلیک کنید' : 'آنلاین شدن برای پاسخ‌گویی'}
          </button>
        )}
      </div>

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      {info && (
        <div className="panel" style={{ marginBottom: 12, borderColor: '#3cc78b55', color: '#8fe4b6' }}>
          {info}
        </div>
      )}

      {agents.length > 0 ? (
        <section className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <div>
              <h2>پشتیبان‌های آنلاین</h2>
              <p>در حال حاضر آماده پاسخ‌گویی</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {agents.map(a => (
              <div key={a.id} style={{ display: 'grid', justifyItems: 'center', gap: 6, width: 72 }}>
                {a.avatar_url ? (
                  <img
                    src={a.avatar_url}
                    alt=""
                    style={{ width: 48, height: 48, borderRadius: 14, objectFit: 'cover' }}
                  />
                ) : (
                  <div
                    className="avatar"
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 14,
                      background: a.gender === 'female' ? '#e879a8' : '#5b8def',
                      display: 'grid',
                      placeItems: 'center',
                      fontWeight: 700,
                      fontSize: 18,
                    }}
                  >
                    {a.gender === 'female' ? '♀' : '♂'}
                  </div>
                )}
                <small style={{ textAlign: 'center', fontSize: 10 }}>{a.first_name || a.username}</small>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 280px) 1fr', gap: 16 }}>
        <section className="panel" style={{ maxHeight: '70vh', overflow: 'auto' }}>
          <div className="panel-head">
            <div>
              <h2>{isAdmin || canReply ? 'همه گفتگوها' : 'گفتگوهای من'}</h2>
            </div>
          </div>
          {loading ? (
            <p style={{ color: 'var(--muted)', fontSize: 12 }}>بارگذاری...</p>
          ) : conversations.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 12 }}>هنوز گفتگویی نیست.</p>
          ) : (
            conversations.map(c => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelected(c.id)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'right',
                  background: selected === c.id ? '#7667f71c' : 'transparent',
                  border: 0,
                  color: '#e9edf7',
                  padding: '10px 8px',
                  borderRadius: 10,
                  cursor: 'pointer',
                  marginBottom: 4,
                }}
              >
                <b style={{ fontSize: 12 }}>{c.subject}</b>
                <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 4 }}>
                  {STATUS_LABEL[c.status] || c.status}
                  {c.ai_handled ? ' · هوشمند' : ''}
                  {(c.escalation_count || 0) > 0 ? ` · پیگیری ${c.escalation_count}` : ''}
                </div>
                {(isAdmin || canReply) && (
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{c.user_name}</div>
                )}
              </button>
            ))
          )}
        </section>

        <section className="panel" style={{ display: 'flex', flexDirection: 'column', minHeight: 420 }}>
          {!current ? (
            <form onSubmit={handleCreate} style={{ display: 'grid', gap: 10 }}>
              <div className="panel-head">
                <div>
                  <h2>گفتگوی جدید</h2>
                  <p>موضوع و پیام اول را بنویسید</p>
                </div>
              </div>
              <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="موضوع" />
              <textarea
                value={body}
                onChange={e => setBody(e.target.value)}
                rows={5}
                placeholder="پیام شما..."
              />
              <button className="primary" disabled={sending || !body.trim()}>
                <Send size={16} /> شروع گفتگو
              </button>
            </form>
          ) : (
            <>
              <div className="panel-head">
                <div>
                  <h2>{current.subject}</h2>
                  <p>
                    {STATUS_LABEL[current.status] || current.status}
                    {current.assigned_agent_name ? ` · کارشناس: ${current.assigned_agent_name}` : ''}
                    {current.ai_confidence != null
                      ? ` · اطمینان AI: ${Math.round(Number(current.ai_confidence) * 100)}٪`
                      : ''}
                  </p>
                </div>
                <button type="button" className="ghost" onClick={() => setSelected(null)}>
                  گفتگوی جدید
                </button>
              </div>

              <div
                ref={listRef}
                style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 10, padding: '8px 0' }}
              >
                {(current.messages || []).map(m => {
                  const mine = m.sender === user?.id && !m.is_ai;
                  const isAi = Boolean(m.is_ai);
                  return (
                    <div
                      key={m.id}
                      style={{
                        alignSelf: mine ? 'flex-end' : 'flex-start',
                        maxWidth: '85%',
                        background: isAi ? '#1a3d4a' : mine ? '#7667f733' : '#ffffff0d',
                        border: isAi ? '1px solid #39d7bb44' : '1px solid transparent',
                        borderRadius: 14,
                        padding: '10px 12px',
                      }}
                    >
                      <div
                        style={{
                          fontSize: 10,
                          color: isAi ? '#39d7bb' : 'var(--muted)',
                          marginBottom: 4,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        {isAi ? (
                          <>
                            <Bot size={12} /> پاسخ هوشمند
                          </>
                        ) : (
                          m.sender_name
                        )}
                        {m.is_staff_reply && !isAi ? ' · پشتیبان' : ''}
                      </div>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>{m.body}</div>
                      <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 6 }}>
                        {new Date(m.created_at).toLocaleString('fa-IR')}
                      </div>
                    </div>
                  );
                })}
              </div>

              <form onSubmit={handleSend} style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <input
                  style={{ flex: 1 }}
                  value={body}
                  onChange={e => setBody(e.target.value)}
                  placeholder={canReply ? 'پاسخ شما...' : 'پیام بعدی...'}
                />
                <button className="primary" disabled={sending || !body.trim()}>
                  <Send size={16} />
                </button>
              </form>

              <div style={{ marginTop: 12, display: 'grid', gap: 10 }}>
                {canReply && (
                  <AIAssist
                    title="پیشنهاد پاسخ پشتیبانی"
                    buttonLabel="پیشنهاد پاسخ"
                    onRun={async () => {
                      const text = (current.messages || []).map(m => `${m.is_staff_reply ? 'پشتیبان' : 'کاربر'}: ${m.body}`).join('\n');
                      const r = await suggestSupportReply(text || body);
                      return { text: r.text || '', tokens_used: r.tokens_used, remaining_tokens: r.remaining_tokens, model: r.model, provider: r.provider };
                    }}
                    onApply={text => setBody(text)}
                  />
                )}
                {(current.messages || []).length > 2 && (
                  <AIAssist
                    title="خلاصه گفتگو"
                    buttonLabel="خلاصه تیکت"
                    onRun={async () => {
                      const text = (current.messages || []).map(m => `${m.sender_name}: ${m.body}`).join('\n');
                      const r = await summarizeText(text, 'support');
                      return { text: r.text || '', tokens_used: r.tokens_used, remaining_tokens: r.remaining_tokens, model: r.model, provider: r.provider };
                    }}
                  />
                )}
                <label style={{ fontSize: 11, color: '#bfc9d8' }}>
                  گفتار به متن
                  <input
                    type="file"
                    accept="audio/*,video/*"
                    onChange={async e => {
                      const f = e.target.files?.[0];
                      if (!f) return;
                      try {
                        const res = await speechToText(f, f.name);
                        if (res.usable === false) setError(res.text || 'STT در دسترس نیست');
                        else setBody(prev => (prev ? prev + '\n' : '') + (res.text || ''));
                      } catch (err) {
                        setError(err instanceof Error ? err.message : 'STT ناموفق');
                      }
                    }}
                  />
                </label>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
