import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link2, Copy, X, Trash2, RefreshCw } from 'lucide-react';
import {
  createPublicLink,
  listPublicLinks,
  revokePublicLink,
  type PublicShareLink,
} from '../api/files';

type Props = {
  fileId: number;
  fileName: string;
  onClose: () => void;
  onToast?: (kind: 'success' | 'error', title: string, body?: string) => void;
};

export function PublicShareModal({ fileId, fileName, onClose, onToast }: Props) {
  const [permission, setPermission] = useState<'view' | 'download'>('download');
  const [password, setPassword] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [maxDownloads, setMaxDownloads] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [link, setLink] = useState<PublicShareLink | null>(null);
  const [existing, setExisting] = useState<PublicShareLink[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [copied, setCopied] = useState(false);

  const loadLinks = useCallback(async () => {
    setLoadingList(true);
    try {
      const rows = await listPublicLinks(fileId);
      setExisting(rows.filter(r => r.is_active && !r.is_expired));
    } catch {
      /* ignore list errors in modal */
    } finally {
      setLoadingList(false);
    }
  }, [fileId]);

  useEffect(() => {
    void loadLinks();
  }, [loadLinks]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const created = await createPublicLink({
        file: fileId,
        permission,
        password: password || undefined,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        max_downloads: maxDownloads ? Number(maxDownloads) : null,
        note: note || undefined,
      });
      setLink(created);
      onToast?.('success', 'لینک عمومی ساخته شد', fileName);
      await loadLinks();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'ساخت لینک ناموفق بود';
      setError(msg);
      onToast?.('error', 'خطا در ساخت لینک', msg);
    } finally {
      setLoading(false);
    }
  }

  async function copyUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      onToast?.('success', 'لینک کپی شد');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('کپی در کلیپ‌بورد پشتیبانی نشد');
    }
  }

  async function revoke(id: number) {
    if (!confirm('این لینک لغو شود؟')) return;
    try {
      await revokePublicLink(id);
      if (link?.id === id) setLink(null);
      onToast?.('success', 'لینک لغو شد');
      await loadLinks();
    } catch (err) {
      onToast?.('error', 'لغو لینک ناموفق بود', err instanceof Error ? err.message : undefined);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal glass" onClick={e => e.stopPropagation()} style={{ maxWidth: 480, width: '94%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0, fontSize: 18, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Link2 size={18} /> لینک عمومی
          </h2>
          <button type="button" className="btn ghost" onClick={onClose} aria-label="بستن">
            <X size={18} />
          </button>
        </div>
        <p className="muted" style={{ marginTop: 0 }}>فایل: <strong>{fileName}</strong></p>

        {/* Existing links */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 14 }}>لینک‌های فعال</h3>
            <button type="button" className="btn ghost" onClick={() => void loadLinks()} disabled={loadingList}>
              <RefreshCw size={14} />
            </button>
          </div>
          {loadingList ? (
            <p className="muted" style={{ fontSize: 13 }}>در حال بارگذاری…</p>
          ) : existing.length === 0 ? (
            <p className="muted" style={{ fontSize: 13 }}>هنوز لینک فعالی برای این فایل نیست.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {existing.map(row => (
                <li
                  key={row.id}
                  className="glass"
                  style={{ padding: '10px 12px', borderRadius: 12, fontSize: 13 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ wordBreak: 'break-all', fontFamily: 'monospace', fontSize: 12 }}>
                        {row.public_url}
                      </div>
                      <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>
                        {row.permission === 'download' ? 'دانلود' : 'مشاهده'}
                        {row.has_password ? ' · با رمز' : ''}
                        {row.expires_at ? ` · تا ${new Date(row.expires_at).toLocaleDateString('fa-IR')}` : ''}
                        {row.max_downloads != null ? ` · ${row.download_count}/${row.max_downloads}` : ''}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button type="button" className="btn ghost" title="کپی" onClick={() => void copyUrl(row.public_url)}>
                        <Copy size={14} />
                      </button>
                      <button type="button" className="btn ghost" title="لغو" onClick={() => void revoke(row.id)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <hr style={{ border: 0, borderTop: '1px solid rgba(0,0,0,0.08)', margin: '12px 0' }} />

        {link ? (
          <div>
            <label>لینک جدید</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input readOnly value={link.public_url} style={{ flex: 1 }} />
              <button type="button" className="btn primary" onClick={() => void copyUrl(link.public_url)}>
                <Copy size={16} /> {copied ? 'کپی شد' : 'کپی'}
              </button>
            </div>
            <button type="button" className="btn" style={{ marginTop: 12 }} onClick={onClose}>
              بستن
            </button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <h3 style={{ margin: '0 0 8px', fontSize: 14 }}>ساخت لینک جدید</h3>
            {error && <div className="form-error" role="alert">{error}</div>}
            <label>
              سطح دسترسی
              <select value={permission} onChange={e => setPermission(e.target.value as 'view' | 'download')}>
                <option value="view">فقط مشاهده</option>
                <option value="download">مشاهده + دانلود</option>
              </select>
            </label>
            <label>
              رمز عبور (اختیاری)
              <input type="text" value={password} onChange={e => setPassword(e.target.value)} placeholder="خالی = بدون رمز" />
            </label>
            <label>
              تاریخ انقضا (اختیاری)
              <input type="datetime-local" value={expiresAt} onChange={e => setExpiresAt(e.target.value)} />
            </label>
            <label>
              حداکثر تعداد دانلود (اختیاری)
              <input type="number" min={1} value={maxDownloads} onChange={e => setMaxDownloads(e.target.value)} placeholder="نامحدود" />
            </label>
            <label>
              یادداشت
              <input type="text" value={note} onChange={e => setNote(e.target.value)} maxLength={200} />
            </label>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button type="submit" className="btn primary" disabled={loading}>
                {loading ? 'در حال ساخت…' : 'ساخت لینک'}
              </button>
              <button type="button" className="btn ghost" onClick={onClose}>
                انصراف
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
