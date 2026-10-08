"""ارسال پیامک / پیام‌رسان — فعلاً لاگ؛ با API واقعی قابل اتصال است."""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_user(user, text: str, channels: list | None = None):
    try:
        profile = user.profile
    except Exception:
        return
    channels = channels or []
    if not channels:
        if profile.notify_sms:
            channels.append('sms')
        if profile.notify_telegram:
            channels.append('telegram')
        if profile.notify_bale:
            channels.append('bale')
        if profile.notify_eitaa:
            channels.append('eitaa')
    phone = profile.phone
    for ch in channels:
        if ch == 'sms' and phone:
            logger.info('[SMS stub] to=%s msg=%s', phone, text[:120])
            # integrate Kavenegar/Ghasedak here
        elif ch == 'telegram' and profile.telegram_chat_id:
            logger.info('[Telegram stub] chat=%s msg=%s', profile.telegram_chat_id, text[:120])
        elif ch == 'bale' and profile.bale_chat_id:
            logger.info('[Bale stub] chat=%s msg=%s', profile.bale_chat_id, text[:120])
        elif ch == 'eitaa' and profile.eitaa_chat_id:
            logger.info('[Eitaa stub] chat=%s msg=%s', profile.eitaa_chat_id, text[:120])
