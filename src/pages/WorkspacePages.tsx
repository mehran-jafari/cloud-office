import { Activity, Mail, Send, Share2, Trash2 } from 'lucide-react';
import { useEffect, useState, type CSSProperties } from 'react';
import { listFiles } from '../api/files';
import {
  createShare,
  deleteShare,
  getMail,
  listActivity,
  listMail,
  listShares,
  lookupUsers,
  sendMail,
} from '../api/workspace';
import type { ActivityItem, FileItem, FileShareItem, MailItem, UserLookup } from '../types/api';
import { draftMail, summarizeText } from '../api/ai';
import { AIAssist } from '../components/AIAssist';
import { SpellCheckEditor } from '../components/SpellCheckEditor';

export function SharedPage() {
  const [direction, setDirection] = useState<'received' | 'sent'>('received');
  const [shares, setShares] = useState<FileShareItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [users, setUsers] = useState<UserLookup[]>([]);
  const [fileId, setFileId] = useState('');
  const [userId, setUserId] = useState('');
  // فقط همین فلگ‌ها منبع حقیقت هستند
  const [canView, setCanView] = useState(true);
  const [canDownload, setCanDownload] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [canReshare, setCanReshare] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [loading, setLoading] = useState(true);

  function permissionFromFlags() {
    if (canReshare) return 'full' as const;
    if (canEdit) return 'edit' as const;
    if (canDownload) return 'download' as const;
    return 'view' as const;
  }

  function applyPreset(level: 'view' | 'download' | 'edit' | 'full') {
    setCanView(true);
    setCanDownload(level === 'download' || level === 'edit' || level === 'full');
    setCanEdit(level === 'edit' || level === 'full');
    setCanReshare(level === 'full');
  }

  function refresh() {
    setLoading(true);
    Promise.all([listShares(direction), listFiles(), lookupUsers()])
      .then(([s, f, u]) => {
        setShares(s);
        setFiles(f.results);
        setUsers(u);
      })
      .catch(e => setError(e instanceof Error ? e.message : 'خطا'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { refresh(); }, [direction]);

  async function handleShare(e: React.FormEvent) {
    e.preventDefault();
    if (!fileId || !userId) return setError('فایل و کاربر را انتخاب کنید');
    setError('');
    setOk('');
    try {
      await createShare(Number(fileId), Number(userId), permissionFromFlags(), message, {
        can_download: canDownload,
        can_edit: canEdit,
        can_reshare: canReshare,
      });
      setMessage('');
      setOk('اشتراک با موفقیت ثبت شد');
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'اشتراک‌گذاری ناموفق');
    }
  }

  /** فقط دسترسی‌های فعال را برمی‌گرداند — غیرفعال‌ها اصلاً نمایش داده نمی‌شوند */
  function activeCapLabels(c: { view?: boolean; download?: boolean; copy?: boolean; edit?: boolean; reshare?: boolean }) {
    const items: string[] = [];
    if (c.view) items.push('مشاهده');
    if (c.download || c.copy) items.push('دانلود/کپی');
    if (c.edit) items.push('ویرایش');
    if (c.reshare) items.push('اشتراک مجدد');
    return items;
  }

  const summaryItems = [
    canView ? 'مشاهده' : null,
    canDownload ? 'دانلود/کپی' : null,
    canEdit ? 'ویرایش' : null,
    canReshare ? 'اشتراک مجدد' : null,
  ].filter(Boolean) as string[];

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">کنترل دسترسی فایل</span>
          <h1>اشتراک‌گذاری حرفه‌ای</h1>
          <p>فقط دسترسی‌هایی که تیک می‌زنید به گیرنده داده و نمایش داده می‌شود.</p>
        </div>
      </div>
      {error && <div className="form-error" role="alert">{error}</div>}
      {ok && <div className="panel" style={{ marginBottom: 12, borderColor: '#3cc78b55', color: '#8fe4b6' }}>{ok}</div>}

      <section className="panel" style={{ marginBottom: 18 }}>
        <div className="panel-head">
          <div>
            <h2>اشتراک جدید</h2>
            <p>پیش‌فرض سریع را انتخاب کنید یا تیک‌ها را دستی تنظیم کنید. بدون تیک = بدون آن دسترسی.</p>
          </div>
        </div>
        <form onSubmit={handleShare} style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <label style={lab}>
              فایل
              <select value={fileId} onChange={e => setFileId(e.target.value)} required style={inp}>
                <option value="">انتخاب فایل...</option>
                {files.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </label>
            <label style={lab}>
              کاربر گیرنده
              <select value={userId} onChange={e => setUserId(e.target.value)} required style={inp}>
                <option value="">انتخاب کاربر...</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.first_name || u.username} ({u.username})</option>)}
              </select>
            </label>
            <label style={lab}>
              پیش‌فرض سریع
              <select
                value={permissionFromFlags()}
                onChange={e => applyPreset(e.target.value as 'view' | 'download' | 'edit' | 'full')}
                style={inp}
              >
                <option value="view">فقط مشاهده</option>
                <option value="download">مشاهده + دانلود/کپی</option>
                <option value="edit">مشاهده + دانلود + ویرایش</option>
                <option value="full">کامل (ویرایش + اشتراک مجدد)</option>
              </select>
            </label>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: 12, color: '#bfc9d8' }}>
            <label>
              <input type="checkbox" checked={canView} disabled /> مشاهده (همیشه)
            </label>
            <label>
              <input
                type="checkbox"
                checked={canDownload}
                onChange={e => {
                  const on = e.target.checked;
                  setCanDownload(on);
                  if (!on) {
                    setCanEdit(false);
                    setCanReshare(false);
                  }
                }}
              />{' '}دانلود / کپی
            </label>
            <label>
              <input
                type="checkbox"
                checked={canEdit}
                onChange={e => {
                  const on = e.target.checked;
                  setCanEdit(on);
                  if (on) setCanDownload(true);
                  else setCanReshare(false);
                }}
              />{' '}ویرایش
            </label>
            <label>
              <input
                type="checkbox"
                checked={canReshare}
                onChange={e => {
                  const on = e.target.checked;
                  setCanReshare(on);
                  if (on) {
                    setCanDownload(true);
                    setCanEdit(true);
                  }
                }}
              />{' '}اشتراک‌گذاری مجدد
            </label>
          </div>

          <div className="panel" style={{ background: '#ffffff06', padding: 12, fontSize: 12 }}>
            <b style={{ color: '#e9edf7' }}>دسترسی‌هایی که به گیرنده داده می‌شود:</b>
            {summaryItems.length === 0 ? (
              <p style={{ color: 'var(--muted)', margin: '8px 0 0' }}>هیچ دسترسی‌ای انتخاب نشده است.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                {summaryItems.map(label => (
                  <span key={label} style={{
                    fontSize: 11, padding: '4px 10px', borderRadius: 8,
                    background: '#7667f733', color: '#cfc8ff', border: '1px solid var(--line)',
                  }}>{label}</span>
                ))}
              </div>
            )}
          </div>

          <label style={lab}>
            پیام (اختیاری)
            <input value={message} onChange={e => setMessage(e.target.value)} placeholder="توضیح برای گیرنده..." style={inp} />
          </label>
          <button className="primary" type="submit" style={{ width: 'fit-content' }}><Share2 size={16} /> ثبت اشتراک</button>
        </form>
      </section>

      <div className="files-toolbar" style={{ marginBottom: 12 }}>
        <div className="view-switch">
          <button className={direction === 'received' ? 'active' : ''} onClick={() => setDirection('received')}>دریافتی من</button>
          <button className={direction === 'sent' ? 'active' : ''} onClick={() => setDirection('sent')}>اشتراک‌های ارسالی</button>
        </div>
      </div>

      {loading ? (
        <div className="panel empty"><h2>در حال بارگذاری...</h2></div>
      ) : shares.length === 0 ? (
        <div className="panel empty"><Share2 size={28} /><h2>موردی نیست</h2><p>هنوز اشتراکی ثبت نشده است.</p></div>
      ) : (
        <section className="panel">
          {shares.map(s => {
            const caps = {
              view: s.can_view !== false && (s.capabilities?.view !== false),
              download: !!(s.capabilities?.download ?? s.can_download),
              copy: !!(s.capabilities?.copy ?? s.can_download),
              edit: !!(s.capabilities?.edit ?? s.can_edit),
              reshare: !!(s.capabilities?.reshare ?? s.can_reshare),
            };
            const labels = activeCapLabels(caps);
            return (
              <div className="file-row" key={s.id} style={{ alignItems: 'flex-start', paddingTop: 14, paddingBottom: 14 }}>
                <span className="file-glyph" style={{ color: s.file_color, background: `${s.file_color}18` }}><Share2 size={18} /></span>
                <div className="file-info" style={{ gap: 6 }}>
                  <b>{s.file_name}</b>
                  <small>
                    {direction === 'received' ? `از ${s.shared_by_username}` : `به ${s.shared_with_username}`}
                    {' · '}{s.file_size}
                  </small>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {labels.length ? labels.map(label => (
                      <span key={label} style={{
                        fontSize: 10, padding: '3px 8px', borderRadius: 8,
                        background: '#7667f722', color: '#b9b2ff', border: '1px solid var(--line)',
                      }}>{label}</span>
                    )) : (
                      <span style={{ fontSize: 10, color: 'var(--muted)' }}>بدون دسترسی فعال</span>
                    )}
                  </div>
                  {direction === 'received' && labels.length > 0 && (
                    <small style={{ color: 'var(--muted)' }}>
                      دسترسی شما: {labels.join(' · ')}
                    </small>
                  )}
                </div>
                <button className="more" aria-label="حذف اشتراک" onClick={() => deleteShare(s.id).then(refresh).catch(e => setError(e.message))}>
                  <Trash2 size={16} />
                </button>
              </div>
            );
          })}
        </section>
      )}
    </>
  );
}

