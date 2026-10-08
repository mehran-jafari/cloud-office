from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction

from . import provider
from .models import AIQuota, AIUsageLog, FileEmbedding


def get_or_create_quota(user) -> AIQuota:
    quota, _ = AIQuota.objects.get_or_create(user=user)
    today = date.today()
    if quota.period_start.month != today.month or quota.period_start.year != today.year:
        quota.used_tokens = 0
        quota.period_start = today
        quota.save(update_fields=['used_tokens', 'period_start', 'updated_at'])
    return quota


MIN_TOKENS_FOR_REMOTE_CALL = 200


def ensure_quota(user, minimum: int = MIN_TOKENS_FOR_REMOTE_CALL):
    """قبل از هر فراخوانی مدل چک می‌شود تا با سهمیه تمام‌شده هزینه API ایجاد نشود."""
    quota = get_or_create_quota(user)
    if quota.remaining() < minimum:
        raise PermissionError(
            f'سهمیه توکن AI این ماه کافی نیست (باقی‌مانده: {quota.remaining()}).'
        )
    return quota


def consume_tokens(user, action: str, tokens: int, model_name: str = '', success: bool = True, detail: str = ''):
    quota = get_or_create_quota(user)
    with transaction.atomic():
        # قفل ردیف برای جلوگیری از lost-update در درخواست‌های همزمان
        quota = AIQuota.objects.select_for_update().get(pk=quota.pk)
        if success and tokens > 0:
            if quota.remaining() < tokens:
                raise PermissionError(
                    f'سهمیه توکن AI این ماه کافی نیست (باقی‌مانده: {quota.remaining()}، نیاز: {tokens}).'
                )
            quota.used_tokens += tokens
            quota.save(update_fields=['used_tokens', 'updated_at'])
        AIUsageLog.objects.create(
            user=user,
            action=action,
            tokens_used=tokens if success else 0,
            model_name=model_name or '',
            success=success,
            detail=(detail or '')[:300],
        )
    return quota


