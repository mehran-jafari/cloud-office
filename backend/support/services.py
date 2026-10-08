"""
منطق پشتیبانی پیشرفته:
- تشخیص پشتیبان آنلاین واقعی (فلگ + last_seen < ۵ دقیقه)
- اعلان آفلاین به پیام‌رسان‌ها با cooldown
- escalation بعد از ۱۵ دقیقه بدون پاسخ
- پاسخ خودکار AI وقتی پشتیبان در دسترس نیست
- متریک‌های امتیازدهی برای ادمین
"""
from __future__ import annotations

import logging
from datetime import timedelta
from statistics import mean

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.models import SupportAgentPermission, UserProfile
from accounts.notifications import notify_user
from files.notifications import push_notification

from .models import Conversation, Message, SupportAlertLog

User = get_user_model()
logger = logging.getLogger(__name__)

ONLINE_WINDOW = timedelta(minutes=5)
ESCALATION_AFTER = timedelta(minutes=15)
OFFLINE_COOLDOWN = timedelta(minutes=12)
ADMIN_DELAY_AFTER = timedelta(minutes=30)
PRESENCE_WRITE_INTERVAL = timedelta(seconds=30)
MAX_ESCALATIONS = 5
ACTIVE_ESCALATION_STATUSES = ['waiting_agent', 'escalated', 'open']


def touch_support_presence(user) -> None:
    """heartbeat حضور پشتیبان."""
    if not user or not user.is_authenticated:
        return
    profile, _ = UserProfile.objects.get_or_create(user=user)
    now = timezone.now()
    # از نوشتن در هر poll (هر ۸ ثانیه) جلوگیری می‌کنیم
    if profile.support_last_seen and now - profile.support_last_seen < PRESENCE_WRITE_INTERVAL:
        return
    profile.support_last_seen = now
    profile.save(update_fields=['support_last_seen', 'updated_at'])


def can_agent_reply(user) -> bool:
    """مجوز صریح پاسخ‌گویی (همان قاعده CanReplySupport)."""
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_active:
        return False
    return SupportAgentPermission.objects.filter(user=user, can_reply=True).exists()


def is_agent_effectively_online(profile: UserProfile) -> bool:
    if not profile.is_support_online:
        return False
    if not profile.support_last_seen:
        return False
    return profile.support_last_seen >= timezone.now() - ONLINE_WINDOW


def get_online_agents():
    # فقط پشتیبانی که هم آنلاین است و هم مجوز پاسخ دارد
    now = timezone.now()
    qs = UserProfile.objects.filter(
        is_support_online=True,
        support_last_seen__gte=now - ONLINE_WINDOW,
        user__is_active=True,
        user__support_permission__can_reply=True,
    ).select_related('user')
    return list(qs)


def get_eligible_agents():
    """پشتیبان‌های دارای مجوز پاسخ (آنلاین یا آفلاین)."""
    perms = SupportAgentPermission.objects.filter(can_reply=True, user__is_active=True).select_related('user')
    agents = []
    for perm in perms:
        profile, _ = UserProfile.objects.get_or_create(user=perm.user)
        agents.append((perm.user, profile))
    # مالک/ادمین را هم به‌عنوان پشتیبان در نظر بگیر اگر can_reply ندارند ولی staff هستند
    return agents


def _already_alerted(conversation_id: int, kind: str, within: timedelta, agent_id=None) -> bool:
    since = timezone.now() - within
    qs = SupportAlertLog.objects.filter(
        conversation_id=conversation_id, kind=kind, sent_at__gte=since
    )
    if agent_id:
        qs = qs.filter(agent_id=agent_id)
    return qs.exists()


def _log_alert(conversation, kind: str, agent=None, channel: str = ''):
    SupportAlertLog.objects.create(
        conversation=conversation,
        agent=agent,
        channel=channel or '',
        kind=kind,
    )