const lab: CSSProperties = { display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' };
const inp: CSSProperties = { padding: 10, borderRadius: 10, background: '#ffffff08', border: '1px solid var(--line)', color: '#fff' };

export function MailPage() {
  const [box, setBox] = useState<'inbox' | 'sent'>('inbox');
  const [mails, setMails] = useState<MailItem[]>([]);
  const [users, setUsers] = useState<UserLookup[]>([]);
  const [selected, setSelected] = useState<MailItem | null>(null);
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [priority, setPriority] = useState('normal');
  const [error, setError] = useState('');
  const [showCompose, setShowCompose] = useState(false);
  const [mailTone, setMailTone] = useState<'formal' | 'friendly' | 'short'>('formal');

  function refresh() {
    listMail(box).then(setMails).catch(e => setError(e.message));
    lookupUsers().then(setUsers).catch(() => {});
  }

  useEffect(() => { refresh(); setSelected(null); }, [box]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!recipient || !subject || !body) return setError('همه فیلدها الزامی است');
    try {
      await sendMail(Number(recipient), subject, body, priority);
      setSubject(''); setBody(''); setShowCompose(false); setBox('sent'); refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ارسال ناموفق');
    }
  }

  async function openMail(id: number) {
    try {
      const m = await getMail(id);
      setSelected(m);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا');
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">اتوماسیون اداری</span>
          <h1>مکاتبات</h1>
          <p>صندوق ورودی، ارسال نامه و پیگیری مکاتبات سازمانی.</p>
        </div>
        <button className="primary" onClick={() => setShowCompose(v => !v)}><Send size={16} /> نامه جدید</button>
      </div>
      {error && <div className="form-error" role="alert">{error}</div>}

      {showCompose && (
        <section className="panel" style={{ marginBottom: 18 }}>
          <form onSubmit={handleSend} style={{ display: 'grid', gap: 12 }}>
            <label style={{ display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' }}>
              گیرنده
              <select value={recipient} onChange={e => setRecipient(e.target.value)} required style={{ padding: 10, borderRadius: 10, background: '#ffffff08', border: '1px solid var(--line)', color: '#fff' }}>
                <option value="">انتخاب...</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.first_name || u.username} ({u.username})</option>)}
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' }}>
              موضوع
              <input value={subject} onChange={e => setSubject(e.target.value)} required style={{ padding: 10, borderRadius: 10, background: '#ffffff08', border: '1px solid var(--line)', color: '#fff' }} />
            </label>
            <label style={{ display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' }}>
              اولویت
              <select value={priority} onChange={e => setPriority(e.target.value)} style={{ padding: 10, borderRadius: 10, background: '#ffffff08', border: '1px solid var(--line)', color: '#fff' }}>
                <option value="low">کم</option>
                <option value="normal">عادی</option>
                <option value="high">فوری</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6, fontSize: 11, color: 'var(--muted)' }}>
              متن نامه
              <SpellCheckEditor value={body} onChange={setBody} rows={6} required placeholder="متن نامه را بنویسید…" />
            </label>
            <AIAssist
              title="پیش‌نویس نامه با AI"
              description="از موضوع و نکات داخل متن، نامه اداری می‌سازد. لحن را انتخاب کنید."
              buttonLabel="نوشتن پیش‌نویس"
              tones={[
                { id: 'formal', label: 'رسمی اداری' },
                { id: 'friendly', label: 'مودب نیمه‌رسمی' },
                { id: 'short', label: 'کوتاه' },
              ]}
              tone={mailTone}
              onToneChange={v => setMailTone(v as 'formal' | 'friendly' | 'short')}
              onRun={async () => {
                const notes = body.trim() || 'لطفاً یک نامه اداری مناسب بنویس';
                const recipientLabel = users.find(u => String(u.id) === String(recipient));
                const res = await draftMail(
                  subject || 'مکاتبه سازمانی',
                  notes,
                  mailTone,
                  recipientLabel ? (recipientLabel.first_name || recipientLabel.username) : ''
                );
                return {
                  text: res.text || '',
                  tokens_used: res.tokens_used,
                  remaining_tokens: res.remaining_tokens,
                  model: res.model,
                  provider: res.provider,
                };
              }}
              onApply={(text) => setBody(text)}
            />
            <AIAssist
              title="خلاصه متن نامه"
              description="متن فعلی را به چند نکته کلیدی فشرده می‌کند."
              buttonLabel="خلاصه کن"
              disabled={!body.trim()}
              onRun={async () => {
                const res = await summarizeText(body, 'general');
                return {
                  text: res.text || '',
                  tokens_used: res.tokens_used,
                  remaining_tokens: res.remaining_tokens,
                  model: res.model,
                  provider: res.provider,
                };
              }}
              onApply={(text) => setBody(text)}
            />
            <button className="primary" type="submit" style={{ width: 'fit-content' }}>ارسال نامه</button>
          </form>
        </section>
      )}

      <div className="files-toolbar" style={{ marginBottom: 12 }}>
        <div className="view-switch">
          <button className={box === 'inbox' ? 'active' : ''} onClick={() => setBox('inbox')}>صندوق ورودی</button>
          <button className={box === 'sent' ? 'active' : ''} onClick={() => setBox('sent')}>ارسال‌شده</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1fr' : '1fr', gap: 16 }}>
        <section className="panel">
          {mails.length === 0 ? <p style={{ color: 'var(--muted)', fontSize: 12 }}>نامه‌ای نیست.</p> : mails.map(m => (
            <div className="file-row" key={m.id} style={{ cursor: 'pointer', opacity: m.is_read || box === 'sent' ? 1 : 1, fontWeight: !m.is_read && box === 'inbox' ? 700 : 400 }} onClick={() => openMail(m.id)}>
              <span className="file-glyph" style={{ color: m.priority === 'high' ? '#f4af46' : '#7667f7', background: m.priority === 'high' ? '#f4af4622' : '#7667f718' }}><Mail size={18} /></span>
              <div className="file-info">
                <b>{m.subject}</b>
                <small>{box === 'inbox' ? m.sender_name : m.recipient_name} · {m.priority_label} · {new Date(m.created_at).toLocaleString('fa-IR')}</small>
              </div>
              {!m.is_read && box === 'inbox' && <span style={{ color: '#9e95ff', fontSize: 10 }}>جدید</span>}
            </div>
          ))}
        </section>
        {selected && (
          <section className="panel">
            <h2 style={{ margin: '0 0 8px', fontSize: 15 }}>{selected.subject}</h2>
            <p style={{ color: 'var(--muted)', fontSize: 11, margin: '0 0 14px' }}>
              از {selected.sender_name} به {selected.recipient_name} · {selected.priority_label} · {new Date(selected.created_at).toLocaleString('fa-IR')}
            </p>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>{selected.body}</div>
          </section>
        )}
      </div>
    </>
  );
}

