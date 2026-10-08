import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type ColorMode = 'dark' | 'light';
export type UiStyle = 'ios' | 'windows';

type ThemeCtx = {
  mode: ColorMode;
  ui: UiStyle;
  setMode: (m: ColorMode) => void;
  setUi: (u: UiStyle) => void;
  toggleMode: () => void;
};

const Ctx = createContext<ThemeCtx | null>(null);

const MODE_KEY = 'cloud-office-theme';
const UI_KEY = 'cloud-office-ui';

function readMode(): ColorMode {
  const v = localStorage.getItem(MODE_KEY);
  if (v === 'light' || v === 'dark') return v;
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function readUi(): UiStyle {
  const v = localStorage.getItem(UI_KEY);
  if (v === 'ios' || v === 'windows') return v;
  const ua = navigator.userAgent || '';
  if (/Mac|iPhone|iPad|iPod/i.test(ua)) return 'ios';
  return 'windows';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ColorMode>(() => (typeof window === 'undefined' ? 'dark' : readMode()));
  const [ui, setUiState] = useState<UiStyle>(() => (typeof window === 'undefined' ? 'windows' : readUi()));

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
    document.documentElement.setAttribute('data-ui', ui);
    localStorage.setItem(MODE_KEY, mode);
    localStorage.setItem(UI_KEY, ui);
  }, [mode, ui]);

  const value = useMemo<ThemeCtx>(
    () => ({
      mode,
      ui,
      setMode: setModeState,
      setUi: setUiState,
      toggleMode: () => setModeState(m => (m === 'dark' ? 'light' : 'dark')),
    }),
    [mode, ui]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