def notify_agents_about_conversation(conversation: Conversation, kind: str = 'new_message'):
    """اعلان به پشتیبان‌ها: اول آنلاین‌ها، وگرنه broadcast آفلاین با cooldown."""
    online = get_online_agents()
    preview = ''
    last_msg = conversation.messages.order_by('-created_at').first()
    if last_msg:
        preview = (last_msg.body or '')[:100]

    title = f'پشتیبانی #{conversation.pk}'
    body = f'{conversation.subject}: {preview}' if preview else conversation.subject
    link = f'/support/{conversation.pk}'

    if online:
        for prof in online:
            push_notification(prof.user, 'support', title, body=body, link=link)
            notify_user(
                prof.user,
                f'پیام پشتیبانی جدید از {conversation.user.get_username()}: {preview}',
            )
            _log_alert(conversation, kind, agent=prof.user, channel='inapp')
        return {'mode': 'online', 'count': len(online)}

    # آفلاین: با cooldown
    if kind != 'escalation' and _already_alerted(conversation.pk, 'offline_broadcast', OFFLINE_COOLDOWN):
        return {'mode': 'offline_skipped_cooldown', 'count': 0}

    agents = get_eligible_agents()
    sent = 0
    for user, profile in agents:
        if not getattr(profile, 'notify_support_offline', True):
            continue
        channels = []
        if profile.notify_telegram and profile.telegram_chat_id:
            channels.append('telegram')
        if profile.notify_bale and profile.bale_chat_id:
            channels.append('bale')
        if profile.notify_eitaa and profile.eitaa_chat_id:
            channels.append('eitaa')
        if profile.notify_sms and profile.phone:
            channels.append('sms')

        push_notification(user, 'support', title, body=body, link=link)
        if channels:
            notify_user(
                user,
                f'[آفلاین] درخواست پشتیبانی #{conversation.pk} از {conversation.user.get_username()}: {preview}\n{link}',
                channels=channels,
            )
            for ch in channels:
                _log_alert(conversation, 'offline_broadcast', agent=user, channel=ch)
        else:
            _log_alert(conversation, 'offline_broadcast', agent=user, channel='inapp')
        sent += 1

    return {'mode': 'offline_broadcast', 'count': sent}


def try_ai_auto_reply(conversation: Conversation, user_message: str) -> dict | None:
    """
    اگر هیچ پشتیبان آنلاینی نباشد، AI تلاش می‌کند جواب بدهد.
    خروجی: dict با text و confidence یا None اگر نباید AI جواب دهد.
    """
    # اگر یک انسان قبلاً در این مکالمه پاسخ داده، AI وسط گفتگو دخالت نمی‌کند
    if conversation.last_agent_message_at:
        return None
    online = get_online_agents()
    if online:
        return None

    from ai.services import auto_support_answer

    # تاریخچه کوتاه مکالمه برای context
    history = list(
        conversation.messages.order_by('-created_at')[:8]
    )
    history.reverse()
    lines = []
    for m in history:
        who = 'AI' if m.is_ai else ('پشتیبان' if m.is_staff_reply else 'کاربر')
        lines.append(f'{who}: {m.body}')
    context = '\n'.join(lines)

    try:
        result = auto_support_answer(
            conversation.user,
            user_message=user_message,
            conversation_context=context,
            subject=conversation.subject,
        )
    except Exception as e:
        logger.warning('support.auto_reply_failed conversation=%s error=%s', conversation.pk, e)
        return {
            'text': (
                'متأسفانه در حال حاضر پشتیبان آنلاین در دسترس نیست. '
                'پیام شما ثبت شد و به‌محض حضور کارشناس پاسخ داده می‌شود.'
            ),
            'confidence': 0.0,
            'needs_human': True,
            'error': str(e)[:120],
        }

    return result


