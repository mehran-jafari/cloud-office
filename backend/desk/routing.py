from django.urls import re_path
from .consumers import DeskSignalConsumer

websocket_urlpatterns = [
    re_path(r'^ws/desk/$', DeskSignalConsumer.as_asgi()),
    re_path(r'^ws/signal/$', DeskSignalConsumer.as_asgi()),
]
