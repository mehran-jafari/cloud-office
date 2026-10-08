import { Download, MonitorSmartphone, Shield, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'desk_agent_prompt';
const INSTALLED_KEY = 'desk_agent_installed';

type Platform = 'windows' | 'macos' | 'linux' | 'other';

function detectPlatform(): Platform {
  const ua = navigator.userAgent || '';
  if (/Windows/i.test(ua)) return 'windows';
  if (/Mac OS|Macintosh/i.test(ua)) return 'macos';
  if (/Linux/i.test(ua) && !/Android/i.test(ua)) return 'linux';
  return 'other';
}

type Installer = { label: string; href: string; hint: string; steps: string };

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

/** آدرس مطلق اسکریپت نصب؛ آدرس سرور داخل اسکریپت قرار می‌گیرد (نه localhost). */
function agentUrl(target: 'windows' | 'macos' | 'linux') {
  const origin = window.location.origin;
  const base = /^https?:/i.test(API_BASE) ? API_BASE : `${origin}${API_BASE}`;
  return `${base.replace(/\/$/, '')}/desk/agent/${target}/?app=${encodeURIComponent(origin)}`;
}

function buildInstallers(): Record<Platform, Installer[]> {
  const win: Installer = {
    label: 'دانلود فایل نصب ویندوز (جایگزین)',
    href: agentUrl('windows'),
    hint: `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; iwr -useb '${agentUrl('windows')}' | iex"`,
    steps: 'PowerShell را باز کنید (کلید Win+X ← Terminal) و دستور زیر را اجرا کنید:',
  };
  const mac: Installer = {
    label: 'دانلود فایل نصب macOS (جایگزین)',
    href: agentUrl('macos'),
    hint: `curl -fsSL '${agentUrl('macos')}' | bash`,
    steps: 'Terminal را باز کنید (Spotlight ← Terminal) و دستور زیر را اجرا کنید:',
  };
  const lin: Installer = {
    label: 'دانلود فایل نصب Linux (جایگزین)',
    href: agentUrl('linux'),
    hint: `curl -fsSL '${agentUrl('linux')}' | bash`,
    steps: 'ترمینال را باز کنید و دستور زیر را اجرا کنید:',
  };
  return { windows: [win], macos: [mac], linux: [lin], other: [win, mac, lin] };
}

type Props = {
  /** اگر از query ?agent=1 آمده باشد نصب‌شده فرض می‌شود */
  forceInstalled?: boolean;
};

export function DeskAgentInstall({ forceInstalled }: Props) {
  const platform = useMemo(() => detectPlatform(), []);
  const [open, setOpen] = useState(false);
  const [dontShow, setDontShow] = useState(false);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    if (forceInstalled) {
      localStorage.setItem(INSTALLED_KEY, '1');
      return;
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get('agent') === '1') {
      localStorage.setItem(INSTALLED_KEY, '1');
      return;
    }
    if (localStorage.getItem(INSTALLED_KEY) === '1') return;
    if (localStorage.getItem(STORAGE_KEY) === 'dismissed') return;
    // کمی تأخیر تا صفحه لود شود
    const t = window.setTimeout(() => setOpen(true), 400);
    return () => window.clearTimeout(t);
  }, [forceInstalled]);

  function dismiss(permanent: boolean) {
    if (permanent || dontShow) localStorage.setItem(STORAGE_KEY, 'dismissed');
    setOpen(false);
  }

  async function copyText(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // مرورگرهای بدون clipboard API (یا HTTP): روش قدیمی
      const area = document.createElement('textarea');
      area.value = text;
      document.body.appendChild(area);
      area.select();
      try { document.execCommand('copy'); } finally { document.body.removeChild(area); }
    }
    setCopied(key);
    window.setTimeout(() => setCopied(''), 2000);
  }

  function markInstalled() {
    localStorage.setItem(INSTALLED_KEY, '1');
    setOpen(false);
  }

  if (!open) {
    // نوار کوچک همیشگی اگر نصب نشده
    if (localStorage.getItem(INSTALLED_KEY) === '1') return null;
    return (
      <button
        type="button"
        className="edit-file"
        style={{ marginBottom: 12 }}
        onClick={() => setOpen(true)}
      >
        <Download size={14} /> نصب عامل Desk
      </button>
    );
  }

  const list = buildInstallers()[platform];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.55)',
        display: 'grid',
        placeItems: 'center',
        padding: 16,
      }}
      role="dialog"
      aria-modal
      aria-labelledby="desk-agent-title"
    >
      <div className="panel" style={{ width: 'min(480px, 100%)', position: 'relative' }}>
        <button
          type="button"
          className="more"
          style={{ position: 'absolute', top: 10, left: 10 }}
          onClick={() => dismiss(false)}
          aria-label="بستن"
        >
          <X size={18} />
        </button>

        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12 }}>
          <span
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'var(--accent-soft)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--accent)',
            }}
          >
            <MonitorSmartphone size={22} />
          </span>
          <div>
            <h2 id="desk-agent-title" style={{ margin: 0, fontSize: 18 }}>
              نصب عامل اتصال امن لازم است
            </h2>
            <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--muted)' }}>
              برای ریموت شبیه AnyDesk، عامل Desk را روی این سیستم نصب کنید تا شناسه ۹ رقمی پایدار داشته باشید و صفحه ریموت به‌صورت خودکار آماده شود.
            </p>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
            fontSize: 12,
            color: 'var(--muted)',
            marginBottom: 14,
            padding: 10,
            borderRadius: 12,
            background: 'var(--fill-quaternary)',
          }}
        >
          <Shield size={16} color="var(--success)" />
          اتصال WebRTC رمزنگاری‌شده · بدون نصب، فقط حالت مرورگر محدود فعال است
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          {list.map(item => (
            <a
              key={item.href}
              href={item.href}
              download
              className="primary"
              style={{ textDecoration: 'none', textAlign: 'center' }}
              onClick={() => {
                // بعد از دانلود، کاربر می‌تواند «نصب کردم» بزند
              }}
            >
              <Download size={16} style={{ verticalAlign: 'middle', marginLeft: 6 }} />
              {item.label}
            </a>
          ))}
        </div>

        <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 12 }}>
          سیستم شناسایی‌شده:{' '}
          <b style={{ color: 'var(--text)' }}>
            {platform === 'windows' ? 'ویندوز' : platform === 'macos' ? 'macOS' : platform === 'linux' ? 'Linux' : 'سایر'}
          </b>
          {list[0] ? ` — ${list[0].steps}` : ''}
        </p>
        {list.map(item => (
          <div key={`hint-${item.href}`} style={{ marginTop: 8 }}>
            <code
              style={{
                display: 'block',
                fontSize: 11,
                padding: 10,
                borderRadius: 10,
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                direction: 'ltr',
                textAlign: 'left',
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {item.hint}
            </code>
            <button
              type="button"
              className="edit-file"
              style={{ marginTop: 6 }}
              onClick={() => void copyText(item.hint, item.href)}
            >
              {copied === item.href ? 'کپی شد ✓' : 'کپی دستور نصب'}
            </button>
          </div>
        ))}

        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 14, fontSize: 12 }}>
          <input type="checkbox" checked={dontShow} onChange={e => setDontShow(e.target.checked)} />
          دیگر این پیام را نشان نده
        </label>

        <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
          <button type="button" className="primary" onClick={markInstalled}>
            نصب کردم — ادامه
          </button>
          <button type="button" className="edit-file" onClick={() => dismiss(true)}>
            فعلاً فقط مرورگر
          </button>
          <a href="/agent/README.txt" download className="edit-file" style={{ textDecoration: 'none' }}>
            راهنما
          </a>
        </div>
      </div>
    </div>
  );
}