def apply_ai_reply(conversation: Conversation, ai_result: dict) -> Message | None:
    text = (ai_result.get('text') or '').strip()
    if not text:
        return None
    needs_human = bool(ai_result.get('needs_human'))
    confidence = float(ai_result.get('confidence') or 0)

    msg = Message.objects.create(
        conversation=conversation,
        sender=None,
        body=text,
        is_staff_reply=True,
        is_ai=True,
    )
    conversation.ai_handled = True
    conversation.ai_confidence = confidence
    if needs_human:
        conversation.status = 'waiting_agent'
        # همچنان escalation زمان‌بندی شود
        if not conversation.next_escalate_at:
            conversation.next_escalate_at = timezone.now() + ESCALATION_AFTER
    else:
        conversation.status = 'ai_handling'
        # AI جواب کامل داده؛ منتظر کاربر می‌مانیم. اگر کاربر دوباره پیام داد، mark_user_message تایمر را برمی‌گرداند.
        conversation.next_escalate_at = None
    conversation.save(update_fields=[
        'ai_handled', 'ai_confidence', 'status', 'next_escalate_at', 'updated_at',
    ])

    try:
        notify_user(conversation.user, f'پاسخ خودکار پشتیبانی: {text[:80]}')
        push_notification(
            conversation.user,
            'support',
            'پاسخ خودکار پشتیبانی',
            body=text[:120],
            link=f'/support/{conversation.pk}',
        )
    except Exception:
        logger.exception('support.ai_reply_notify_failed conversation=%s', conversation.pk)
    return msg


def process_new_user_message(conversation: Conversation, message: Message) -> dict:
    """بعد از ثبت پیام کاربر فراخوانی شود. خطای AI/اعلان هرگز نباید ثبت پیام را خراب کند."""
    conversation.mark_user_message()
    info = {'ai': None, 'notify': None}

    ai_result = None
    try:
        ai_result = try_ai_auto_reply(conversation, message.body)
        if ai_result:
            ai_msg = apply_ai_reply(conversation, ai_result)
            info['ai'] = {
                'replied': bool(ai_msg),
                'confidence': ai_result.get('confidence'),
                'needs_human': ai_result.get('needs_human'),
            }
    except Exception:
        logger.exception('support.ai_pipeline_failed conversation=%s', conversation.pk)
        ai_result = {'needs_human': True}

    # اگر AI جواب نداد یا گفت نیاز به انسان است، حتماً به پشتیبان‌ها خبر بده
    if not ai_result or ai_result.get('needs_human'):
        try:
            info['notify'] = notify_agents_about_conversation(conversation, kind='new_message')
        except Exception:
            logger.exception('support.notify_failed conversation=%s', conversation.pk)

    return info


def process_agent_message(conversation: Conversation, agent, message: Message) -> None:
    conversation.mark_agent_message(agent)
    touch_support_presence(agent)


def run_escalations(limit: int = 50) -> dict:
    """
    escalation مکالماتی که next_escalate_at گذشته و هنوز پاسخ انسانی نگرفته‌اند.
    مکالمات ai_handling (AI پاسخ داده و منتظر کاربر است) escalate نمی‌شوند.
    حداکثر MAX_ESCALATIONS بار برای هر مکالمه.
    """
    now = timezone.now()
    qs = list(Conversation.objects.filter(
        next_escalate_at__lte=now,
        status__in=ACTIVE_ESCALATION_STATUSES,
    ).order_by('next_escalate_at')[:limit])

    escalated = 0
    admin_notified = 0

    for conv in qs:
        # اگر در این فاصله پاسخ انسانی آمده، رد شو
        if conv.last_agent_message_at and conv.last_user_message_at:
            if conv.last_agent_message_at >= conv.last_user_message_at:
                conv.next_escalate_at = None
                conv.save(update_fields=['next_escalate_at', 'updated_at'])
                continue

        conv.escalation_count = (conv.escalation_count or 0) + 1
        conv.status = 'escalated'
        conv.next_escalate_at = (
            now + ESCALATION_AFTER if conv.escalation_count < MAX_ESCALATIONS else None
        )
        conv.save(update_fields=['escalation_count', 'status', 'next_escalate_at', 'updated_at'])

        try:
            if not _already_alerted(conv.pk, 'escalation', OFFLINE_COOLDOWN):
                notify_agents_about_conversation(conv, kind='escalation')
                _log_alert(conv, 'escalation')
                escalated += 1
        except Exception:
            logger.exception('support.escalation_notify_failed conversation=%s', conv.pk)

        # تأخیر بالا → ادمین
        if conv.last_user_message_at and (now - conv.last_user_message_at) >= ADMIN_DELAY_AFTER:
            if not _already_alerted(conv.pk, 'admin_delay', timedelta(hours=1)):
                owners = User.objects.filter(
                    Q(is_superuser=True) | Q(access_role__role__in=['owner', 'admin']),
                    is_active=True,
                ).distinct()[:10]
                for u in owners:
                    push_notification(
                        u,
                        'support',
                        f'تأخیر پشتیبانی #{conv.pk}',
                        body=f'بیش از ۳۰ دقیقه بدون پاسخ انسانی — escalation={conv.escalation_count}',
                        link=f'/support/{conv.pk}',
                    )
                    _log_alert(conv, 'admin_delay', agent=u, channel='inapp')
                admin_notified += 1

    return {'escalated': escalated, 'admin_notified': admin_notified}


