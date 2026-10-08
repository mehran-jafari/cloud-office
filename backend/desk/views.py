import re
import secrets
import string
from pathlib import Path
from urllib.parse import urlparse

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.http import HttpResponse
from django.http.request import validate_host
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import AddressBookEntry, DeskConference, DeskSession, Device
from .serializers import (
    AddressBookSerializer,
    DeskConferenceSerializer,
    DeskSessionSerializer,
    DevicePrivateSerializer,
    DevicePublicSerializer,
)


def device_from_request(request) -> Device | None:
    """توکن فقط از سرصفحه X-Desk-Token پذیرفته می‌شود — هرگز از query string
    (توکن در URL در لاگ سرور و تاریخچه مرورگر نشت می‌کند)."""
    token = request.headers.get('X-Desk-Token')
    if token:
        return Device.objects.filter(token=token).first()
    if request.user and request.user.is_authenticated:
        return Device.objects.filter(user=request.user).order_by('-last_seen').first()
    return None


class IceConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ice = list(getattr(settings, 'WEBRTC_ICE_SERVERS', [
            {'urls': 'stun:stun.l.google.com:19302'},
            {'urls': 'stun:stun1.l.google.com:19302'},
        ]))
        return Response({'iceServers': ice})


class RegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token') or request.headers.get('X-Desk-Token')
        hostname = str(request.data.get('hostname') or '')[:120]
        os_name = str(request.data.get('os_name') or '')[:80]
        alias = str(request.data.get('alias') or hostname or request.user.username)[:80]

        device = None
        if token:
            device = Device.objects.filter(token=token, user=request.user).first()
        if not device:
            device = Device.objects.filter(user=request.user).order_by('-last_seen').first()

        if device:
            device.hostname = hostname or device.hostname
            device.os_name = os_name or device.os_name
            if request.data.get('alias'):
                device.alias = alias
            device.last_seen = timezone.now()
            device.save()
        else:
            device = Device.objects.create(
                user=request.user,
                hostname=hostname,
                os_name=os_name,
                alias=alias,
            )
            device.set_password()
            device.save(update_fields=['password'])

        data = DevicePrivateSerializer(device).data
        if getattr(device, 'password_plain', ''):
            data['password_plain'] = device.password_plain
        return Response(data)


class MyDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device = device_from_request(request)
        if not device or device.user_id != request.user.id:
            return Response({'detail': 'دستگاهی ثبت نشده است؛ ابتدا register را صدا بزنید'}, status=404)
        return Response(DevicePrivateSerializer(device).data)

    def patch(self, request):
        device = device_from_request(request)
        if not device or device.user_id != request.user.id:
            return Response({'detail': 'دستگاه پیدا نشد'}, status=404)
        if 'alias' in request.data:
            device.alias = str(request.data.get('alias') or '')[:80]
        if request.data.get('rotate_password'):
            device.set_password()
        device.save()
        data = DevicePrivateSerializer(device).data
        if request.data.get('rotate_password'):
            data['password_plain'] = getattr(device, 'password_plain', '')
        return Response(data)


class LookupDeviceView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'desk_lookup'

    def get(self, request, desk_id):
        digits = ''.join(ch for ch in str(desk_id) if ch.isdigit())
        device = Device.objects.filter(desk_id=digits).first()
        if not device:
            return Response({'detail': 'شناسه پیدا نشد'}, status=404)
        return Response(DevicePublicSerializer(device).data)


