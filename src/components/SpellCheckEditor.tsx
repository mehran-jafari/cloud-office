import { useCallback, useEffect, useRef, useState } from 'react';
import { proofreadText, type ProofIssue } from '../api/ai';

type Props = {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
  required?: boolean;
};

/** ویرایشگر نامه با خط قرمز زیر غلط و پیشنهاد اصلاح */
export function SpellCheckEditor({ value, onChange, rows = 6, placeholder, required }: Props) {
  const [issues, setIssues] = useState<ProofIssue[]>([]);
  const [busy, setBusy] = useState(false);
  const [tip, setTip] = useState<{ x: number; y: number; issue: ProofIssue } | null>(null);
  const timer = useRef<number | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  const runCheck = useCallback(async (text: string) => {
    if (text.trim().length < 3) {
      setIssues([]);
      return;
    }
    setBusy(true);
    try {
      const res = await proofreadText(text);
      setIssues(res.issues || []);
    } catch {
      // local-ish silent fail
      setIssues([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      void runCheck(value);
    }, 900);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [value, runCheck]);

  function applySuggestion(issue: ProofIssue) {
    const next = value.replace(issue.original, issue.suggestion);
    onChange(next);
    setIssues(prev => prev.filter(i => i.original !== issue.original));
    setTip(null);
  }

  function applyAll() {
    let next = value;
    for (const issue of issues) {
      // Keep the project compatible with the ES2020 TypeScript lib target.
      next = next.split(issue.original).join(issue.suggestion);
    }
    onChange(next);
    setIssues([]);
    setTip(null);
  }

  // لایه هایلایت: متن را با mark برای غلط‌ها می‌سازد
  function renderHighlights() {
    if (!value) return null;
    if (!issues.length) {
      return <span style={{ whiteSpace: 'pre-wrap' }}>{value}</span>;
    }
    // مرتب‌سازی بر اساس طول original نزولی تا تداخل کمتر شود
    const sorted = [...issues].sort((a, b) => b.original.length - a.original.length);
    type Part = { text: string; issue?: ProofIssue };
    let parts: Part[] = [{ text: value }];
    for (const issue of sorted) {
      const next: Part[] = [];
      for (const part of parts) {
        if (part.issue || !part.text.includes(issue.original)) {
          next.push(part);
          continue;
        }
        const chunks = part.text.split(issue.original);
        chunks.forEach((chunk, idx) => {
          if (chunk) next.push({ text: chunk });
          if (idx < chunks.length - 1) next.push({ text: issue.original, issue });
        });
      }
      parts = next;
    }
    return (
      <>
        {parts.map((p, i) =>
          p.issue ? (
            <mark
              key={i}
              className="spell-error"
              title={`${p.issue.suggestion} — ${p.issue.reason || ''}`}
              onClick={e => {
                e.preventDefault();
                e.stopPropagation();
                const rect = (e.target as HTMLElement).getBoundingClientRect();
                setTip({ x: rect.left, y: rect.bottom + 6, issue: p.issue! });
              }}
            >
              {p.text}
            </mark>
          ) : (
            <span key={i}>{p.text}</span>
          )
        )}
      </>
    );
  }

  return (
    <div className="spell-editor" ref={boxRef}>
      <div className="spell-editor-toolbar">
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>
          {busy ? 'در حال غلط‌یابی…' : issues.length ? `${issues.length} مورد پیشنهادی` : 'غلط‌یاب فعال'}
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" className="edit-file" disabled={busy || !value.trim()} onClick={() => runCheck(value)}>
            بررسی دوباره
          </button>
          {issues.length > 0 && (
            <button type="button" className="primary small-button" onClick={applyAll}>
              اعمال همه اصلاحات
            </button>
          )}
        </div>
      </div>
      <div className="spell-editor-stack">
        <div className="spell-editor-backdrop" aria-hidden>
          {renderHighlights()}
        </div>
        <textarea
          className="spell-editor-input"
          value={value}
          onChange={e => onChange(e.target.value)}
          rows={rows}
          required={required}
          placeholder={placeholder}
          spellCheck
          lang="fa"
          onBlur={() => void runCheck(value)}
        />
      </div>
      {tip && (
        <>
          <div className="ctx-backdrop" onClick={() => setTip(null)} />
          <div className="spell-tip" style={{ top: tip.y, left: Math.min(tip.x, window.innerWidth - 220) }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>{tip.issue.reason || 'پیشنهاد'}</div>
            <button type="button" className="primary small-button" onClick={() => applySuggestion(tip.issue)}>
              {tip.issue.suggestion}
            </button>
            <button type="button" className="edit-file" style={{ marginRight: 6 }} onClick={() => setTip(null)}>
              نادیده
            </button>
          </div>
        </>
      )}
    </div>
  );
}
