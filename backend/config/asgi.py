import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter
from support.routing import websocket_urlpatterns as support_ws
from desk.routing import websocket_urlpatterns as desk_ws
websocket_urlpatterns = support_ws + desk_ws
from support.ws_auth import AccessTokenSubprotocolMiddleware
application = ProtocolTypeRouter({'http': django_asgi_app, 'websocket': AccessTokenSubprotocolMiddleware(URLRouter(websocket_urlpatterns))})
