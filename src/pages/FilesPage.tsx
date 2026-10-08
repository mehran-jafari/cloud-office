import { Download, Eye, FilePenLine, FileText, Folder, Grid2X2, List, Search, Upload, X, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { advancedSearch, bulkAction, convertFile, createFolder, downloadFile, fetchFileBlob, formatBytes, isEditableFile, isPdfFile, isWordFile, listFiles, listFolders, mediaKind, renameFile, uploadFile, uploadFileToFolder, type FolderItem } from '../api/files';
import { createShare, lookupUsers } from '../api/workspace';
import { PublicShareModal } from '../components/PublicShareModal';
import { Toast, makeToast, type ToastMessage } from '../components/Toast';
import { FileContextMenu, type ContextMenuState } from '../components/FileContextMenu';
import { createFileWithAI, indexFile, semanticSearch } from '../api/ai';
import type { FileItem } from '../types/api';

export function FilesPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ name: string; percent: number; loaded: number; total: number } | null>(null);
  const [error, setError] = useState('');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [semanticQ, setSemanticQ] = useState('');
  const [semanticHits, setSemanticHits] = useState<Array<{ file_id: number; name: string; score: number; preview: string }>>([]);
  const [aiBusy, setAiBusy] = useState(false);
  const [searchMode, setSearchMode] = useState<'name' | 'semantic' | 'advanced'>('name');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [advType, setAdvType] = useState('');
  const [advDateFrom, setAdvDateFrom] = useState('');
  const [advDateTo, setAdvDateTo] = useState('');
  const [advMinMb, setAdvMinMb] = useState('');
  const [advMaxMb, setAdvMaxMb] = useState('');
  const [advShared, setAdvShared] = useState(false);
  const [advBusy, setAdvBusy] = useState(false);
  const [showCreateAI, setShowCreateAI] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createPrompt, setCreatePrompt] = useState('');
  const [createType, setCreateType] = useState('txt');
  const [createPreview, setCreatePreview] = useState('');
  const [convertingId, setConvertingId] = useState<number | null>(null);
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [currentFolder, setCurrentFolder] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedFolderIds, setSelectedFolderIds] = useState<number[]>([]);
  const [ctx, setCtx] = useState<ContextMenuState | null>(null);
  const [clipboard, setClipboard] = useState<{ mode: 'copy' | 'cut'; fileIds: number[]; folderIds: number[] } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const dragDepth = useRef(0);
  const [shareUserId, setShareUserId] = useState('');
  const [publicLinkFile, setPublicLinkFile] = useState<{ id: number; name: string } | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const showToast = (kind: 'success' | 'error', title: string, body?: string) => setToast(makeToast(kind, title, body));
  const [showShare, setShowShare] = useState(false);
  const [shareUsers, setShareUsers] = useState<Array<{ id: number; username: string; first_name?: string }>>([]);


  const [preview, setPreview] = useState<{ file: FileItem; url: string; kind: string } | null>(null);

  function refresh(search = query) {
    setLoading(true);
    Promise.all([
      listFiles(search),
      listFolders().catch(() => [] as FolderItem[]),
    ])
      .then(([filesRes, foldersRes]) => {
        const fileList = Array.isArray(filesRes) ? filesRes : (filesRes.results || []);
        const folderList = Array.isArray(foldersRes)
          ? foldersRes
          : ((foldersRes as { results?: FolderItem[] }).results || []);
        setFolders(folderList);
        if (currentFolder === null) {
          setItems(fileList.filter(f => f.folder == null || f.folder === undefined));
        } else {
          setItems(fileList.filter(f => f.folder === currentFolder));
        }
      })
      .catch(e => setError(e instanceof Error ? e.message : 'خطا'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { refresh(query); setSelectedIds([]); setSelectedFolderIds([]); }, [query, currentFolder]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    setUploading(true);
    setError('');
    try {
      for (const file of Array.from(files)) {
        setUploadProgress({ name: file.name, percent: 0, loaded: 0, total: file.size });
        const created = await uploadFileToFolder(file, currentFolder, p => {
          setUploadProgress({ name: file.name, percent: p.percent, loaded: p.loaded, total: p.total });
        });
        setItems(prev => [created, ...prev]);
        try { await indexFile(created.id, created.name); } catch { /* optional */ }
      }
      setUploadProgress(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'آپلود ناموفق');
      setUploadProgress(null);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  
  async function handleConvert(file: FileItem, target: 'pdf' | 'docx') {
    setConvertingId(file.id);
    setError('');
    try {
      const created = await convertFile(file.id, target);
      setItems(prev => [created, ...prev]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'تبدیل ناموفق بود');
    } finally {
      setConvertingId(null);
    }
  }

  async function openPreview(file: FileItem) {
    const kind = mediaKind(file);
    try {
      const blob = await fetchFileBlob(file.id);
      const url = URL.createObjectURL(blob);
      setPreview({ file, url, kind });
    } catch (err) {
      if (kind === 'office') {
        navigate(`/files/${file.id}/edit`);
      } else {
        setError(err instanceof Error ? err.message : 'پیش‌نمایش ممکن نیست');
      }
    }
  }

  function closePreview() {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    setPreview(null);
  }


  const visibleFolders = folders.filter(f => (f.parent ?? null) === currentFolder);

  function toggleSelectFile(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (e.ctrlKey || e.metaKey) {
      setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
      return;
    }
    if (e.shiftKey && selectedIds.length) {
      const ids = items.map(i => i.id);
      const last = selectedIds[selectedIds.length - 1];
      const a = ids.indexOf(last);
      const b = ids.indexOf(id);
      if (a >= 0 && b >= 0) {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        setSelectedIds(ids.slice(lo, hi + 1));
        return;
      }
    }
    setSelectedIds([id]);
    setSelectedFolderIds([]);
  }

  function openContext(e: React.MouseEvent, fileId?: number, folderId?: number) {
    e.preventDefault();
    e.stopPropagation();
    if (fileId != null) {
      if (!selectedIds.includes(fileId)) {
        setSelectedIds([fileId]);
        setSelectedFolderIds([]);
      }
    } else if (folderId != null) {
      if (!selectedFolderIds.includes(folderId)) {
        setSelectedFolderIds([folderId]);
        setSelectedIds([]);
      }
    }
    setCtx({ x: e.clientX, y: e.clientY, blank: fileId == null && folderId == null });
  }

  async function doRename() {
    const name = window.prompt('نام جدید:');
    if (!name?.trim()) return;
    try {
      if (selectedIds.length === 1) {
        await bulkAction({ action: 'rename', file_ids: selectedIds, name: name.trim() });
      } else if (selectedFolderIds.length === 1) {
        await bulkAction({ action: 'rename', folder_ids: selectedFolderIds, name: name.trim() });
      }
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'تغییر نام ناموفق');
    }
  }

  function doCopy() {
    setClipboard({ mode: 'copy', fileIds: [...selectedIds], folderIds: [...selectedFolderIds] });
  }
  function doCut() {
    setClipboard({ mode: 'cut', fileIds: [...selectedIds], folderIds: [...selectedFolderIds] });
  }
  async function doPaste() {
    if (!clipboard) return;
    try {
      if (clipboard.mode === 'copy') {
        await bulkAction({ action: 'copy', file_ids: clipboard.fileIds, folder_ids: clipboard.folderIds, target_folder_id: currentFolder });
      } else {
        await bulkAction({ action: 'move', file_ids: clipboard.fileIds, folder_ids: clipboard.folderIds, target_folder_id: currentFolder });
        setClipboard(null);
      }
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'چسباندن ناموفق');
    }
  }
  async function doDelete() {
    if (!selectedIds.length && !selectedFolderIds.length) return;
    if (!window.confirm('موارد انتخاب‌شده به سطل زباله منتقل شوند؟')) return;
    try {
      await bulkAction({ action: 'delete', file_ids: selectedIds, folder_ids: selectedFolderIds });
      showToast('success', 'به سطل زباله منتقل شد', `${selectedIds.length + selectedFolderIds.length} مورد`);
      setSelectedIds([]);
      setSelectedFolderIds([]);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'حذف ناموفق');
    }
  }

  async function runAdvancedSearch() {
    setAdvBusy(true);
    setError('');
    try {
      const res = await advancedSearch({
        q: query.trim() || undefined,
        type: advType || undefined,
        folder: currentFolder,
        date_from: advDateFrom || undefined,
        date_to: advDateTo || undefined,
        min_size: advMinMb ? Math.round(Number(advMinMb) * 1024 * 1024) : undefined,
        max_size: advMaxMb ? Math.round(Number(advMaxMb) * 1024 * 1024) : undefined,
        include_shared: advShared,
        limit: 100,
      });
      setItems(res.results || []);
      setSemanticHits([]);
      showToast('success', 'جستجوی پیشرفته', `${res.count} نتیجه`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'جستجو ناموفق بود';
      setError(msg);
      showToast('error', 'خطا در جستجو', msg);
    } finally {
      setAdvBusy(false);
    }
  }

  async function doShare() {
    try {
      const users = await lookupUsers();
      setShareUsers(users as Array<{ id: number; username: string; first_name?: string }>);
    } catch { /* ignore */ }
    setShowShare(true);
  }
  async function submitShare() {
    if (!shareUserId || !selectedIds.length) return;
    try {
      for (const id of selectedIds) {
        await createShare(id, Number(shareUserId), 'view', '', { can_download: true, can_edit: false, can_reshare: false });
      }
      setShowShare(false);
      setShareUserId('');
      showToast('success', 'اشتراک‌گذاری انجام شد', `${selectedIds.length} فایل`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'اشتراک ناموفق';
      setError(msg);
      showToast('error', 'اشتراک ناموفق', msg);
    }
  }

  function onKeyDownExplorer(e: React.KeyboardEvent) {
    if (e.key === 'F2') { e.preventDefault(); doRename(); }
    if (e.key === 'Delete' || e.key === 'Backspace' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); doDelete(); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'c') { e.preventDefault(); doCopy(); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'x') { e.preventDefault(); doCut(); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'v') { e.preventDefault(); doPaste(); }
    if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
      e.preventDefault();
      setSelectedIds(items.map(i => i.id));
      setSelectedFolderIds(visibleFolders.map(f => f.id));
    }
  }

  function isFileDrag(e: React.DragEvent) {
    const types = e.dataTransfer?.types;
    if (!types) return false;
    const list = Array.from(types as unknown as string[]);
    return list.includes('Files') || list.includes('application/x-cloud-office-files');
  }

  function onDragEnterZone(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!isFileDrag(e)) return;
    dragDepth.current += 1;
    setDragOver(true);
  }

  function onDragOverZone(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!isFileDrag(e)) return;
    e.dataTransfer.dropEffect = e.dataTransfer.types.includes('application/x-cloud-office-files') ? 'move' : 'copy';
    setDragOver(true);
  }

  function onDragLeaveZone(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragOver(false);
  }

  async function onDropFiles(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragDepth.current = 0;
    setDragOver(false);

    // انتقال داخلی بین پوشه‌ها
    const raw = e.dataTransfer.getData('application/x-cloud-office-files');
    if (raw) {
      try {
        const payload = JSON.parse(raw) as { fileIds: number[]; folderIds: number[] };
        await bulkAction({
          action: 'move',
          file_ids: payload.fileIds || [],
          folder_ids: payload.folderIds || [],
          target_folder_id: currentFolder,
        });
        refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'انتقال ناموفق');
      }
      return;
    }

    // فایل از سیستم‌عامل (ویندوز / مک / لینوکس)
    const items = e.dataTransfer.items;
    const collected: globalThis.File[] = [];
    if (items && items.length) {
      for (let i = 0; i < items.length; i++) {
        const it = items[i];
        if (it.kind === 'file') {
          const f = it.getAsFile();
          if (f && f.size >= 0 && f.name) collected.push(f);
        }
      }
    }
    if (!collected.length) {
      collected.push(...Array.from(e.dataTransfer.files || []));
    }
    // فیلتر پوشه‌های خالی/آیتم‌های بدون محتوا که بعضی مرورگرها می‌فرستند
    const list = collected.filter(f => f && typeof f.name === 'string' && f.name.length > 0);

    if (!list.length) {
      setError('فایلی برای آپلود تشخیص داده نشد. دوباره از فایل‌منیجر بکشید و رها کنید.');
      return;
    }

    setUploading(true);
    setError('');
    try {
      for (const file of list) {
        setUploadProgress({ name: file.name, percent: 0, loaded: 0, total: file.size || 0 });
        const created = await uploadFileToFolder(file, currentFolder, p => {
          setUploadProgress({ name: file.name, percent: p.percent, loaded: p.loaded, total: p.total });
        });
        setItems(prev => {
          if (currentFolder === null && (created.folder == null || created.folder === undefined)) {
            return [created, ...prev];
          }
          if (created.folder === currentFolder) return [created, ...prev];
          return prev;
        });
        try { await indexFile(created.id, created.name); } catch { /* optional */ }
      }
      setUploadProgress(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'آپلود با درگ‌اند‌دراپ ناموفق بود');
      setUploadProgress(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">فضای کاری شخصی</span>
          <h1>فایل‌های من</h1>
          <p>آپلود عکس، فیلم، صدا، PDF و فایل‌های آفیس با پیش‌نمایش داخل برنامه.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input ref={inputRef} type="file" multiple accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.rtf" style={{ display: 'none' }} onChange={handleUpload} />
          <button type="button" className="edit-file" onClick={async () => {
            const name = window.prompt('نام پوشه جدید:');
            if (!name?.trim()) return;
            try {
              await createFolder(name.trim(), currentFolder);
              refresh();
            } catch (e) { setError(e instanceof Error ? e.message : 'ایجاد پوشه ناموفق'); }
          }}>پوشه جدید</button>
          <button type="button" className="edit-file" onClick={() => setShowCreateAI(v => !v)}>
            <Sparkles size={16} /> ایجاد با AI
          </button>
          <button className="primary" disabled={uploading} onClick={() => inputRef.current?.click()}>
            <Upload size={17} />
            {uploading ? 'در حال آپلود...' : 'آپلود فایل / رسانه'}
          </button>
        </div>
      </div>

      {error && <div className="form-error" role="alert">{error}</div>}

      {showCreateAI && (
        <section className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-head">
            <div>
              <h2>ایجاد فایل با هوش مصنوعی</h2>
              <p>عنوان و موضوع را بنویسید؛ محتوا تولید و به‌صورت فایل متنی در فضای شما ذخیره می‌شود.</p>
            </div>
          </div>
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            <label>عنوان فایل
              <input value={createTitle} onChange={e => setCreateTitle(e.target.value)} placeholder="مثلاً صورت‌جلسه هفتگی" />
            </label>
            <label>نوع سند
              <select value={createType} onChange={e => setCreateType(e.target.value)}>
                <option value="txt">متن ساده (.txt)</option>
                <option value="md">یادداشت (.md)</option>
                <option value="memo">یادداشت اداری</option>
                <option value="report">گزارش</option>
                <option value="list">فهرست / چک‌لیست</option>
              </select>
            </label>
          </div>
          <label style={{ marginTop: 10 }}>موضوع و جزئیات محتوا
            <textarea
              value={createPrompt}
              onChange={e => setCreatePrompt(e.target.value)}
              rows={4}
              placeholder="مثلاً: یک چک‌لیست آماده‌سازی ارائه مشتری با ۵ بخش بنویس"
            />
          </label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
            <button
              className="primary"
              type="button"
              disabled={aiBusy || createPrompt.trim().length < 3}
              onClick={async () => {
                setAiBusy(true);
                setError('');
                setCreatePreview('');
                try {
                  const res = await createFileWithAI(createTitle || 'سند جدید', createPrompt.trim(), createType, true);
                  setCreatePreview(res.content || res.text || '');
                  if (res.file) setItems(prev => [res.file as FileItem, ...prev]);
                  setCreatePrompt('');
                } catch (e) {
                  setError(e instanceof Error ? e.message : 'ایجاد فایل ناموفق بود');
                } finally {
                  setAiBusy(false);
                }
              }}
            >
              {aiBusy ? 'در حال تولید...' : 'تولید و ذخیره فایل'}
            </button>
            <button type="button" className="edit-file" onClick={() => setShowCreateAI(false)}>بستن</button>
          </div>
          {createPreview ? (
            <pre style={{ marginTop: 12, whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 220, overflow: 'auto', padding: 12, borderRadius: 12, background: 'var(--fill-quaternary)', border: '1px solid var(--line)' }}>
              {createPreview}
            </pre>
          ) : null}
        </section>
      )}

      <div className="panel" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <div className="view-switch">
            <button type="button" className={searchMode === 'name' ? 'active' : ''} onClick={() => { setSearchMode('name'); setShowAdvancedSearch(false); setSemanticHits([]); }}>جست‌وجوی نام</button>
            <button type="button" className={searchMode === 'semantic' ? 'active' : ''} onClick={() => { setSearchMode('semantic'); setShowAdvancedSearch(false); }}>جست‌وجوی معنایی AI</button>
            <button type="button" className={searchMode === 'advanced' || showAdvancedSearch ? 'active' : ''} onClick={() => { setSearchMode('advanced'); setShowAdvancedSearch(v => !v); }}>جست‌وجوی پیشرفته</button>
          </div>
          <input
            value={searchMode === 'name' ? query : semanticQ}
            onChange={e => {
              if (searchMode === 'name') setQuery(e.target.value);
              else setSemanticQ(e.target.value);
            }}
            onKeyDown={async e => {
              if (e.key !== 'Enter' || searchMode !== 'semantic') return;
              setAiBusy(true); setError('');
              try {
                const res = await semanticSearch(semanticQ.trim());
                setSemanticHits(res.results || []);
                if (!(res.results || []).length) setError('نتیجه‌ای پیدا نشد.');
              } catch (err) {
                setError(err instanceof Error ? err.message : 'جست‌وجو ناموفق');
              } finally {
                setAiBusy(false);
              }
            }}
            placeholder={searchMode === 'name' ? 'جست‌وجو بر اساس نام فایل...' : 'معنایی: مثلاً قرارداد اجاره یا صورت‌جلسه فروش'}
            style={{ flex: 1, minWidth: 200 }}
          />
          {searchMode === 'semantic' ? (
            <button
              className="primary"
              type="button"
              disabled={aiBusy || !semanticQ.trim()}
              onClick={async () => {
                setAiBusy(true); setError('');
                try {
                  const res = await semanticSearch(semanticQ.trim());
                  setSemanticHits(res.results || []);
                  if (!(res.results || []).length) setError('نتیجه‌ای پیدا نشد.');
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'جست‌وجو ناموفق');
                } finally {
                  setAiBusy(false);
                }
              }}
            >
              {aiBusy ? '...' : 'جست‌وجو'}
            </button>
          ) : null}
        </div>
        <p style={{ margin: '8px 0 0', fontSize: 11, color: 'var(--muted)' }}>
          {searchMode === 'name'
            ? 'جست‌وجوی سریع روی نام فایل‌های شما.'
            : 'جست‌وجوی مفهومی با AI. فایل‌های متنی بعد از آپلود یا ایجاد با AI ایندکس می‌شوند.'}
        </p>
      </div>
      {searchMode === 'semantic' && semanticHits.length > 0 ? (
        <div className="panel" style={{ marginBottom: 14 }}>
          <b style={{ fontSize: 12 }}>نتایج معنایی ({semanticHits.length})</b>
          {semanticHits.map(h => (
            <div key={h.file_id} className="file-row" style={{ cursor: 'pointer' }} onClick={() => { const f = items.find(i => i.id === h.file_id); if (f) openPreview(f); }}>
              <div className="file-info">
                <b>{h.name}</b>
                <small>ارتباط {Math.round(h.score * 100)}% · {(h.preview || '').slice(0, 100)}</small>
              </div>
            </div>
          ))}
        </div>
      ) : null}

{uploadProgress && (
        <div className="panel" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
            <span>آپلود: {uploadProgress.name}</span>
            <span>{uploadProgress.percent}% — {formatBytes(uploadProgress.loaded)} از {formatBytes(uploadProgress.total)}</span>
          </div>
          <div style={{ height: 10, borderRadius: 6, background: '#ffffff12', overflow: 'hidden' }}>
            <div style={{ width: `${uploadProgress.percent}%`, height: '100%', background: '#7667f7', transition: 'width .15s' }} />
          </div>
          <small style={{ color: 'var(--muted)', fontSize: 10 }}>باقی‌مانده: {formatBytes(Math.max(0, uploadProgress.total - uploadProgress.loaded))}</small>
        </div>
      )}

      <div
        className={'drop-zone-root' + (dragOver ? ' is-dragover' : '')}
        onDragEnter={onDragEnterZone}
        onDragOver={onDragOverZone}
        onDragLeave={onDragLeaveZone}
        onDrop={onDropFiles}
      >
        {dragOver && (
          <div className="drop-overlay" aria-hidden>
            <div className="drop-overlay-card">
              <Upload size={28} />
              <strong>رها کنید تا آپلود شود</strong>
              <span>فایل‌ها در پوشه جاری ذخیره می‌شوند</span>
            </div>
          </div>
        )}
      <div className="files-toolbar">
        <div className="search">
          <Search size={16} />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="جست‌وجوی فایل..." />
        </div>
        <div className="view-switch">
          <button className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')}><Grid2X2 size={17} /></button>
          <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}><List size={18} /></button>
        </div>
      </div>

      
      {(selectedIds.length > 0 || selectedFolderIds.length > 0) && (
        <div className="selection-bar">
          <b>{selectedIds.length + selectedFolderIds.length}</b> مورد انتخاب شده
          <button type="button" className="edit-file" onClick={doCopy}>کپی</button>
          <button type="button" className="edit-file" onClick={doCut}>برش</button>
          <button type="button" className="edit-file" onClick={doPaste} disabled={!clipboard}>چسباندن</button>
          <button type="button" className="edit-file" onClick={doRename} disabled={selectedIds.length + selectedFolderIds.length !== 1}>تغییر نام</button>
          <button type="button" className="edit-file" onClick={doShare} disabled={!selectedIds.length}>اشتراک</button>
          <button type="button" className="edit-file" onClick={doDelete}>حذف</button>
          <button type="button" className="edit-file" onClick={() => { setSelectedIds([]); setSelectedFolderIds([]); }}>لغو انتخاب</button>
        </div>
      )}
      {clipboard && (
        <p className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          کلیپ‌بورد: {clipboard.mode === 'copy' ? 'کپی' : 'برش'} — {clipboard.fileIds.length + clipboard.folderIds.length} مورد (Ctrl+V برای چسباندن)
        </p>
      )}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <button type="button" className={'folder-chip' + (currentFolder === null ? ' active' : '')} onClick={() => setCurrentFolder(null)}>
          <Folder size={14} /> ریشه
        </button>
        {folders.filter(f => f.parent == null).map(f => (
          <button
            key={f.id}
            type="button"
            className={'folder-chip' + (currentFolder === f.id ? ' active' : '')}
            onClick={() => setCurrentFolder(f.id)}
            onContextMenu={e => openContext(e, undefined, f.id)}
            onDragOver={e => { e.preventDefault(); }}
            onDrop={async e => {
              e.preventDefault();
              e.stopPropagation();
              const raw = e.dataTransfer.getData('application/x-cloud-office-files');
              if (!raw) return;
              try {
                const payload = JSON.parse(raw);
                await bulkAction({ action: 'move', file_ids: payload.fileIds, folder_ids: payload.folderIds, target_folder_id: f.id });
                refresh();
              } catch (err) {
                setError(err instanceof Error ? err.message : 'انتقال ناموفق');
              }
            }}
          >
            <Folder size={14} /> {f.name}
          </button>
        ))}
      </div>
{loading ? (
        <div className="panel empty"><h2>در حال دریافت فایل‌ها...</h2></div>
      ) : items.length === 0 ? (
        <div className="panel empty"><h2>فایلی نیست</h2><p>عکس، فیلم، صدا یا سند آپلود کنید.</p></div>
      ) : view === 'grid' ? (
        <div className="file-grid">
          {items.map(file => (
            <article
              className={'file-card' + (selectedIds.includes(file.id) ? ' selected' : '')}
              key={file.id}
              draggable
              onClick={e => toggleSelectFile(file.id, e)}
              onDoubleClick={() => openPreview(file)}
              onContextMenu={e => openContext(e, file.id)}
              onDragStart={e => {
                const ids = selectedIds.includes(file.id) ? selectedIds : [file.id];
                e.dataTransfer.setData('application/x-cloud-office-files', JSON.stringify({ fileIds: ids, folderIds: selectedFolderIds }));
                e.dataTransfer.effectAllowed = 'move';
                if (!selectedIds.includes(file.id)) setSelectedIds([file.id]);
              }}
            >
              <div className="card-top">
                <span className="file-glyph" style={{ color: file.color, background: `${file.color}18` }}>
                  {file.type === 'folder' ? <Folder size={21} /> : <FileText size={21} />}
                </span>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button className="more" aria-label="پیش‌نمایش" onClick={() => openPreview(file)}><Eye size={16} /></button>
                  <button className="more" aria-label="دانلود" onClick={() => downloadFile(file.id, file.name).catch(e => setError(e.message))}><Download size={16} /></button>
                  {isPdfFile(file) && (
                    <button className="more" title="تبدیل به Word" disabled={convertingId === file.id} onClick={() => handleConvert(file, 'docx')}>
                      {convertingId === file.id ? '...' : '→ Word'}
                    </button>
                  )}
                  {isWordFile(file) && (
                    <button className="more" title="تبدیل به PDF" disabled={convertingId === file.id} onClick={() => handleConvert(file, 'pdf')}>
                      {convertingId === file.id ? '...' : '→ PDF'}
                    </button>
                  )}
                </div>
              </div>
              <b>{file.name}</b>
              <small>{file.size} · {file.updated}</small>
              <div className="card-footer">
                <span>{file.owner}</span>
                {isEditableFile(file) && (
                  <button className="edit-file" onClick={() => navigate(`/files/${file.id}/edit`)}>
                    <FilePenLine size={14} /> ویرایش
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <section className="panel">
          {items.map(file => (
            <div
              className={'file-row' + (selectedIds.includes(file.id) ? ' selected' : '')}
              key={file.id}
              draggable
              onClick={e => toggleSelectFile(file.id, e)}
              onDoubleClick={() => openPreview(file)}
              onContextMenu={e => openContext(e, file.id)}
              onDragStart={e => {
                const ids = selectedIds.includes(file.id) ? selectedIds : [file.id];
                e.dataTransfer.setData('application/x-cloud-office-files', JSON.stringify({ fileIds: ids, folderIds: selectedFolderIds }));
                if (!selectedIds.includes(file.id)) setSelectedIds([file.id]);
              }}
            >
              <span className="file-glyph" style={{ color: file.color, background: `${file.color}18` }}>
                {file.type === 'folder' ? <Folder size={20} /> : <FileText size={20} />}
              </span>
              <div className="file-info"><b>{file.name}</b><small>{file.owner} · {file.updated}</small></div>
              <span className="file-size">{file.size}</span>
              <button className="more" onClick={() => openPreview(file)}><Eye size={16} /></button>
              <button className="more" onClick={() => downloadFile(file.id, file.name).catch(e => setError(e.message))}><Download size={16} /></button>
              {isPdfFile(file) && (
                <button className="more" disabled={convertingId === file.id} onClick={() => handleConvert(file, 'docx')}>{convertingId === file.id ? '...' : '→ Word'}</button>
              )}
              {isWordFile(file) && (
                <button className="more" disabled={convertingId === file.id} onClick={() => handleConvert(file, 'pdf')}>{convertingId === file.id ? '...' : '→ PDF'}</button>
              )}
            </div>
          ))}
        </section>
      )}

      {preview && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, background: '#000000cc', display: 'grid', placeItems: 'center', padding: 20 }} onClick={closePreview}>
          <div className="panel" style={{ width: 'min(900px, 100%)', maxHeight: '90vh', overflow: 'auto', position: 'relative' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <strong>{preview.file.name}</strong>
              <button className="more" onClick={closePreview}><X size={18} /></button>
            </div>
            {preview.kind === 'image' && <img src={preview.url} alt={preview.file.name} style={{ maxWidth: '100%', borderRadius: 12 }} />}
            {preview.kind === 'video' && <video src={preview.url} controls style={{ width: '100%', borderRadius: 12 }} />}
            {preview.kind === 'audio' && <audio src={preview.url} controls style={{ width: '100%' }} />}
            {preview.kind === 'pdf' && <iframe src={preview.url} title={preview.file.name} style={{ width: '100%', height: '70vh', border: 0, borderRadius: 12 }} />}
            {preview.kind === 'office' && (
              <div style={{ textAlign: 'center', padding: 24 }}>
                <p>برای ویرایش آنلاین آفیس از دکمه زیر استفاده کنید.</p>
                <button className="primary" onClick={() => { closePreview(); navigate(`/files/${preview.file.id}/edit`); }}>باز کردن در ویرایشگر</button>
              </div>
            )}
            {preview.kind === 'other' && <p>پیش‌نمایش این نوع فایل پشتیبانی نمی‌شود. می‌توانید دانلود کنید.</p>}
            <div style={{ marginTop: 12 }}>
              <button className="primary" onClick={() => downloadFile(preview.file.id, preview.file.name)}><Download size={16} /> دانلود</button>
              {isPdfFile(preview.file) && (
                <button className="edit-file" disabled={convertingId === preview.file.id} onClick={() => handleConvert(preview.file, 'docx')}>
                  {convertingId === preview.file.id ? 'در حال تبدیل...' : 'تبدیل به Word'}
                </button>
              )}
              {isWordFile(preview.file) && (
                <button className="edit-file" disabled={convertingId === preview.file.id} onClick={() => handleConvert(preview.file, 'pdf')}>
                  {convertingId === preview.file.id ? 'در حال تبدیل...' : 'تبدیل به PDF'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      </div>{/* end drop-zone-root */}
      <FileContextMenu
        menu={ctx}
        selectedCount={selectedIds.length + selectedFolderIds.length}
        canPaste={!!clipboard}
        onClose={() => setCtx(null)}
        onOpen={() => {
          const f = items.find(i => i.id === selectedIds[0]);
          if (f) openPreview(f);
        }}
        onRename={doRename}
        onCopy={doCopy}
        onCut={doCut}
        onPaste={doPaste}
        onDelete={doDelete}
        onPublicLink={() => {
            if (selectedIds.length === 1) {
              const f = items.find(x => x.id === selectedIds[0]);
              if (f) setPublicLinkFile({ id: f.id, name: f.name });
            }
          }}
          onShare={doShare}
        onDownload={() => {
          const f = items.find(i => i.id === selectedIds[0]);
          if (f) downloadFile(f.id, f.name).catch(e => setError(e.message));
        }}
        showConvertWord={selectedIds.length === 1 && !!items.find(i => i.id === selectedIds[0] && isPdfFile(i))}
        showConvertPdf={selectedIds.length === 1 && !!items.find(i => i.id === selectedIds[0] && isWordFile(i))}
        onConvertWord={() => {
          const f = items.find(i => i.id === selectedIds[0]);
          if (f) handleConvert(f, 'docx');
        }}
        onConvertPdf={() => {
          const f = items.find(i => i.id === selectedIds[0]);
          if (f) handleConvert(f, 'pdf');
        }}
      />
      <Toast toast={toast} onClose={() => setToast(null)} />
      {publicLinkFile && (
        <PublicShareModal
          fileId={publicLinkFile.id}
          fileName={publicLinkFile.name}
          onClose={() => setPublicLinkFile(null)}
          onToast={showToast}
        />
      )}
      {showShare && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 70, background: '#0008', display: 'grid', placeItems: 'center' }} onClick={() => setShowShare(false)}>
          <div className="panel" style={{ width: 'min(400px, 92vw)' }} onClick={e => e.stopPropagation()}>
            <h2 style={{ marginTop: 0, fontSize: 16 }}>اشتراک‌گذاری</h2>
            <label>کاربر
              <select value={shareUserId} onChange={e => setShareUserId(e.target.value)}>
                <option value="">انتخاب...</option>
                {shareUsers.map(u => (
                  <option key={u.id} value={u.id}>{u.first_name || u.username}</option>
                ))}
              </select>
            </label>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button className="primary" type="button" onClick={submitShare}>اشتراک</button>
              <button type="button" className="edit-file" onClick={() => setShowShare(false)}>انصراف</button>
            </div>
          </div>
        </div>
      )}

    </>
  );
}

