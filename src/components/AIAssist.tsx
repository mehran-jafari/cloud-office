import { Check, Copy, Sparkles, X } from 'lucide-react';
import { useState } from 'react';

export type AIAssistResult = {
  text: string;
  tokens_used?: number;
  remaining_tokens?: number;
  model?: string;
  provider?: string;
};

type Props = {
  title?: string;
  description?: string;
  buttonLabel?: string;
  onRun: () => Promise<AIAssistResult | string>;
  onApply?: (text: string) => void;
  disabled?: boolean;
  /** گزینه‌های لحن برای نامه */
  tones?: Array<{ id: string; label: string }>;
  tone?: string;
  onToneChange?: (tone: string) => void;
};

export function AIAssist({
  title = 'دستیار هوشمند',
  description,
  onRun,
  onApply,
  buttonLabel = 'تولید با AI',
  disabled,
  tones,
  tone,
  onToneChange,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState('');
  const [meta, setMeta] = useState('');
  const [copied, setCopied] = useState(false);

  async function run() {
    setLoading(true);
    setError('');
    setCopied(false);
    try {
      const out = await onRun();
      if (typeof out === 'string') {
        setResult(out);
        setMeta('');
      } else {
        setResult(out.text || '');
        const parts = [
          out.provider === 'local' ? 'موتور محلی' : 'API',
          out.model ? `مدل: ${out.model}` : '',
          out.tokens_used != null ? `توکن: ${out.tokens_used}` : '',
          out.remaining_tokens != null ? `باقی‌مانده: ${out.remaining_tokens}` : '',
        ].filter(Boolean);
        setMeta(parts.join(' · '));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'خطای هوش مصنوعی');
    } finally {
      setLoading(false);
    }
  }

  async function copyText() {
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }

  return (
    <div
      style={{
        marginTop: 12,
        padding: 14,
        borderRadius: 14,
        background: 'linear-gradient(135deg, #7667f714, #35b9820d)',
        border: '1px solid #7667f744',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ display: 'grid', gap: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <span
              style={{
                width: 28,
                height: 28,
                borderRadius: 9,
                background: '#7667f733',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <Sparkles size={15} color="#cfc8ff" />
            </span>
            <b>{title}</b>
          </div>
          {description && <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)', paddingRight: 36 }}>{description}</p>}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {tones && tones.length > 0 && onToneChange && (
            <select
              value={tone}
              onChange={e => onToneChange(e.target.value)}
              style={{
                padding: '7px 10px',
                borderRadius: 10,
                background: '#ffffff0c',
                border: '1px solid var(--line)',
                color: '#e9edf7',
                fontSize: 12,
              }}
            >
              {tones.map(t => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          )}
          <button className="primary small-button" type="button" disabled={loading || disabled} onClick={run}>
            {loading ? 'در حال تولید...' : buttonLabel}
          </button>
        </div>
      </div>

      {error && (
        <p style={{ color: '#ffaaa9', fontSize: 12, margin: '10px 0 0' }} role="alert">
          {error}
        </p>
      )}

      {result && (
        <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
          <textarea
            value={result}
            onChange={e => setResult(e.target.value)}
            rows={7}
            style={{
              width: '100%',
              padding: 12,
              borderRadius: 12,
              background: '#0d1220',
              border: '1px solid var(--line)',
              color: '#e9edf7',
              resize: 'vertical',
              lineHeight: 1.7,
              fontSize: 13,
            }}
          />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {onApply && (
              <button className="primary" type="button" onClick={() => onApply(result)}>
                <Check size={15} /> اعمال در فیلد
              </button>
            )}
            <button type="button" className="edit-file" onClick={copyText}>
              {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'کپی شد' : 'کپی'}
            </button>
            <button type="button" className="edit-file" onClick={() => setResult('')}>
              <X size={14} /> بستن
            </button>
            {meta && <small style={{ color: 'var(--muted)', marginRight: 'auto' }}>{meta}</small>}
          </div>
        </div>
      )}

      <p style={{ margin: '10px 0 0', fontSize: 10, color: 'var(--muted)' }}>
        خروجی پیشنهادی است؛ قبل از ارسال از نظر حقوقی و محتوایی بررسی کنید.
      </p>
    </div>
  );
}
