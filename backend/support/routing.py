from django.urls import re_path
from .consumers import RemoteConferenceConsumer
websocket_urlpatterns = [re_path(r'^ws/remote/(?P<session_id>[0-9]+)/$', RemoteConferenceConsumer.as_asgi())]