class ConnectRemoteView(APIView):
    """درخواست اتصال به شناسه ۹ رقمی (شبیه AnyDesk)."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'desk_connect'

    def post(self, request):
        client = device_from_request(request)
        if not client or client.user_id != request.user.id:
            return Response({'detail': 'دستگاه ثبت نشده'}, status=400)

        target_id = ''.join(ch for ch in str(request.data.get('desk_id') or '') if ch.isdigit())
        password = str(request.data.get('password') or '')
        if len(target_id) != 9:
            return Response({'detail': 'شناسه باید ۹ رقم باشد'}, status=400)
        if target_id == client.desk_id:
            return Response({'detail': 'نمی‌توانید به خودتان وصل شوید'}, status=400)

        host = Device.objects.filter(desk_id=target_id).first()
        if not host:
            return Response({'detail': 'دستگاه مقصد پیدا نشد'}, status=404)
        password_ok = host.verify_password(password)
        if host.password and password and not password_ok:
            return Response({'detail': 'رمز اتصال نادرست است'}, status=403)

        session = DeskSession.objects.create(host=host, client=client, status='pending')
        AddressBookEntry.objects.update_or_create(
            owner=client, desk_id=target_id,
            defaults={'alias': host.alias or target_id, 'last_connected': timezone.now()},
        )

        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(
                f'desk_{host.desk_id}',
                {
                    'type': 'signal.message',
                    'payload': {
                        'type': 'incoming_session',
                        'session_key': session.session_key,
                        'from_desk_id': client.desk_id,
                        'from_alias': client.alias or client.hostname,
                        'password_ok': not host.password or password_ok,
                    },
                },
            )

        return Response(DeskSessionSerializer(session).data, status=201)


class SessionActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_key):
        action = str(request.data.get('action') or '').lower()
        device = device_from_request(request)
        session = DeskSession.objects.filter(session_key=session_key).select_related('host', 'client').first()
        if not session or not device:
            return Response({'detail': 'نشست پیدا نشد'}, status=404)

        is_host = session.host_id == device.id
        is_client = session.client_id == device.id
        if not (is_host or is_client):
            return Response({'detail': 'دسترسی ندارید'}, status=403)

        if action == 'accept' and is_host:
            session.status = 'active'
            session.save(update_fields=['status'])
            payload_type = 'session_accepted'
        elif action == 'reject' and is_host:
            session.status = 'rejected'
            session.ended_at = timezone.now()
            session.save(update_fields=['status', 'ended_at'])
            payload_type = 'session_rejected'
        elif action == 'end':
            session.status = 'ended'
            session.ended_at = timezone.now()
            session.save(update_fields=['status', 'ended_at'])
            payload_type = 'session_ended'
        else:
            return Response({'detail': 'عملیات نامعتبر'}, status=400)

        layer = get_channel_layer()
        if layer:
            for desk_id in {session.host.desk_id, session.client.desk_id}:
                async_to_sync(layer.group_send)(
                    f'desk_{desk_id}',
                    {
                        'type': 'signal.message',
                        'payload': {
                            'type': payload_type,
                            'session_key': session.session_key,
                            'status': session.status,
                        },
                    },
                )
        return Response(DeskSessionSerializer(session).data)


class AddressBookView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device = device_from_request(request)
        if not device:
            return Response([])
        qs = AddressBookEntry.objects.filter(owner=device).order_by('-last_connected', '-created_at')[:100]
        return Response(AddressBookSerializer(qs, many=True).data)

    def post(self, request):
        device = device_from_request(request)
        if not device:
            return Response({'detail': 'دستگاه ثبت نشده'}, status=400)
        desk_id = ''.join(ch for ch in str(request.data.get('desk_id') or '') if ch.isdigit())
        alias = str(request.data.get('alias') or desk_id)[:80]
        if len(desk_id) != 9:
            return Response({'detail': 'شناسه نامعتبر'}, status=400)
        entry, _ = AddressBookEntry.objects.update_or_create(
            owner=device, desk_id=desk_id, defaults={'alias': alias}
        )
        return Response(AddressBookSerializer(entry).data, status=201)


class ConferenceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device = device_from_request(request)
        if not device:
            return Response({'detail': 'دستگاه ثبت نشده'}, status=400)
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        while DeskConference.objects.filter(code=code).exists():
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        conf = DeskConference.objects.create(
            code=code,
            title=str(request.data.get('title') or 'ویدیوکنفرانس')[:120],
            host=device,
        )
        invitees = request.data.get('participant_ids') or []
        layer = get_channel_layer()
        for raw in invitees:
            desk_id = ''.join(ch for ch in str(raw) if ch.isdigit())
            if len(desk_id) != 9 or desk_id == device.desk_id:
                continue
            if layer:
                async_to_sync(layer.group_send)(
                    f'desk_{desk_id}',
                    {
                        'type': 'signal.message',
                        'payload': {
                            'type': 'conf_invite',
                            'code': conf.code,
                            'title': conf.title,
                            'from': device.desk_id,
                            'from_alias': device.alias,
                        },
                    },
                )
        return Response(DeskConferenceSerializer(conf).data, status=201)


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device = device_from_request(request)
        if not device:
            return Response([])
        from django.db.models import Q
        qs = DeskSession.objects.filter(Q(host=device) | Q(client=device)).select_related('host', 'client')[:40]
        return Response(DeskSessionSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# نصب‌کننده عامل Desk (ویندوز / مک / لینوکس)
# اسکریپت‌ها با آدرس سرور واقعی ساخته می‌شوند تا روی سیستم مقصد به localhost وصل نشوند.
# ---------------------------------------------------------------------------
AGENT_TEMPLATES_DIR = Path(__file__).resolve().parent / 'agent_templates'
AGENT_PLATFORMS = {
    'windows': ('install-windows.ps1', 'text/plain; charset=utf-8'),
    'macos': ('install-macos.sh', 'text/x-shellscript; charset=utf-8'),
    'linux': ('install-linux.sh', 'text/x-shellscript; charset=utf-8'),
}
_APP_URL_RE = re.compile(r'^https?://[A-Za-z0-9.-]+(:\d{1,5})?$')


def resolve_app_url(request) -> str:
    """آدرس پایه برنامه برای قرار گرفتن در اسکریپت؛ فقط مقادیر امن و مجاز."""
    configured = (getattr(settings, 'PUBLIC_APP_URL', '') or '').strip().rstrip('/')
    if configured and _APP_URL_RE.match(configured):
        return configured
    candidate = (request.query_params.get('app') or '').strip().rstrip('/')
    if candidate and _APP_URL_RE.match(candidate):
        host = urlparse(candidate).hostname or ''
        allowed = (
            candidate in getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            or candidate in getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
            or validate_host(host, settings.ALLOWED_HOSTS)
        )
        if allowed:
            return candidate
    return f"{request.scheme}://{request.get_host()}".rstrip('/')


class AgentInstallerView(APIView):
    """GET /api/desk/agent/<windows|macos|linux>/?app=<origin> — متن اسکریپت نصب."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'desk_lookup'

    def get(self, request, platform):
        entry = AGENT_PLATFORMS.get(platform)
        if not entry:
            return Response({'detail': 'پلتفرم نامعتبر است'}, status=status.HTTP_404_NOT_FOUND)
        filename, content_type = entry
        template = (AGENT_TEMPLATES_DIR / filename).read_text(encoding='utf-8')
        body = template.replace('__APP_URL__', resolve_app_url(request))
        if platform == 'windows':
            body = body.replace('\r\n', '\n').replace('\n', '\r\n')
        response = HttpResponse(body, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store'
        return response