export function ActivityPage() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    listActivity().then(setItems).catch(e => setError(e instanceof Error ? e.message : 'خطا'));
  }, []);

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">ممیزی و ردیابی</span>
          <h1>گزارش فعالیت</h1>
          <p>رویدادهای فضای کاری: آپلود، اشتراک، مکاتبات، پشتیبانی و ورود.</p>
        </div>
      </div>
      {error && <div className="form-error">{error}</div>}
      <section className="panel">
        {items.length === 0 ? (
          <div className="empty"><Activity size={28} /><h2>هنوز رویدادی ثبت نشده</h2><p>با آپلود فایل یا ارسال نامه، فعالیت‌ها اینجا ظاهر می‌شوند.</p></div>
        ) : items.map(item => (
          <div className="file-row" key={item.id}>
            <span className="file-glyph" style={{ color: '#9e95ff', background: '#7667f718' }}><Activity size={18} /></span>
            <div className="file-info">
              <b>{item.title}</b>
              <small>{item.action_label} · {item.username} · {new Date(item.created_at).toLocaleString('fa-IR')}{item.detail ? ` · ${item.detail}` : ''}</small>
            </div>
          </div>
        ))}
      </section>
    </>
  );
}

export function NotFoundPage() {
  return <div className="panel empty"><h1>صفحه پیدا نشد</h1><p>مسیر درخواست‌شده وجود ندارد.</p></div>;
}
