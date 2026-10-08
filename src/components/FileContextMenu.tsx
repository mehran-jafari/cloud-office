import type { ReactNode } from 'react';
import { Copy, FolderInput, Pencil, Share2, Trash2, ClipboardPaste, Scissors, Download, FileType, Link2 } from 'lucide-react';

export type ContextMenuState = {
  x: number;
  y: number;
  /** empty area menu when no selection focus */
  blank?: boolean;
};

type Props = {
  menu: ContextMenuState | null;
  selectedCount: number;
  canPaste: boolean;
  onClose: () => void;
  onOpen?: () => void;
  onRename: () => void;
  onCopy: () => void;
  onCut: () => void;
  onPaste: () => void;
  onDelete: () => void;
  onShare: () => void;
  onPublicLink?: () => void;
  onDownload?: () => void;
  onConvertPdf?: () => void;
  onConvertWord?: () => void;
  showConvertPdf?: boolean;
  showConvertWord?: boolean;
};

export function FileContextMenu({
  menu,
  selectedCount,
  canPaste,
  onClose,
  onOpen,
  onRename,
  onCopy,
  onCut,
  onPaste,
  onDelete,
  onShare,
  onPublicLink,
  onDownload,
  onConvertPdf,
  onConvertWord,
  showConvertPdf,
  showConvertWord,
}: Props) {
  if (!menu) return null;

  const item = (label: string, icon: ReactNode, action: () => void, disabled?: boolean) => (
    <button
      type="button"
      disabled={disabled}
      className="ctx-item"
      onClick={() => {
        if (disabled) return;
        action();
        onClose();
      }}
    >
      {icon}
      <span>{label}</span>
    </button>
  );

  return (
    <>
      <div className="ctx-backdrop" onClick={onClose} onContextMenu={e => { e.preventDefault(); onClose(); }} />
      <div
        className="ctx-menu"
        style={{ top: menu.y, left: menu.x }}
        role="menu"
        onClick={e => e.stopPropagation()}
      >
        {!menu.blank && selectedCount > 0 && (
          <>
            {selectedCount === 1 && onOpen && item('باز کردن', <FileType size={15} />, onOpen)}
            {selectedCount === 1 && item('تغییر نام', <Pencil size={15} />, onRename)}
            {item('کپی', <Copy size={15} />, onCopy)}
            {item('برش', <Scissors size={15} />, onCut)}
            {item('اشتراک‌گذاری', <Share2 size={15} />, onShare)}
            {selectedCount === 1 && onPublicLink && item('لینک عمومی', <Link2 size={15} />, onPublicLink)}
            {selectedCount === 1 && onDownload && item('دانلود', <Download size={15} />, onDownload)}
            {showConvertWord && onConvertWord && item('تبدیل به Word', <FileType size={15} />, onConvertWord)}
            {showConvertPdf && onConvertPdf && item('تبدیل به PDF', <FileType size={15} />, onConvertPdf)}
            {item('حذف', <Trash2 size={15} />, onDelete)}
            <div className="ctx-sep" />
          </>
        )}
        {item('چسباندن', <ClipboardPaste size={15} />, onPaste, !canPaste)}
        {item('انتقال به پوشه…', <FolderInput size={15} />, onPaste, !canPaste && selectedCount === 0)}
      </div>
    </>
  );
}
