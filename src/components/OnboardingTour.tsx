import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X, Sparkles } from 'lucide-react';

const STORAGE_KEY = 'cloud-office-tour-done-v1';

type Step = {
  id: string;
  title: string;
  body: string;
  route?: string;
  selector?: string; // optional highlight target
};

const STEPS: Step[] = [
  {
    id: 'welcome',
    title: 'به دفتر ابری خوش آمدید',
    body: 'این راهنمای کوتاه امکانات اصلی را نشان می‌دهد. هر وقت خواستید می‌توانید آن را ببندید.',
    route: '/',
  },
  {
    id: 'files',
    title: 'فایل‌های من',
    body: 'از اینجا فایل آپلود کنید، پوشه بسازید، با راست‌کلیک اشتراک‌گذاری یا لینک عمومی بسازید.',
    route: '/files',
  },
  {
    id: 'search',
    title: 'جستجوی پیشرفته',
    body: 'در صفحه فایل‌ها می‌توانید بر اساس نام، نوع، تاریخ و حجم جستجو کنید. جستجوی معنایی AI هم فعال است.',
    route: '/files',
  },
  {
    id: 'trash',
    title: 'سطل زباله',
    body: 'فایل‌های حذف‌شده اینجا می‌مانند تا بازیابی یا برای همیشه پاک شوند.',
    route: '/trash',
  },
  {
    id: 'support',
    title: 'پشتیبانی و اتصال امن',
    body: 'از منوی پشتیبانی تیکت بسازید و از «اتصال امن» برای دسترسی از راه دور استفاده کنید.',
    route: '/support',
  },
  {
    id: 'done',
    title: 'آماده کار هستید',
    body: 'از داشبورد شروع کنید. هر زمان خواستید این راهنما را از منوی کاربر دوباره اجرا کنید.',
    route: '/',
  },
];

type Props = {
  forceOpen?: boolean;
  onClose?: () => void;
};

export function OnboardingTour({ forceOpen = false, onClose }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (forceOpen) {
      setOpen(true);
      setIndex(0);
      return;
    }
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setOpen(true);
        setIndex(0);
      }
    } catch {
      /* ignore */
    }
  }, [forceOpen]);

  const step = STEPS[index];
  const progress = useMemo(() => ((index + 1) / STEPS.length) * 100, [index]);

  useEffect(() => {
    if (open && step?.route && location.pathname !== step.route) {
      navigate(step.route);
    }
  }, [open, step, navigate, location.pathname]);

  function finish() {
    try {
      localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      /* ignore */
    }
    setOpen(false);
    onClose?.();
  }

  function next() {
    if (index >= STEPS.length - 1) {
      finish();
      return;
    }
    setIndex(i => i + 1);
  }

  function prev() {
    setIndex(i => Math.max(0, i - 1));
  }

  if (!open || !step) return null;

  return (
    <>
      <div
        className="tour-backdrop"
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 90,
          background: 'rgba(15, 23, 42, 0.35)',
        }}
        onClick={finish}
      />
      <div
        className="tour-card glass"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-title"
        style={{
          position: 'fixed',
          bottom: 28,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 91,
          width: 'min(420px, 92vw)',
          padding: '18px 20px',
          borderRadius: 16,
          boxShadow: '0 16px 40px rgba(0,0,0,0.18)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <h2 id="tour-title" style={{ margin: 0, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} /> {step.title}
          </h2>
          <button type="button" className="btn ghost" onClick={finish} aria-label="بستن راهنما">
            <X size={16} />
          </button>
        </div>
        <p style={{ margin: '10px 0 14px', fontSize: 13, lineHeight: 1.7, color: 'var(--muted)' }}>
          {step.body}
        </p>
        <div
          style={{
            height: 4,
            borderRadius: 999,
            background: 'rgba(0,0,0,0.08)',
            overflow: 'hidden',
            marginBottom: 12,
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              background: 'var(--accent, #3489f5)',
              transition: 'width 0.25s ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="muted" style={{ fontSize: 12 }}>
            {index + 1} از {STEPS.length}
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn ghost" disabled={index === 0} onClick={prev}>
              <ChevronRight size={16} /> قبلی
            </button>
            <button type="button" className="btn primary" onClick={next}>
              {index >= STEPS.length - 1 ? 'شروع کار' : 'بعدی'} <ChevronLeft size={16} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/** فراخوانی دستی از منوی کاربر */
export function resetOnboardingTour() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
