from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.notifications import notify_user
from files.notifications import push_notification
from support.permissions import CanReplySupport, role_for

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from . import services

MAX_BODY_LENGTH = 5000
STAFF_ROLES = {'owner', 'admin', 'support'}


class PostScopedThrottle(ScopedRateThrottle):
    """فقط درخواست‌های POST (ساخت مکالمه/پیام) محدود می‌شوند؛ polling فرانت (GET) نه."""

    def allow_request(self, request, view):
        if request.method != 'POST':
            return True
        return super().allow_request(request, view)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PostScopedThrottle]
    throttle_scope = 'support_msg'

    def get(self, request):
        qs = Conversation.objects.select_related(
            'user', 'assigned_agent'
        ).prefetch_related('messages__sender')
        if role_for(request.user) not in {'owner', 'admin', 'support'}:
            qs = qs.filter(user=request.user)
        # heartbeat حضور برای پشتیبان‌ها
        if role_for(request.user) in {'owner', 'admin', 'support'}:
            services.touch_support_presence(request.user)
        return Response(
            ConversationSerializer(qs.order_by('-updated_at')[:100], many=True).data
        )

    def post(self, request):
        subject = str(request.data.get('subject') or 'درخواست پشتیبانی').strip()[:200] or 'درخواست پشتیبانی'
        body = str(request.data.get('body') or '').strip()
        if len(body) > MAX_BODY_LENGTH:
            return Response({'detail': 'متن پیام حداکثر ۵۰۰۰ نویسه است'}, status=400)
        conversation = Conversation.objects.create(user=request.user, subject=subject)
        info = {}
        if body:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
                is_staff_reply=False,
            )
            info = services.process_new_user_message(conversation, message)
        else:
            services.notify_agents_about_conversation(conversation, kind='new_message')
        data = ConversationSerializer(conversation).data
        data['pipeline'] = info
        return Response(data, status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        qs = Conversation.objects.select_related(
            'user', 'assigned_agent'
        ).prefetch_related('messages__sender')
        if role_for(request.user) not in {'owner', 'admin', 'support'}:
            qs = qs.filter(user=request.user)
        return get_object_or_404(qs, pk=pk)

    def get(self, request, pk):
        if role_for(request.user) in {'owner', 'admin', 'support'}:
            services.touch_support_presence(request.user)
        return Response(ConversationSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk):
        """بستن مکالمه یا تغییر وضعیت توسط پشتیبان/ادمین."""
        conversation = self.get_object(request, pk)
        if role_for(request.user) not in {'owner', 'admin', 'support'}:
            if conversation.user_id != request.user.id:
                return Response({'detail': 'دسترسی ندارید'}, status=403)
        status_val = str(request.data.get('status') or '').strip()
        is_staff = role_for(request.user) in STAFF_ROLES
        allowed = {'closed', 'open', 'waiting_agent', 'waiting_user'} if is_staff else {'closed', 'open'}
        if status_val in allowed:
            conversation.status = status_val
            if status_val in {'closed', 'waiting_user'}:
                conversation.next_escalate_at = None
            else:
                # بازگشایی/انتظار پشتیبان: تایمر escalation دوباره فعال شود
                conversation.next_escalate_at = timezone.now() + services.ESCALATION_AFTER
            conversation.save(update_fields=['status', 'next_escalate_at', 'updated_at'])
        return Response(ConversationSerializer(conversation).data)


class ConversationMessageView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PostScopedThrottle]
    throttle_scope = 'support_msg'

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        role = role_for(request.user)
        has_staff_role = role in STAFF_ROLES or request.user.is_staff or request.user.is_superuser
        is_owner = conversation.user_id == request.user.id
        # پشتیبان وقتی در تیکت خودش می‌نویسد، پیام «کاربر» است نه «پاسخ پشتیبان»
        is_staff = has_staff_role and not is_owner

        if not is_staff and not is_owner:
            return Response({'detail': 'دسترسی ندارید'}, status=403)

        body = str(request.data.get('body') or '').strip()
        if not body:
            return Response({'detail': 'متن پیام الزامی است'}, status=400)
        if len(body) > MAX_BODY_LENGTH:
            return Response({'detail': 'متن پیام حداکثر ۵۰۰۰ نویسه است'}, status=400)

        if is_staff:
            # پاسخ پشتیبان فقط با مجوز صریح can_reply (برای همه نقش‌ها، از جمله مالک)
            if not CanReplySupport().has_permission(request, self):
                return Response({'detail': CanReplySupport.message}, status=403)

            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
                is_staff_reply=True,
                is_ai=False,
            )
            services.process_agent_message(conversation, request.user, message)
            try:
                notify_user(conversation.user, f'پاسخ پشتیبانی: {body[:80]}')
                push_notification(
                    conversation.user,
                    'support',
                    'پاسخ پشتیبانی',
                    body=body[:120],
                    link=f'/support/{conversation.pk}',
                )
            except Exception:
                pass
            return Response(MessageSerializer(message).data, status=201)

        # پیام کاربر
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=body,
            is_staff_reply=False,
        )
        info = services.process_new_user_message(conversation, message)
        data = MessageSerializer(message).data
        data['pipeline'] = info
        return Response(data, status=201)


class SupportPresenceView(APIView):
    """heartbeat حضور پشتیبان (هر ۳۰–۶۰ ثانیه از فرانت)؛ فقط کاربران دارای مجوز پاسخ."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not services.can_agent_reply(request.user):
            return Response({'detail': 'مجوز پاسخ‌گویی پشتیبانی فعال نیست.'}, status=403)
        from accounts.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.support_last_seen = timezone.now()
        fields = ['support_last_seen', 'updated_at']
        if 'online' in request.data:
            raw = request.data.get('online')
            profile.is_support_online = raw if isinstance(raw, bool) else str(raw).lower() in {'1', 'true', 'yes', 'on'}
            fields.append('is_support_online')
        profile.save(update_fields=fields)
        return Response({'ok': True, 'is_support_online': profile.is_support_online})


class SupportEscalationRunView(APIView):
    """اجرای دستی/زمان‌بندی‌شده escalation (ادمین)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if role_for(request.user) not in {'owner', 'admin'} and not request.user.is_superuser:
            return Response({'detail': 'فقط ادمین'}, status=403)
        result = services.run_escalations()
        return Response(result)


class SupportPerformanceReportView(APIView):
    """گزارش امتیاز و فعالیت پشتیبان‌ها."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if role_for(request.user) not in {'owner', 'admin'} and not request.user.is_superuser:
            return Response({'detail': 'فقط ادمین'}, status=403)
        try:
            days = int(request.query_params.get('days') or 30)
        except ValueError:
            days = 30
        days = max(1, min(365, days))
        rows = services.agent_performance_report(days=days)
        return Response({'days': days, 'agents': rows})
