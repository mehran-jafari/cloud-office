import { Monitor, Moon, Smartphone, Sun } from 'lucide-react';
import { useTheme } from '../theme/ThemeProvider';

export function ThemeSwitcher({ compact = false }: { compact?: boolean }) {
  const { mode, ui, setMode, setUi } = useTheme();

  return (
    <div className="theme-switcher" role="group" aria-label="تم و سبک رابط">
      <button type="button" className={mode === 'light' ? 'active' : ''} onClick={() => setMode('light')} title="تم سفید">
        <Sun size={14} />
        {!compact && 'روشن'}
      </button>
      <button type="button" className={mode === 'dark' ? 'active' : ''} onClick={() => setMode('dark')} title="تم مشکی">
        <Moon size={14} />
        {!compact && 'تیره'}
      </button>
      <button type="button" className={ui === 'windows' ? 'active' : ''} onClick={() => setUi('windows')} title="سبک ویندوز">
        <Monitor size={14} />
        {!compact && 'ویندوز'}
      </button>
      <button type="button" className={ui === 'ios' ? 'active' : ''} onClick={() => setUi('ios')} title="سبک iOS">
        <Smartphone size={14} />
        {!compact && 'iOS'}
      </button>
    </div>
  );
}
