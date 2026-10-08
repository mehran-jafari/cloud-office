"""اعلان درون‌برنامه‌ای + ایمیل اختیاری."""
from __future__ import annotations

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags

from .models import Notification

logger = logging.getLogger(__name__)


def push_notification(user, kind: str, title: str, body: str = '', link: str = '', *, send_email: bool = False):
    """ایجاد اعلان درون‌برنامه‌ای و در صورت نیاز ارسال ایمیل."""
    if not user:
        return None
    notif = Notification.objects.create(
        user=user,
        kind=kind,
        title=title[:200],
        body=(body or '')[:500],
        link=(link or '')[:200],
    )
    if send_email or getattr(settings, 'NOTIFY_EMAIL_ON_ALL', False):
        _send_email_notification(user, title, body, link)
    return notif


def _send_email_notification(user, title: str, body: str, link: str = '') -> bool:
    email = getattr(user, 'email', None) or ''
    if not email or not getattr(settings, 'EMAIL_HOST', ''):
        return False
    subject = f"[Cloud Office] {title}"
    public_url = getattr(settings, 'PUBLIC_APP_URL', '').rstrip('/')
    full_link = ''
    if link:
        full_link = link if link.startswith('http') else f"{public_url}{link}"
    text = body or title
    if full_link:
        text = f"{text}\n\nلینک: {full_link}"
    html = f"<p>{strip_tags(body or title)}</p>"
    if full_link:
        html += f'<p><a href="{full_link}">{full_link}</a></p>'
    try:
        send_mail(
            subject=subject,
            message=text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cloud-office.local'),
            recipient_list=[email],
            html_message=html,
            fail_silently=True,
        )
        return True
    except Exception:
        logger.exception("Failed to send notification email to %s", email)
        return False
