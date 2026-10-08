import type { ReactNode } from 'react';
import { FileText, HardDrive, Mail, Share2, Upload } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatBytes, listFiles, uploadFile } from '../api/files';
import { getDashboardStats } from '../api/workspace';
import { useAuth } from '../auth/AuthProvider';
import type { DashboardStats, FileItem } from '../types/api';

function Stat({ icon, label, value, tone }: { icon: ReactNode; label: string; value: string; tone: string }) {
  return (
    <div className="stat glass">
      <span className={`stat-icon ${tone}`}>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{percent:number;loaded:number;total:number;name:string}|null>(null);
  const [error, setError] = useState('');

  const name = user ? `${user.first_name || user.username}` : 'کاربر';

  function refresh() {
    listFiles().then(data => setFiles(data.results)).catch(() => {});
    getDashboardStats().then(setStats).catch(() => {});
  }

  useEffect(() => { refresh(); }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      await uploadFile(file, p => setUploadProgress({ name: file.name, ...p }));
      setUploadProgress(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'آپلود ناموفق بود');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">نمای کلی فضای کاری</span>
          <h1>صبح بخیر، {name}</h1>
          <p>فایل‌ها و ارتباطات سازمانی شما در یک نگاه.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input ref={inputRef} type="file" style={{ display: 'none' }} onChange={handleUpload} />
          <button className="primary" disabled={uploading} onClick={() => inputRef.current?.click()}>
            <Upload size={17} />
            {uploading ? 'در حال آپلود...' : 'آپلود فایل'}
          </button>
        </div>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}
      {uploadProgress && (
        <div className="panel" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
            <span>{uploadProgress.name}</span>
            <span>{uploadProgress.percent}% — {formatBytes(uploadProgress.loaded)} / {formatBytes(uploadProgress.total)}</span>
          </div>
          <div style={{ height: 10, borderRadius: 6, background: '#ffffff12', overflow: 'hidden' }}>
            <div style={{ width: `${uploadProgress.percent}%`, height: '100%', background: '#7667f7' }} />
          </div>
        </div>
      )}

      <div className="stats">
        <Stat icon={<HardDrive />} label="فضای استفاده‌شده" value={stats ? `${stats.used_gb} GB` : '—'} tone="purple" />
        <Stat icon={<FileText />} label="کل فایل‌ها" value={stats ? String(stats.files_count) : String(files.length || '—')} tone="blue" />
        <Stat icon={<Share2 />} label="اشتراک‌گذاری‌شده" value={stats ? String(stats.shared_count) : '—'} tone="green" />
        <Stat icon={<Mail />} label="مکاتبات خوانده‌نشده" value={stats ? String(stats.open_mails) : '—'} tone="orange" />
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>فایل‌های اخیر</h2>
            <p>آخرین فایل‌های فضای کاری</p>
          </div>
          <button className="edit-file" onClick={() => navigate('/files')}>مشاهده همه</button>
        </div>
        {files.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 12 }}>هنوز فایلی آپلود نشده. از دکمه بالا شروع کنید.</p>
        ) : (
          files.slice(0, 5).map(file => (
            <div className="file-row" key={file.id}>
              <span className="file-glyph" style={{ color: file.color, background: `${file.color}18` }}>
                <FileText size={20} />
              </span>
              <div className="file-info">
                <b>{file.name}</b>
                <small>{file.owner} · {file.updated}</small>
              </div>
              <span className="file-size">{file.size}</span>
            </div>
          ))
        )}
      </section>
    </>
  );
}