def draft_mail(user, subject: str, notes: str, tone: str = 'formal', recipient_name: str = '') -> dict:
    ensure_quota(user)
    tone = tone if tone in {'formal', 'friendly', 'short'} else 'formal'
    system = (
        'DRAFT_MAIL | پیش‌نویس نامه. تو منشی اداری حرفه‌ای هستی. '
        'فقط متن نامه فارسی را برگردان؛ بدون توضیح، بدون مارک‌داون اضافه. '
        'ساختار: سلام، بدنه منسجم، درخواست/جمع‌بندی، امضا. '
        'حقایق جعلی نساز؛ فقط از نکات کاربر استفاده کن.'
    )
    user_msg = (
        f'موضوع: {subject or "بدون موضوع"}\n'
        f'لحن: {tone}\n'
        f'گیرنده: {recipient_name or "—"}\n'
        f'نکات:\n{notes.strip()}'
    )
    temp = 0.25 if tone == 'formal' else 0.45
    text, tokens, model = provider.chat_completion(system, user_msg, max_tokens=1000, temperature=temp)
    quota = consume_tokens(user, 'draft_mail', tokens, model, True, (subject or '')[:80])
    return {
        'text': text,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'tone': tone,
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def summarize_text(user, text: str, purpose: str = 'general') -> dict:
    ensure_quota(user)
    text = (text or '').strip()
    if purpose == 'support':
        system = (
            'SUMMARIZE_SUPPORT | خلاصه پشتیبانی. '
            'خروجی فارسی کوتاه با بخش‌های: موضوع، وضعیت، اقدام لازم. بدون مقدمه.'
        )
    else:
        system = (
            'SUMMARIZE | خلاصه متن. '
            '۳ تا ۷ بولت فارسی از نکات کلیدی؛ بدون مقدمه و بدون تکرار.'
        )
    out, tokens, model = provider.chat_completion(system, text[:14000], max_tokens=700, temperature=0.2)
    quota = consume_tokens(user, 'summarize', tokens, model, True, purpose)
    return {
        'text': out,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def suggest_support_reply(user, conversation_text: str) -> dict:
    ensure_quota(user)
    system = (
        'SUPPORT_REPLY | پاسخ پشتیبانی. '
        'یک پاسخ فارسی مودب، کوتاه و عملی برای کارشناس بنویس. '
        'وعده زمانی قطعی نده مگر در متن باشد. بدون امضای انگلیسی.'
    )
    out, tokens, model = provider.chat_completion(
        system, conversation_text[:10000], max_tokens=600, temperature=0.35
    )
    quota = consume_tokens(user, 'support_reply', tokens, model, True)
    return {
        'text': out,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }



def auto_support_answer(user, user_message: str, conversation_context: str = '', subject: str = '') -> dict:
    """
    پاسخ خودکار لایه اول پشتیبانی.
    خروجی استاندارد:
      text, confidence (0..1), needs_human (bool), tokens_used, model, provider
    """
    ensure_quota(user)
    system = (
        'AUTO_SUPPORT | تو دستیار پشتیبانی سازمانی فارسی هستی.\n'
        'قوانین سخت:\n'
        '1) فقط درباره محصول/فایل/حساب/اتصال امن/کنفرانس در همین سامانه صحبت کن.\n'
        '2) اگر مطمئن نیستی یا موضوع نیاز به دسترسی انسانی دارد '
        '(مالی، حذف داده، تغییر نقش، امنیت، باگ بحرانی، شکایت)، '
        'صریحاً بگو که کاربر را به پشتیبان انسانی وصل می‌کنی و needs_human را در نظر بگیر.\n'
        '3) وعده زمانی قطعی نده.\n'
        '4) پاسخ کوتاه، مودب و عملی باشد.\n'
        '5) در خط اول فقط یکی از این دو برچسب را بنویس:\n'
        'CONFIDENT: یا NEEDS_HUMAN:\n'
        'سپس متن پاسخ برای کاربر.'
    )
    user_msg = (
        f'موضوع تیکت: {subject or "—"}\n'
        f'تاریخچه:\n{(conversation_context or "")[:4000]}\n\n'
        f'آخرین پیام کاربر:\n{(user_message or "").strip()[:2000]}'
    )
    out, tokens, model = provider.chat_completion(
        system, user_msg, max_tokens=700, temperature=0.3,
        timeout=getattr(settings, 'SUPPORT_AI_TIMEOUT', 20),
    )
    text = (out or '').strip()
    needs_human = True
    confidence = 0.35
    upper = text.upper()
    if upper.startswith('CONFIDENT:'):
        needs_human = False
        confidence = 0.82
        text = text.split(':', 1)[-1].strip()
    elif upper.startswith('NEEDS_HUMAN:'):
        needs_human = True
        confidence = 0.4
        text = text.split(':', 1)[-1].strip()
    else:
        # بدون برچسب → محافظه‌کار
        needs_human = True
        confidence = 0.45

    if needs_human and 'پشتیبان' not in text and 'کارشناس' not in text:
        text = (
            (text + '\n\n' if text else '') +
            'برای پاسخ دقیق‌تر و کامل‌تر شما را به کارشناس پشتیبانی متصل می‌کنم. '
            'پیام شما ثبت شده است.'
        )

    try:
        quota = consume_tokens(user, 'auto_support', tokens, model, True, (subject or '')[:80])
        remaining = quota.remaining()
    except PermissionError:
        # سهمیه تمام — فقط پیام ارجاع به انسان
        return {
            'text': (
                'در حال حاضر پشتیبان آنلاین در دسترس نیست و پاسخ خودکار موقتاً محدود است. '
                'پیام شما ثبت شد و به‌محض حضور کارشناس رسیدگی می‌شود.'
            ),
            'confidence': 0.0,
            'needs_human': True,
            'tokens_used': 0,
            'model': model or '',
            'provider': 'none',
            'remaining_tokens': 0,
        }

    return {
        'text': text,
        'confidence': confidence,
        'needs_human': needs_human,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': remaining,
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def speech_to_text(user, file_bytes: bytes, filename: str) -> dict:
    ensure_quota(user)
    text, tokens, model = provider.transcribe_audio(file_bytes, filename)
    ok = model != 'local-stt-unavailable'
    quota = consume_tokens(user, 'stt', tokens, model, True, filename[:80])
    return {
        'text': text,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if ok and provider.has_remote() else 'local',
        'usable': ok,
    }


def meeting_summary(user, transcript: str, title: str = 'جلسه') -> dict:
    ensure_quota(user)
    system = (
        'MEETING_SUMMARY | خلاصه جلسه. '
        'خروجی ساخت‌یافته فارسی: موضوعات، تصمیمات، اقدامات، موارد باز. '
        'اگر اطلاعات کم است صریح بگو کمبود داده.'
    )
    user_msg = f'عنوان: {title}\n\n{transcript[:16000]}'
    out, tokens, model = provider.chat_completion(system, user_msg, max_tokens=1100, temperature=0.25)
    quota = consume_tokens(user, 'meeting_summary', tokens, model, True, title[:80])
    return {
        'text': out,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def extract_file_text(file_obj, max_chars: int = 12000) -> str:
    """استخراج متن ساده از فایل‌های متنی/csv برای ایندکس معنایی."""
    name = (file_obj.name or '').lower()
    parts = [file_obj.name or '']
    if file_obj.mime_type:
        parts.append(file_obj.mime_type)
    key = file_obj.storage_key
    if key and default_storage.exists(key):
        ext = Path(name).suffix.lower()
        if ext in {'.txt', '.md', '.csv', '.json', '.log', '.rtf'} or (
            file_obj.mime_type or ''
        ).startswith('text/'):
            try:
                with default_storage.open(key, 'rb') as fh:
                    raw = fh.read(max_chars * 2)
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('utf-8', errors='ignore')
                parts.append(text[:max_chars])
            except Exception:
                pass
    return '\n'.join(p for p in parts if p).strip()


def index_file_text(user, file_obj, text: str = '') -> dict:
    ensure_quota(user)
    content = (text or '').strip() or extract_file_text(file_obj)
    if not content:
        content = file_obj.name or f'file-{file_obj.id}'
    vectors, tokens, model = provider.embed_texts([content[:8000]])
    vec = vectors[0]
    emb, _ = FileEmbedding.objects.update_or_create(
        file=file_obj,
        defaults={
            'model_name': model,
            'dims': len(vec),
            'vector': vec,
            'text_preview': content[:500],
        },
    )
    quota = consume_tokens(user, 'embed', tokens, model, True, file_obj.name[:80])
    return {
        'file_id': file_obj.id,
        'dims': emb.dims,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'preview': emb.text_preview,
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def semantic_search(user, query: str, limit: int = 10) -> dict:
    ensure_quota(user)
    query = (query or '').strip()
    q_vecs, tokens, model = provider.embed_texts([query])
    q = q_vecs[0]
    import re
    q_tokens = set(re.findall(r'[\w\u0600-\u06FF]+', query.lower()))

    results = []
    qs = FileEmbedding.objects.select_related('file', 'file__owner').filter(file__owner=user)
    for emb in qs[:800]:
        score = provider.cosine(q, emb.vector or [])
        # تقویت با تطبیق نام فایل
        name = (emb.file.name or '').lower()
        preview = (emb.text_preview or '').lower()
        name_hits = sum(1 for t in q_tokens if t in name)
        preview_hits = sum(1 for t in q_tokens if t in preview)
        boost = 0.05 * name_hits + 0.02 * preview_hits
        final = min(1.0, score + boost)
        results.append({
            'file_id': emb.file_id,
            'name': emb.file.name,
            'score': round(final, 4),
            'vector_score': round(score, 4),
            'preview': emb.text_preview,
        })
    results.sort(key=lambda x: x['score'], reverse=True)
    results = [r for r in results if r['score'] > 0.05][:limit]
    quota = consume_tokens(user, 'semantic_search', tokens, model, True, query[:80])
    return {
        'results': results,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
        'query': query,
        'count': len(results),
    }



def create_document_content(user, title: str, prompt: str, doc_type: str = 'txt') -> dict:
    """تولید محتوای فایل با AI برای ایجاد سند جدید."""
    ensure_quota(user)
    kind = doc_type if doc_type in {'txt', 'md', 'memo', 'report', 'list'} else 'txt'
    system = (
        'CREATE_FILE | تولید محتوای فایل. '
        'فقط محتوای فایل را به فارسی برگردان؛ بدون توضیح اضافه و بدون کد بلوک. '
        f'نوع سند: {kind}. عنوان را در محتوا منعکس کن اگر لازم است.'
    )
    safe_title = title or 'بدون عنوان'
    user_msg = f'عنوان: {safe_title}\nدرخواست:\n{prompt.strip()}'
    text, tokens, model = provider.chat_completion(system, user_msg, max_tokens=2000, temperature=0.4)
    if not text.strip():
        text = f'{safe_title}\n\n{prompt}'
    quota = consume_tokens(user, 'draft_mail', tokens, model, True, f'file:{safe_title[:60]}')
    return {
        'title': title or 'سند جدید',
        'content': text,
        'doc_type': kind,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }



# غلط‌های رایج فارسی (نمونه محلی وقتی API نیست)
COMMON_FA_FIXES = {
    'میشود': 'می‌شود',
    'میکند': 'می‌کند',
    'میکنم': 'می‌کنم',
    'میباشد': 'می‌باشد',
    'نمی شود': 'نمی‌شود',
    'نمی کند': 'نمی‌کند',
    'صورتجلسه': 'صورت‌جلسه',
    'اینده': 'آینده',
    'حتما': 'حتماً',
    'لطفا': 'لطفاً',
    'مثلا': 'مثلاً',
    'ضمنا': 'ضمناً',
    'سلام عرض': 'با سلام',
    'با عرض سلام': 'با سلام',
}


def proofread_text(user, text: str) -> dict:
    """غلط‌یابی املایی/نگارشی؛ خروجی: متن اصلاح‌شده + لیست خطاها با پیشنهاد."""
    ensure_quota(user)
    text = (text or '').strip()
    if len(text) < 2:
        return {'text': text, 'issues': [], 'tokens_used': 0, 'provider': 'none'}

    system = (
        'PROOFREAD | غلط‌یاب فارسی. '
        'فقط JSON معتبر برگردان با این شکل: '
        '{"corrected":"...","issues":[{"original":"...","suggestion":"...","reason":"..."}]} '
        'اگر غلطی نیست issues خالی باشد. فقط همان JSON بدون توضیح.'
    )
    raw, tokens, model = provider.chat_completion(system, text[:12000], max_tokens=1500, temperature=0.1)

    issues = []
    corrected = text
    import json
    import re
    try:
        # extract JSON block
        m = re.search(r'\{.*\}', raw, re.S)
        blob = m.group(0) if m else raw
        data = json.loads(blob)
        corrected = data.get('corrected') or text
        for item in data.get('issues') or []:
            if not isinstance(item, dict):
                continue
            orig = str(item.get('original') or '').strip()
            sug = str(item.get('suggestion') or '').strip()
            if orig and sug and orig != sug:
                issues.append({
                    'original': orig,
                    'suggestion': sug,
                    'reason': str(item.get('reason') or 'پیشنهاد اصلاح')[:120],
                })
    except Exception:
        # fallback محلی
        corrected = text
        for wrong, right in COMMON_FA_FIXES.items():
            if wrong in text and wrong != right:
                issues.append({'original': wrong, 'suggestion': right, 'reason': 'املای رایج'})
                corrected = corrected.replace(wrong, right)

    if not issues:
        for wrong, right in COMMON_FA_FIXES.items():
            if wrong in text and not any(i['original'] == wrong for i in issues):
                issues.append({'original': wrong, 'suggestion': right, 'reason': 'املای رایج'})
        for it in issues:
            if it['original'] in corrected:
                corrected = corrected.replace(it['original'], it['suggestion'])

    quota = consume_tokens(user, 'summarize', tokens, model, True, 'proofread')
    return {
        'text': corrected,
        'issues': issues,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }


def conference_document(user, transcript: str, doc_kind: str = 'minutes', title: str = 'جلسه') -> dict:
    """خروجی‌های ساخت‌یافته از متن جلسه: صورت‌جلسه، اقدامات، ایمیل، خلاصه اجرایی."""
    ensure_quota(user)
    kind_map = {
        'minutes': (
            'MEETING_MINUTES | صورت‌جلسه رسمی فارسی بنویس با بخش‌های: '
            'عنوان، تاریخ، حاضران (اگر معلوم نیست بنویس نامشخص)، موضوعات، تصمیمات، اقدامات و مسئول.'
        ),
        'actions': (
            'MEETING_ACTIONS | فقط فهرست اقدامات بعدی از روی رونوشت. '
            'هر مورد: اقدام، مسئول فرضی، مهلت پیشنهادی. بولت فارسی.'
        ),
        'executive': (
            'MEETING_EXEC | خلاصه اجرایی حداکثر ۸ خط برای مدیر.'
        ),
        'email': (
            'MEETING_EMAIL | یک ایمیل اداری فارسی به شرکت‌کنندگان جلسه: '
            'تشکر، خلاصه تصمیمات، اقدامات، بدون امضای انگلیسی.'
        ),
        'transcript_clean': (
            'TRANSCRIPT_CLEAN | رونوشت را مرتب و خوانا کن؛ جملات کامل، بدون پر کردن جعلی.'
        ),
    }
    system = kind_map.get(doc_kind, kind_map['minutes'])
    user_msg = f'عنوان: {title}\n\n{transcript[:16000]}'
    out, tokens, model = provider.chat_completion(system, user_msg, max_tokens=1600, temperature=0.25)
    quota = consume_tokens(user, 'meeting_summary', tokens, model, True, doc_kind)
    return {
        'text': out,
        'doc_kind': doc_kind,
        'tokens_used': tokens,
        'model': model,
        'remaining_tokens': quota.remaining(),
        'provider': 'remote' if provider.has_remote() else 'local',
    }
