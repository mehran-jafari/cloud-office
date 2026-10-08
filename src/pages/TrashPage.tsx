import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, RefreshCw, Trash2, RotateCcw, AlertTriangle, Inbox } from 'lucide-react';
import {
  listTrash,
  purgeTrash,
  restoreTrash,
  formatBytes,
  type FolderItem,
} from '../api/files';
import type { FileItem } from '../types/api';
import { Toast, makeToast, type ToastMessage } from '../components/Toast';

export function TrashPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<number[]>([]);
  const [selectedFolders, setSelectedFolders] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const showToast = (kind: 'success' | 'error', title: string, body?: string) => {
    setToast(makeToast(kind, title, body));
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listTrash();
      setFiles(data.files || []);
      setFolders(data.folders || []);
      setSelectedFiles([]);
      setSelectedFolders([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'بارگذاری سطل زباله ناموفق بود');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleFile = (id: number) => {
    setSelectedFiles(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));
  };
  const toggleFolder = (id: number) => {
    setSelectedFolders(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));
  };

  const selectAll = () => {
    setSelectedFiles(files.map(f => f.id));
    setSelectedFolders(folders.map(f => f.id));
  };

  const restoreSelected = async () => {
    if (!selectedFiles.length && !selectedFolders.length) return;
    setBusy(true);
    try {
      const res = await restoreTrash(selectedFiles, selectedFolders);
      showToast(
        'success',
        'بازیابی انجام شد',
        `${res.restored_files} فایل و ${res.restored_folders} پوشه`
      );
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'بازیابی ناموفق بود';
      setError(msg);
      showToast('error', 'خطا در بازیابی', msg);
    } finally {
      setBusy(false);
    }
  };

  const purgeSelected = async () => {
    if (!selectedFiles.length && !selectedFolders.length) return;
    if (!confirm('حذف دائمی انجام شود؟ این عمل قابل بازگشت نیست.')) return;
    setBusy(true);
    try {
      const res = await purgeTrash({ file_ids: selectedFiles, folder_ids: selectedFolders });
      showToast('success', 'حذف دائمی انجام شد', `${res.purged_files} فایل و ${res.purged_folders} پوشه`);
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'حذف دائمی ناموفق بود';
      setError(msg);
      showToast('error', 'خطا در حذف دائمی', msg);
    } finally {
      setBusy(false);
    }
  };

  const emptyTrash = async () => {
    if (!files.length && !folders.length) return;
    if (!confirm('کل سطل زباله خالی شود؟ این عمل قابل بازگشت نیست.')) return;
    setBusy(true);
    try {
      const res = await purgeTrash({ empty_all: true });
      showToast('success', 'سطل زباله خالی شد', `${res.purged_files} فایل و ${res.purged_folders} پوشه`);
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'خالی کردن سطل ناموفق بود';
      setError(msg);
      showToast('error', 'خطا', msg);
    } finally {
      setBusy(false);
    }
  };

  const total = files.length + folders.length;

  return (
    <div className="page trash-page">
      <div
        className="page-header"
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}
      >
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
            <Trash2 size={22} /> سطل زباله
          </h1>
          <p className="muted" style={{ margin: '6px 0 0' }}>
            فایل‌ها و پوشه‌های حذف‌شده تا قبل از حذف دائمی اینجا هستند.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link to="/files" className="btn ghost" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <ArrowRight size={16} /> بازگشت به فایل‌ها
          </Link>
          <button type="button" className="btn ghost" onClick={() => void load()} disabled={loading || busy}>
            <RefreshCw size={16} /> بروزرسانی
          </button>
        </div>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}

      <div className="toolbar" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '16px 0' }}>
        <button type="button" className="btn" disabled={!total || busy} onClick={selectAll}>
          انتخاب همه ({total})
        </button>
        <button
          type="button"
          className="btn primary"
          disabled={busy || (!selectedFiles.length && !selectedFolders.length)}
          onClick={() => void restoreSelected()}
        >
          <RotateCcw size={16} /> بازیابی
        </button>
        <button
          type="button"
          className="btn danger"
          disabled={busy || (!selectedFiles.length && !selectedFolders.length)}
          onClick={() => void purgeSelected()}
        >
          <AlertTriangle size={16} /> حذف دائمی
        </button>
        <button type="button" className="btn danger" disabled={busy || !total} onClick={() => void emptyTrash()}>
          خالی کردن سطل
        </button>
      </div>

      {loading ? (
        <p className="muted">در حال بارگذاری…</p>
      ) : total === 0 ? (
        <div
          className="empty-state glass"
          style={{
            padding: '48px 24px',
            textAlign: 'center',
            borderRadius: 16,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'rgba(52, 137, 245, 0.1)',
              display: 'grid',
              placeItems: 'center',
            }}
          >
            <Inbox size={32} style={{ opacity: 0.55, color: 'var(--accent, #3489f5)' }} />
          </div>
          <h3 style={{ margin: 0 }}>سطل زباله خالی است</h3>
          <p className="muted" style={{ margin: 0, maxWidth: 320 }}>
            وقتی فایلی را حذف کنید اینجا نمایش داده می‌شود و می‌توانید آن را بازیابی کنید.
          </p>
          <Link to="/files" className="btn primary" style={{ marginTop: 8 }}>
            رفتن به فایل‌ها
          </Link>
        </div>
      ) : (
        <div className="glass" style={{ padding: 12, overflow: 'auto', borderRadius: 14 }}>
          <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ width: 40 }}></th>
                <th>نام</th>
                <th>نوع</th>
                <th>اندازه</th>
                <th>حذف‌شده</th>
              </tr>
            </thead>
            <tbody>
              {folders.map(f => (
                <tr key={`d-${f.id}`}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedFolders.includes(f.id)}
                      onChange={() => toggleFolder(f.id)}
                    />
                  </td>
                  <td>📁 {f.name}</td>
                  <td>پوشه</td>
                  <td>—</td>
                  <td className="muted">—</td>
                </tr>
              ))}
              {files.map(f => (
                <tr key={`f-${f.id}`}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedFiles.includes(f.id)}
                      onChange={() => toggleFile(f.id)}
                    />
                  </td>
                  <td>{f.name}</td>
                  <td>{f.type}</td>
                  <td>{f.size || formatBytes(0)}</td>
                  <td className="muted">{f.updated || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
