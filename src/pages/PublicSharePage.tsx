import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Cloud, Download, Lock } from 'lucide-react';
import { accessPublicShare, publicShareDownloadUrl } from '../api/files';

export function PublicSharePage() {
  const { token = '' } = useParams();
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState<{
    file_name: string;
    size_bytes: number;
    can_download: boolean;
    permission: string;
  } | null>(null);

  async function unlock(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await accessPublicShare(token, password);
      setInfo({
        file_name: data.file_name,
        size_bytes: data.size_bytes,
        can_download: data.can_download,
        permission: data.permission,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دسترسی ممکن نیست');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card glass" onSubmit={unlock} style={{ maxWidth: 420 }}>
        <div className="brand-mark"><Cloud size={22} /></div>
        <h1>اشتراک عمومی</h1>
        <p>Cloud Office — دسترسی امن به فایل اشتراکی</p>
        {error && <div className="form-error" role="alert">{error}</div>}

        {!info ? (
          <>
            <label>
              رمز عبور (اگر لازم باشد)
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="در صورت نیاز"
                autoComplete="off"
              />
            </label>
            <button className="primary" disabled={loading || !token}>
              {loading ? 'در حال بررسی…' : 'ادامه'}
            </button>
          </>
        ) : (
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: 16, fontWeight: 600 }}>{info.file_name}</p>
            <p className="muted">سطح: {info.permission === 'download' ? 'دانلود' : 'مشاهده'}</p>
            {info.can_download ? (
              <a
                className="primary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 12, textDecoration: 'none', padding: '10px 18px', borderRadius: 10 }}
                href={publicShareDownloadUrl(token, password)}
              >
                <Download size={18} /> دانلود فایل
              </a>
            ) : (
              <p className="muted" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <Lock size={16} /> این لینک فقط برای مشاهده است
              </p>
            )}
          </div>
        )}
      </form>
    </main>
  );
}
