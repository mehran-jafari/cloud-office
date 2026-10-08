import { useCallback, useEffect, useState } from 'react';
import { Activity, Download, RefreshCw, Filter } from 'lucide-react';
import { fetchAudit, type AuditEntry } from '../api/files';
import { Toast, makeToast, type ToastMessage } from '../components/Toast';
import { csvCell } from '../utils/csv';

const ACTION_LABELS: Record<string, string> = {
  upload: 'آپلود',
  download: 'دانلود',
  share: 'اشتراک',
  edit: 'ویرایش',
  login: 'ورود',
  delete: 'حذف',
  mail_sent: 'ارسال نامه',
  mail_received: 'دریافت نامه',
  support: 'پشتیبانی',
  remote: 'اتصال امن',
  admin: 'مدیریتی',
  other: 'سایر',
};

const EXPORT_LIMIT = 5000;

export function AuditPage() {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [summary, setSummary] = useState<{ action: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [action, setAction] = useState('');
  const [q, setQ] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchAudit({
        action: action || undefined,
        q: q || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 200,
      });
      setRows(data.results || []);
      setSummary(data.summary || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'بارگذاری گزارش ناموفق بود');
    } finally {
      setLoading(false);
    }
  }, [action, q, dateFrom, dateTo]);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportCsv() {
    setExporting(true);
    try {
      // خروجی کامل بر اساس همان فیلترها (نه فقط ردیف‌های نمایش‌داده‌شده)
      const data = await fetchAudit({
        action: action || undefined,
        q: q || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: EXPORT_LIMIT,
      });
      const header = ['id', 'username', 'action', 'title', 'detail', 'created_at'];
      const lines = [header.join(',')];
      for (const r of data.results || []) {
        lines.push([r.id, r.username, r.action, r.title, r.detail, r.created_at].map(csvCell).join(','));
      }
      const blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setToast(makeToast('success', `خروجی CSV آماده شد (${(data.results || []).length} ردیف)`));
    } catch (e) {
      setToast(makeToast('error', e instanceof Error ? e.message : 'خروجی CSV ناموفق بود'));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="page audit-page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={22} /> گزارش Audit
          </h1>
          <p className="muted" style={{ margin: '6px 0 0' }}>
            فعالیت کاربران — فیلترپذیر و قابل خروجی CSV
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className="btn ghost" onClick={() => void load()} disabled={loading}>
            <RefreshCw size={16} /> بروزرسانی
          </button>
          <button type="button" className="btn primary" onClick={() => void exportCsv()} disabled={!rows.length || exporting}>
            <Download size={16} /> خروجی CSV
          </button>
        </div>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}

      <div className="glass" style={{ padding: 14, margin: '16px 0', borderRadius: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, fontWeight: 600, fontSize: 14 }}>
          <Filter size={16} /> فیلترها
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
          <label>
            جستجو
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="عنوان یا جزئیات" />
          </label>
          <label>
            نوع عملیات
            <select value={action} onChange={e => setAction(e.target.value)}>
              <option value="">همه</option>
              {Object.entries(ACTION_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            از تاریخ
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </label>
          <label>
            تا تاریخ
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </label>
        </div>
        <button type="button" className="btn primary" style={{ marginTop: 12 }} onClick={() => void load()}>
          اعمال فیلتر
        </button>
      </div>

      {summary.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {summary.map(s => (
            <span
              key={s.action}
              className="glass"
              style={{ padding: '6px 12px', borderRadius: 999, fontSize: 12 }}
            >
              {ACTION_LABELS[s.action] || s.action}: <b>{s.count}</b>
            </span>
          ))}
        </div>
      )}

      {loading ? (
        <p className="muted">در حال بارگذاری…</p>
      ) : (
        <div className="glass" style={{ padding: 12, borderRadius: 14, overflow: 'auto' }}>
          <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th>زمان</th>
                <th>کاربر</th>
                <th>عملیات</th>
                <th>عنوان</th>
                <th>جزئیات</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td className="muted" style={{ whiteSpace: 'nowrap' }}>
                    {r.created_at ? new Date(r.created_at).toLocaleString('fa-IR') : '—'}
                  </td>
                  <td>{r.username || r.user || '—'}</td>
                  <td>{ACTION_LABELS[r.action] || r.action}</td>
                  <td>{r.title}</td>
                  <td className="muted">{r.detail || '—'}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center' }} className="muted">
                    موردی یافت نشد
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
