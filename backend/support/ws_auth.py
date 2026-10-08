"""
Middleware برای احراز هویت WebSocket از طریق subprotocol.

فرمت مورد انتظار:
  subprotocols: ['access_token', '<JWT access token>']
یا برای desk:
  subprotocols: ['desk_token', '<device token>']

JWT را استخراج و user را در scope قرار می‌دهد.
"""
from urllib.parse import urlparse

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http.request import validate_host
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user(user_id):
    User = get_user_model()
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


def origin_allowed(scope) -> bool:
    """
    جلوگیری از Cross-Site WebSocket Hijacking.
    - بدون هدر Origin (کلاینت غیرمرورگری مثل agent) → مجاز؛ احراز هویت با توکن انجام می‌شود.
    - با Origin: باید در CORS_ALLOWED_ORIGINS باشد یا میزبانش در ALLOWED_HOSTS.
    """
    origin = None
    for name, value in scope.get('headers', []):
        if name == b'origin':
            origin = value.decode('latin1')
            break
    if not origin:
        return True
    if origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
        return True
    if origin in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
        return True
    host = urlparse(origin).hostname
    return bool(host) and validate_host(host, settings.ALLOWED_HOSTS)


class AccessTokenSubprotocolMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            if not origin_allowed(scope):
                await send({'type': 'websocket.close'})
                return
            subs = [
                s.decode('utf-8', errors='ignore') if isinstance(s, bytes) else s
                for s in scope.get('subprotocols', [])
            ]
            # توکن فقط از subprotocol (query string در لاگ‌ها نشت می‌کند)
            token = subs[1] if len(subs) >= 2 and subs[0] == 'access_token' else None

            scope = dict(scope)
            scope['user'] = AnonymousUser()
            if token:
                try:
                    access = AccessToken(token)
                    user_id = access.get('user_id')
                    if user_id:
                        scope['user'] = await get_user(user_id)
                except Exception:
                    scope['user'] = AnonymousUser()
            return await super().__call__(scope, receive, send)
        return await super().__call__(scope, receive, send)
