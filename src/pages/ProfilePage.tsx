import { HardDrive, Save, User } from 'lucide-react';
import { useEffect, useState, type CSSProperties } from 'react';
import { getProfile, updateProfile, type ProfileData } from '../api/admin';
import { getAccessToken } from '../api/client';
import { aiStatus } from '../api/ai';
import { useAuth } from '../auth/AuthProvider';

export function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [notifySms, setNotifySms] = useState(false);
  const [notifyTelegram, setNotifyTelegram] = useState(false);
  const [notifyBale, setNotifyBale] = useState(false);
  const [notifyEitaa, setNotifyEitaa] = useState(false);
  const [gender, setGender] = useState('male');
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [saving, setSaving] = useState(false);
  const [aiInfo, setAiInfo] = useState<{ remaining_tokens?: number; monthly_tokens?: number; used_tokens?: number; provider_configured?: boolean } | null>(null);

  useEffect(() => {
    aiStatus().then(setAiInfo).catch(() => {});
    getProfile()
      .then(p => {
        setProfile(p);
        setFirstName(p.first_name || '');
        setLastName(p.last_name || '');
        setEmail(p.email || '');
        setPhone((p as any).phone || '');
        setNotifySms(Boolean((p as any).notify_sms));
        setNotifyTelegram(Boolean((p as any).notify_telegram));
        setNotifyBale(Boolean((p as any).notify_bale));
        setNotifyEitaa(Boolean((p as any).notify_eitaa));
        setGender((p as any).gender || 'male');
        setAvatarUrl((p as any).avatar_url || null);
      })
      .catch(e => setError(e instanceof Error ? e.message : 'خطا در دریافت پروفایل'));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setOk('');
    try {
      const payload: Parameters<typeof updateProfile>[0] = {
        first_name: firstName,
        last_name: lastName,
        email,
      };
      if (password) payload.password = password;
      (payload as any).phone = phone;
      (payload as any).notify_sms = notifySms;
      (payload as any).notify_telegram = notifyTelegram;
      (payload as any).notify_bale = notifyBale;
      (payload as any).notify_eitaa = notifyEitaa;
      (payload as any).gender = gender;
      const updated = await updateProfile(payload);
      setProfile(updated);
      setPassword('');
      setOk('پروفایل ذخیره شد');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ذخیره ناموفق بود');
    } finally {
      setSaving(false);
    }
  }

  const usedGb = profile ? (profile.quota.used_bytes / 1024 ** 3).toFixed(2) : '—';
  const allocGb = profile ? (profile.quota.allocated_bytes / 1024 ** 3).toFixed(2) : '—';

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">حساب کاربری</span>
          <h1>پنل کاربر</h1>
          <p>اطلاعات شخصی، سهمیه فضا و تغییر رمز عبور.</p>
        </div>
      </div>

      
      <section className="panel" style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        {avatarUrl ? (
          <img src={avatarUrl} alt="" style={{ width: 72, height: 72, borderRadius: 18, objectFit: 'cover' }} />
        ) : (
          <div style={{ width: 72, height: 72, borderRadius: 18, background: gender === 'female' ? '#e879a8' : '#5b8def', display: 'grid', placeItems: 'center', fontSize: 28, color: '#fff' }}>
            {gender === 'female' ? '♀' : '♂'}
          </div>
        )}
        <div style={{ display: 'grid', gap: 8 }}>
          <label style={{ fontSize: 11, color: '#bfc9d8' }}>
            عکس پروفایل
            <input type="file" accept="image/*" disabled={uploadingAvatar} onChange={async e => {
              const f = e.target.files?.[0];
              if (!f) return;
              setUploadingAvatar(true);
              try {
                const fd = new FormData();
                fd.append('avatar', f);
                const headers: HeadersInit = {};
                const token = getAccessToken();
                if (token) headers['Authorization'] = `Bearer ${token}`;
                const API = import.meta.env.VITE_API_URL ?? '/api';
                const res = await fetch(`${API}/account/avatar/`, { method: 'POST', headers, body: fd, credentials: 'include' });
                if (!res.ok) throw new Error('آپلود عکس ناموفق');
                const data = await res.json();
                setAvatarUrl(data.avatar_url);
                setOk('عکس پروفایل ذخیره شد');
              } catch (err) {
                setError(err instanceof Error ? err.message : 'خطا');
              } finally {
                setUploadingAvatar(false);
              }
            }} />
          </label>
          <label style={{ fontSize: 11, color: '#bfc9d8', display: 'grid', gap: 4 }}>
            جنسیت (برای تصویر پیش‌فرض پشتیبان)
            <select value={gender} onChange={e => setGender(e.target.value)} style={{ padding: 8, borderRadius: 10, background: '#ffffff08', border: '1px solid var(--line)', color: '#fff' }}>
              <option value="male">مرد</option>
              <option value="female">زن</option>
              <option value="other">سایر</option>
            </select>
          </label>
        </div>
      </section>

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      {ok && (
        <div className="panel" style={{ marginBottom: 12, borderColor: '#3cc78b55', color: '#8fe4b6' }}>
          {ok}
        </div>
      )}

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>
                <User size={16} style={{ verticalAlign: 'middle', marginLeft: 6 }} />
                مشخصات
              </h2>
              <p>
                {profile?.role_label || user?.role || 'کاربر'} · @{profile?.username || user?.username}
              </p>
            </div>
          </div>
          <form onSubmit={handleSave} style={{ display: 'grid', gap: 12 }}>
            <label style={labelStyle}>
              نام
              <input value={firstName} onChange={e => setFirstName(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              نام خانوادگی
              <input value={lastName} onChange={e => setLastName(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              ایمیل
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} />
            </label>
            <label style={labelStyle}>
              موبایل (پیامک / پیام‌رسان)
              <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="09xxxxxxxxx" style={inputStyle} />
            </label>
            <div style={{ display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' }}>
              <span>کانال اطلاع‌رسانی</span>
              <label><input type="checkbox" checked={notifySms} onChange={e => setNotifySms(e.target.checked)} /> پیامک (سیم‌کارت)</label>
              <label><input type="checkbox" checked={notifyTelegram} onChange={e => setNotifyTelegram(e.target.checked)} /> تلگرام</label>
              <label><input type="checkbox" checked={notifyBale} onChange={e => setNotifyBale(e.target.checked)} /> بله</label>
              <label><input type="checkbox" checked={notifyEitaa} onChange={e => setNotifyEitaa(e.target.checked)} /> ایتا</label>
            </div>
            <label style={labelStyle}>
              رمز عبور جدید (اختیاری)
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="خالی = بدون تغییر" style={inputStyle} />
            </label>
            <button className="primary" type="submit" disabled={saving} style={{ width: 'fit-content' }}>
              <Save size={16} /> {saving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>
                <HardDrive size={16} style={{ verticalAlign: 'middle', marginLeft: 6 }} />
                سهمیه فضای ذخیره‌سازی
              </h2>
              <p>
                {usedGb} از {allocGb} گیگابایت استفاده شده
              </p>
            </div>
          </div>
          {profile && (
            <>
              <div style={{ height: 10, borderRadius: 6, background: '#ffffff12', overflow: 'hidden', marginBottom: 12 }}>
                <div
                  style={{
                    width: `${Math.min(100, profile.quota.percent_used)}%`,
                    height: '100%',
                    background: profile.quota.percent_used > 90 ? '#e05a5a' : '#7667f7',
                  }}
                />
              </div>
              <p style={{ color: 'var(--muted)', fontSize: 12, margin: 0 }}>
                {profile.quota.percent_used}% پر شده · باقی‌مانده: {(profile.quota.remaining_bytes / 1024 ** 3).toFixed(2)} GB
              </p>
              {profile.date_joined && (
                <p style={{ color: 'var(--muted)', fontSize: 11, marginTop: 16 }}>
                  تاریخ عضویت: {new Date(profile.date_joined).toLocaleDateString('fa-IR')}
                </p>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}

const labelStyle: CSSProperties = { display: 'grid', gap: 6, fontSize: 11, color: '#bfc9d8' };
const inputStyle: CSSProperties = {
  padding: 10,
  borderRadius: 10,
  background: '#ffffff08',
  border: '1px solid var(--line)',
  color: '#fff',
};
