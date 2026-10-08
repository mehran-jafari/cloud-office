import { ArrowRight, CloudOff, FilePenLine, LoaderCircle, RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getEditorConfig } from '../api/editor';
import type { OnlyOfficeEditorConfig } from '../types/api';

declare global { interface Window { DocsAPI?: { DocEditor: new (elementId: string, config: OnlyOfficeEditorConfig['config']) => { destroyEditor?: () => void } } } }

function loadOnlyOfficeScript(serverUrl: string) {
  const src = `${serverUrl.replace(/\/$/, '')}/web-apps/apps/api/documents/api.js`;
  const existing = document.querySelector<HTMLScriptElement>(`script[data-onlyoffice-src="${src}"]`);
  if (existing && window.DocsAPI) return Promise.resolve();
  if (existing) return new Promise<void>((resolve, reject) => { existing.addEventListener('load', () => resolve(), { once: true }); existing.addEventListener('error', () => reject(new Error('بارگذاری اسکریپت OnlyOffice ناموفق بود')), { once: true }); });
  return new Promise<void>((resolve, reject) => { const script = document.createElement('script'); script.src = src; script.async = true; script.dataset.onlyofficeSrc = src; script.onload = () => resolve(); script.onerror = () => reject(new Error('Document Server در دسترس نیست')); document.head.appendChild(script); });
}

export function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [config, setConfig] = useState<OnlyOfficeEditorConfig | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const editorRef = useRef<{ destroyEditor?: () => void } | null>(null);

  useEffect(() => { if (!id) return; let active = true; setLoading(true); setError(''); getEditorConfig(id).then(value => { if (active) setConfig(value); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'دریافت تنظیمات ویرایشگر ناموفق بود'); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; editorRef.current?.destroyEditor?.(); editorRef.current = null; }; }, [id]);

  useEffect(() => { if (!config || !window.document.getElementById('onlyoffice-editor')) return; let active = true; loadOnlyOfficeScript(config.documentServerUrl).then(() => { if (!active || !window.DocsAPI) return; editorRef.current = new window.DocsAPI.DocEditor('onlyoffice-editor', config.config); }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'راه‌اندازی ویرایشگر ناموفق بود'); }); return () => { active = false; editorRef.current?.destroyEditor?.(); editorRef.current = null; }; }, [config]);

  return <div className="editor-page"><div className="editor-toolbar"><button className="editor-back" onClick={() => navigate('/files')}><ArrowRight size={18}/> بازگشت به فایل‌ها</button><div className="editor-title"><FilePenLine size={18}/><strong>{config?.config.document.title ?? 'ویرایش آنلاین فایل'}</strong>{config?.config.editorConfig.mode === 'view' && <span className="editor-mode">فقط مشاهده</span>}</div><span className="editor-status"><span className="status-dot"/> ذخیره‌سازی توسط OnlyOffice</span></div>{loading ? <EditorState icon={<LoaderCircle className="spin"/>} title="در حال آماده‌سازی ویرایشگر..." description="تنظیمات امن فایل در حال دریافت است."/> : error ? <EditorState icon={<CloudOff/>} title="ویرایشگر در دسترس نیست" description={error} action={<button className="primary" onClick={() => window.location.reload()}><RefreshCw size={16}/> تلاش دوباره</button>}/> : <div id="onlyoffice-editor" className="onlyoffice-host" aria-label="ویرایشگر آنلاین OnlyOffice"/>}</div>;
}
function EditorState({ icon, title, description, action }: { icon: ReactNode; title: string; description: string; action?: ReactNode }) { return <div className="editor-state panel"><span className="empty-icon">{icon}</span><h2>{title}</h2><p>{description}</p>{action}</div>; }
