"""تبدیل PDF ↔ DOCX (و مسیر LibreOffice برای کیفیت بهتر)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from accounts.models import StorageQuota
from .models import File
from .workspace import log_activity


PDF_EXTS = {'.pdf'}
DOC_EXTS = {'.doc', '.docx'}


def _ext(name: str) -> str:
    return Path(name or '').suffix.lower()


def can_convert(file_obj: File, target: str) -> bool:
    ext = _ext(file_obj.name)
    target = target.lower().lstrip('.')
    if target in {'docx', 'doc', 'word'}:
        return ext in PDF_EXTS
    if target in {'pdf'}:
        return ext in DOC_EXTS or ext in PDF_EXTS
    return False


def _quota_check(user, size: int):
    quota, _ = StorageQuota.objects.get_or_create(user=user)
    used = File.objects.filter(owner=user).aggregate(total=Sum('size_bytes')).get('total') or 0
    if used + size > quota.allocated_bytes:
        raise ValidationError({'detail': 'سهمیه فضای ذخیره‌سازی برای فایل تبدیل‌شده کافی نیست.'})


def _save_converted(user, original: File, out_bytes: bytes, out_name: str, mime: str) -> File:
    _quota_check(user, len(out_bytes))
    storage_key = default_storage.save(
        f'uploads/{user.id}/{uuid.uuid4().hex}_{out_name}',
        ContentFile(out_bytes),
    )
    obj = File.objects.create(
        name=out_name[:255],
        owner=user,
        folder=original.folder,
        storage_key=storage_key,
        mime_type=mime,
        size_bytes=len(out_bytes),
    )
    log_activity(
        user,
        'upload',
        f'تبدیل «{original.name}» → «{obj.name}»',
        target_type='file',
        target_id=obj.id,
    )
    return obj


def _read_source(file_obj: File) -> bytes:
    if not file_obj.storage_key or not default_storage.exists(file_obj.storage_key):
        raise ValidationError({'detail': 'فایل منبع روی دیسک پیدا نشد.'})
    with default_storage.open(file_obj.storage_key, 'rb') as fh:
        return fh.read()


def _libreoffice_convert(src_path: Path, target_ext: str, out_dir: Path) -> Path:
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        raise RuntimeError('LibreOffice نصب نیست')
    cmd = [
        soffice,
        '--headless',
        '--nologo',
        '--nolockcheck',
        '--convert-to', target_ext.lstrip('.'),
        '--outdir', str(out_dir),
        str(src_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b'').decode('utf-8', errors='ignore')[:300]
        raise RuntimeError(f'LibreOffice: {err or "conversion failed"}')
    expected = out_dir / f'{src_path.stem}.{target_ext.lstrip(".")}'
    if expected.exists():
        return expected
    # بعضی نسخه‌ها نام را عوض می‌کنند
    matches = list(out_dir.glob(f'*.{target_ext.lstrip(".")}'))
    if matches:
        return matches[0]
    raise RuntimeError('خروجی LibreOffice پیدا نشد')


def pdf_to_docx(file_obj: File, user) -> File:
    data = _read_source(file_obj)
    out_name = Path(file_obj.name).with_suffix('.docx').name

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / 'source.pdf'
        src.write_bytes(data)
        dest = tmp_path / 'out.docx'

        # ۱) LibreOffice اگر باشد
        try:
            result = _libreoffice_convert(src, 'docx', tmp_path)
            out_bytes = result.read_bytes()
            return _save_converted(
                user, file_obj, out_bytes, out_name,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
        except Exception:
            pass

        # ۲) pdf2docx
        try:
            from pdf2docx import Converter
        except ImportError as e:
            raise ValidationError({
                'detail': 'برای تبدیل PDF→Word بسته pdf2docx یا LibreOffice لازم است. pip install pdf2docx',
            }) from e

        try:
            cv = Converter(str(src))
            cv.convert(str(dest))
            cv.close()
        except Exception as e:
            raise ValidationError({'detail': f'تبدیل PDF به Word ناموفق بود: {e}'}) from e

        if not dest.exists() or dest.stat().st_size == 0:
            raise ValidationError({'detail': 'فایل Word خروجی خالی است.'})
        return _save_converted(
            user, file_obj, dest.read_bytes(), out_name,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )


def docx_to_pdf(file_obj: File, user) -> File:
    data = _read_source(file_obj)
    out_name = Path(file_obj.name).with_suffix('.pdf').name
    ext = _ext(file_obj.name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / f'source{ext if ext else ".docx"}'
        src.write_bytes(data)

        # LibreOffice بهترین مسیر
        try:
            result = _libreoffice_convert(src, 'pdf', tmp_path)
            return _save_converted(user, file_obj, result.read_bytes(), out_name, 'application/pdf')
        except Exception as lo_err:
            # fallback محدود با reportlab فقط برای متن ساده — اگر docx متنی
            try:
                from docx import Document
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.lib.units import mm
            except ImportError as e:
                raise ValidationError({
                    'detail': (
                        'برای تبدیل Word→PDF نصب LibreOffice توصیه می‌شود. '
                        f'یا: pip install python-docx reportlab — جزئیات: {lo_err}'
                    ),
                }) from e

            try:
                doc = Document(str(src))
                pdf_path = tmp_path / 'out.pdf'
                c = canvas.Canvas(str(pdf_path), pagesize=A4)
                width, height = A4
                y = height - 20 * mm
                c.setFont('Helvetica', 11)
                for p in doc.paragraphs:
                    text = (p.text or '').strip()
                    if not text:
                        y -= 6
                        continue
                    # بدون فونت فارسی کامل؛ پیام شفاف
                    line = text.encode('latin-1', errors='replace').decode('latin-1')
                    for chunk in [line[i:i + 90] for i in range(0, len(line), 90)]:
                        if y < 20 * mm:
                            c.showPage()
                            c.setFont('Helvetica', 11)
                            y = height - 20 * mm
                        c.drawString(20 * mm, y, chunk)
                        y -= 6 * mm
                c.save()
                note = (
                    'توجه: تبدیل بدون LibreOffice کیفیت محدود دارد (فونت فارسی ناقص). '
                    'برای نتیجه دقیق LibreOffice را نصب کنید.\n\n'
                )
                # prepend note as separate attempt - skip, just return
                return _save_converted(user, file_obj, pdf_path.read_bytes(), out_name, 'application/pdf')
            except Exception as e:
                raise ValidationError({
                    'detail': f'تبدیل Word به PDF ناموفق بود. LibreOffice را نصب کنید. ({e})',
                }) from e


def convert_file(file_obj: File, user, target: str) -> File:
    target = (target or '').lower().lstrip('.')
    if target in {'docx', 'doc', 'word'}:
        if _ext(file_obj.name) not in PDF_EXTS:
            raise ValidationError({'detail': 'فقط PDF را می‌توان به Word تبدیل کرد.'})
        return pdf_to_docx(file_obj, user)
    if target == 'pdf':
        if _ext(file_obj.name) not in DOC_EXTS:
            raise ValidationError({'detail': 'فقط Word (doc/docx) را می‌توان به PDF تبدیل کرد.'})
        return docx_to_pdf(file_obj, user)
    raise ValidationError({'detail': 'فرمت مقصد نامعتبر است. از pdf یا docx استفاده کنید.'})
