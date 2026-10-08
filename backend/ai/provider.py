"""لایه فراخوانی مدل — OpenAI-compatible یا fallback ساخت‌یافته محلی."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request


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
}


def _cfg():
    return {
        'api_key': os.getenv('AI_API_KEY', '').strip() or os.getenv('OPENAI_API_KEY', '').strip(),
        'base_url': (os.getenv('AI_BASE_URL', '') or 'https://api.openai.com/v1').rstrip('/'),
        'chat_model': os.getenv('AI_CHAT_MODEL', 'gpt-4o-mini'),
        'embed_model': os.getenv('AI_EMBED_MODEL', 'text-embedding-3-small'),
        'stt_model': os.getenv('AI_STT_MODEL', 'whisper-1'),
    }


def has_remote() -> bool:
    return bool(_cfg()['api_key'])


def _post_json(path: str, payload: dict, timeout: int = 90) -> dict:
    cfg = _cfg()
    url = f"{cfg['base_url']}{path}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {cfg['api_key']}",
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:400]
        raise RuntimeError(f'خطای سرویس AI ({e.code}): {body}') from e
    except Exception as e:
        raise RuntimeError(f'ارتباط با سرویس AI برقرار نشد: {e}') from e


def chat_completion(
    system: str,
    user: str,
    *,
    max_tokens: int = 1200,
    temperature: float = 0.35,
    timeout: int | None = None,
) -> tuple[str, int, str]:
    cfg = _cfg()
    if not cfg['api_key']:
        text = _local_chat(system, user)
        tokens = max(40, len(text) // 3)
        return text, tokens, 'local-fallback'

    result = _post_json('/chat/completions', {
        'model': cfg['chat_model'],
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }, timeout=timeout or 90)
    text = (result['choices'][0]['message']['content'] or '').strip()
    usage = result.get('usage') or {}
    tokens = int(usage.get('total_tokens') or max(40, (len(system) + len(user) + len(text)) // 4))
    return text, tokens, cfg['chat_model']


def _extract_field(blob: str, *keys: str) -> str:
    for key in keys:
        m = re.search(rf'{re.escape(key)}\s*[:：]\s*(.+)', blob, re.I | re.M)
        if m:
            return m.group(1).strip()
    return ''


def _local_chat(system: str, user: str) -> str:
    """الگوهای ساخت‌یافتهٔ فارسی وقتی کلید API نیست."""
    s = system
    u = user.strip()

    if 'PROOFREAD' in s:
        # local: apply simple fixes
        import json as _json
        corrected = u
        issues = []
        for w, r in COMMON_FA_FIXES.items():
            if w in corrected:
                issues.append({'original': w, 'suggestion': r, 'reason': 'املای رایج'})
                corrected = corrected.replace(w, r)
        return _json.dumps({'corrected': corrected, 'issues': issues}, ensure_ascii=False)

    if 'MEETING_MINUTES' in s or 'صورت‌جلسه' in s:
        return (
            f'صورت‌جلسه\nعنوان: جلسه\n\nموضوعات:\n• از روی رونوشت استخراج شد\n\n'
            f'تصمیمات:\n• نیازمند تأیید\n\nاقدامات:\n• پیگیری موارد باز\n\n'
            f'متن مبنا:\n{u[:600]}'
        )
    if 'MEETING_ACTIONS' in s:
        lines = [ln.strip() for ln in u.splitlines() if len(ln.strip()) > 10][:8]
        body = '\n'.join(f'• {ln[:100]} — مسئول: نامشخص — مهلت: هفته آینده' for ln in lines) or '• اقدامی استخراج نشد'
        return 'اقدامات جلسه:\n' + body
    if 'MEETING_EMAIL' in s:
        return (
            'با سلام و احترام،\n\n'
            'خلاصه تصمیمات و اقدامات جلسه به پیوست ذهنیت شما رسید. '
            'لطفاً موارد مربوط به خود را پیگیری فرمایید.\n\nبا سپاس'
        )
    if 'MEETING_EXEC' in s or 'TRANSCRIPT_CLEAN' in s:
        lines = [ln.strip() for ln in u.splitlines() if ln.strip()][:10]
        return '\n'.join(f'• {ln[:120]}' for ln in lines) or u[:500]

    if 'CREATE_FILE' in s or 'تولید محتوای فایل' in s:
        title = _extract_field(u, 'عنوان', 'title') or 'سند جدید'
        req = _extract_field(u, 'درخواست', 'prompt') or u
        lines = [ln.strip() for ln in req.splitlines() if ln.strip()]
        body = '\n'.join(f'• {ln}' for ln in lines[:15]) if lines else req
        return (
            f'{title}\n'
            f'{"=" * min(40, max(8, len(title)))}\n\n'
            f'{body}\n\n'
            f'— تولیدشده توسط دستیار دفتر ابری (حالت محلی)'
        )

    if 'DRAFT_MAIL' in s or 'پیش‌نویس نامه' in s:
        subject = _extract_field(u, 'موضوع', 'subject') or 'بدون موضوع'
        notes = _extract_field(u, 'نکات', 'notes') or u
        tone = _extract_field(u, 'لحن', 'tone') or 'formal'
        notes_lines = [ln.strip('•- \t') for ln in notes.splitlines() if ln.strip()]
        if not notes_lines:
            notes_lines = [notes[:300]]
        bullets = '\n'.join(f'• {ln}' for ln in notes_lines[:12])
        if tone in ('short', 'کوتاه'):
            return (
                f'موضوع: {subject}\n\n'
                f'با سلام؛\n'
                f'به استحضار می‌رساند:\n{bullets}\n\n'
                f'با سپاس'
            )
        if tone in ('friendly', 'دوستانه'):
            return (
                f'موضوع: {subject}\n\n'
                f'سلام و وقت بخیر،\n\n'
                f'امیدوارم حال‌تان خوب باشد. در ادامه نکات مربوط به «{subject}» آمده است:\n'
                f'{bullets}\n\n'
                f'اگر نکته‌ای مد نظرتان است بفرمایید تا اصلاح کنم.\n\n'
                f'ارادتمند'
            )
        return (
            f'موضوع: {subject}\n\n'
            f'با سلام و احترام،\n\n'
            f'احتراماً در خصوص «{subject}» به استحضار می‌رساند:\n'
            f'{bullets}\n\n'
            f'خواهشمند است دستور فرمایید.\n\n'
            f'با تقدیم احترام'
        )

    if 'SUMMARIZE_SUPPORT' in s or 'خلاصه پشتیبانی' in s:
        lines = [ln.strip() for ln in u.splitlines() if ln.strip()]
        user_msgs = [ln for ln in lines if ln.startswith('کاربر') or 'user' in ln.lower()]
        staff_msgs = [ln for ln in lines if 'پشتیبان' in ln or 'staff' in ln.lower()]
        return (
            'خلاصه تیکت پشتیبانی\n'
            f'• تعداد پیام‌ها: {len(lines)}\n'
            f'• پیام‌های کاربر: {len(user_msgs)}\n'
            f'• پاسخ‌های پشتیبانی: {len(staff_msgs)}\n'
            f'• آخرین پیام: {(lines[-1] if lines else "—")[:160]}\n'
            f'• وضعیت پیشنهادی: {"نیازمند پیگیری" if len(staff_msgs) == 0 else "در حال رسیدگی"}'
        )

    if 'SUMMARIZE' in s or 'خلاصه' in s:
        lines = [ln.strip() for ln in re.split(r'[\n.؟!]', u) if len(ln.strip()) > 15]
        if not lines:
            lines = [u[:120]] if u else ['متنی برای خلاصه نبود.']
        bullets = '\n'.join(f'• {ln[:140]}' for ln in lines[:7])
        return f'خلاصه نکات کلیدی:\n{bullets}'

    if 'SUPPORT_REPLY' in s or 'پاسخ پشتیبانی' in s:
        last_user = ''
        for ln in reversed(u.splitlines()):
            if 'کاربر' in ln or ln.strip():
                last_user = ln.strip()
                break
        return (
            'با سلام و احترام؛\n\n'
            'پیام شما دریافت شد و در صف بررسی قرار گرفت. '
            f'در ارتباط با موضوع مطرح‌شده'
            + (f' («{last_user[:80]}»)' if last_user else '')
            + ' نتیجه در اولین فرصت از همین گفتگو اعلام می‌شود.\n\n'
            'در صورت داشتن پیوست یا جزئیات بیشتر، همین‌جا ارسال فرمایید.\n\n'
            'با سپاس\nواحد پشتیبانی'
        )

    if 'MEETING_SUMMARY' in s or 'خلاصه جلسه' in s:
        title = _extract_field(u, 'عنوان', 'title') or 'جلسه'
        lines = [ln.strip() for ln in u.splitlines() if ln.strip() and not ln.startswith('عنوان')]
        topics = lines[:5] or ['موضوعات از رونوشت استخراج نشد']
        return (
            f'خلاصه جلسه: {title}\n\n'
            f'۱) موضوعات مطرح‌شده:\n' + '\n'.join(f'   • {t[:120]}' for t in topics) + '\n\n'
            f'۲) تصمیمات:\n   • نیاز به تأیید شرکت‌کنندگان دارد.\n\n'
            f'۳) اقدامات بعدی:\n   • پیگیری موارد باز تا جلسه بعد\n'
            f'   • مستندسازی نتایج در مکاتبات\n\n'
            f'۴) یادداشت: این خلاصه با موتور محلی تولید شده؛ با AI_API_KEY دقیق‌تر می‌شود.'
        )

    return u[:800] if u else 'خروجی خالی'


def embed_texts(texts: list[str]) -> tuple[list[list[float]], int, str]:
    cfg = _cfg()
    cleaned = [(t or '').strip() or ' ' for t in texts]
    if not cfg['api_key']:
        vectors = [_local_embed(t) for t in cleaned]
        return vectors, max(8, sum(len(t) for t in cleaned) // 5), 'local-hash-embed'

    result = _post_json('/embeddings', {
        'model': cfg['embed_model'],
        'input': cleaned,
    })
    vectors = [item['embedding'] for item in sorted(result['data'], key=lambda x: x['index'])]
    usage = result.get('usage') or {}
    tokens = int(usage.get('total_tokens') or 40)
    return vectors, tokens, cfg['embed_model']


def _local_embed(text: str, dims: int = 96) -> list[float]:
    """بردار مبتنی بر توکن‌های فارسی/انگلیسی با وزن تکرار."""
    tokens = re.findall(r'[\w\u0600-\u06FF]+', (text or '').lower())
    vec = [0.0] * dims
    if not tokens:
        return vec
    for i, tok in enumerate(tokens):
        h = hashlib.sha256(f'{tok}:{i // 3}'.encode('utf-8')).digest()
        weight = 1.0 + math.log(1 + tokens.count(tok))
        for d in range(dims):
            vec[d] += weight * ((h[d % len(h)] / 255.0) - 0.5)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def transcribe_audio(file_bytes: bytes, filename: str = 'audio.webm') -> tuple[str, int, str]:
    cfg = _cfg()
    if not cfg['api_key']:
        return (
            'تبدیل گفتار به متن در حالت محلی فعال نیست.\n'
            'برای رونوشت دقیق، AI_API_KEY و مدل Whisper را در .env تنظیم کنید.\n'
            f'(فایل «{filename}» با حجم {len(file_bytes):,} بایت دریافت شد.)',
            15,
            'local-stt-unavailable',
        )

    import uuid
    boundary = f'----CloudOffice{uuid.uuid4().hex}'
    parts = []
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{cfg["stt_model"]}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'.encode()
        + file_bytes
        + b'\r\n'
    )
    parts.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(parts)

    url = f"{cfg['base_url']}/audio/transcriptions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Authorization': f"Bearer {cfg['api_key']}",
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise RuntimeError(f'تبدیل گفتار ناموفق: {e}') from e
    text = (result.get('text') or '').strip()
    if not text:
        raise RuntimeError('سرویس STT متنی برنگرداند.')
    tokens = max(25, len(text) // 3)
    return text, tokens, cfg['stt_model']