def agent_performance_report(days: int = 30) -> list[dict]:
    """گزارش ریز فعالیت پشتیبان‌ها برای امتیازدهی."""
    since = timezone.now() - timedelta(days=days)
    agents = get_eligible_agents()
    # همچنین کسانی که قبلاً پاسخ staff داده‌اند
    responder_ids = set(
        Message.objects.filter(
            is_staff_reply=True, is_ai=False, created_at__gte=since, sender_id__isnull=False
        ).values_list('sender_id', flat=True)
    )
    agent_map = {u.id: (u, p) for u, p in agents}
    for uid in responder_ids:
        if uid not in agent_map:
            try:
                u = User.objects.get(pk=uid)
                p, _ = UserProfile.objects.get_or_create(user=u)
                agent_map[uid] = (u, p)
            except User.DoesNotExist:
                pass

    rows = []
    for uid, (user, profile) in agent_map.items():
        msgs = Message.objects.filter(
            sender=user, is_staff_reply=True, is_ai=False, created_at__gte=since
        )
        reply_count = msgs.count()
        conv_ids = set(msgs.values_list('conversation_id', flat=True))
        assigned = Conversation.objects.filter(
            Q(assigned_agent=user) | Q(id__in=conv_ids),
            updated_at__gte=since,
        )
        assigned_count = assigned.count()

        # زمان اولین پاسخ روی مکالماتی که او اولین پاسخ‌دهنده بوده
        first_responses = Conversation.objects.filter(
            assigned_agent=user,
            first_agent_response_at__isnull=False,
            created_at__gte=since,
        )
        fr_seconds = []
        for c in first_responses:
            if c.last_user_message_at and c.first_agent_response_at:
                # تقریبی: از ساخته شدن تا اولین پاسخ
                delta = (c.first_agent_response_at - c.created_at).total_seconds()
                if delta >= 0:
                    fr_seconds.append(delta)

        avg_first_response = mean(fr_seconds) if fr_seconds else None

        escalations_on_them = Conversation.objects.filter(
            assigned_agent=user, escalation_count__gt=0, updated_at__gte=since
        ).count()

        # آنلاین بودن تقریبی از alert logs و last_seen
        online_now = is_agent_effectively_online(profile)

        # امتیاز ساده ۰–۱۰۰
        score = 50.0
        score += min(30, reply_count * 2)
        if avg_first_response is not None:
            if avg_first_response <= 300:
                score += 15
            elif avg_first_response <= 900:
                score += 8
            elif avg_first_response > 1800:
                score -= 10
        score -= min(25, escalations_on_them * 5)
        if online_now:
            score += 5
        score = max(0, min(100, score))

        rows.append({
            'user_id': user.id,
            'username': user.get_username(),
            'full_name': user.get_full_name() or user.get_username(),
            'is_online_now': online_now,
            'support_last_seen': profile.support_last_seen.isoformat() if profile.support_last_seen else None,
            'reply_count': reply_count,
            'conversations_touched': assigned_count,
            'avg_first_response_seconds': round(avg_first_response, 1) if avg_first_response is not None else None,
            'escalations': escalations_on_them,
            'score': round(score, 1),
        })

    rows.sort(key=lambda r: (-r['score'], -r['reply_count']))
    return rows
