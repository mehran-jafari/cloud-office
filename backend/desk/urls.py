from django.urls import path
from .views import (
    AgentInstallerView,
    AddressBookView,
    ConferenceCreateView,
    ConnectRemoteView,
    IceConfigView,
    LookupDeviceView,
    MyDeviceView,
    RegisterDeviceView,
    SessionActionView,
    SessionListView,
)

urlpatterns = [
    path('ice/', IceConfigView.as_view()),
    path('agent/<str:platform>/', AgentInstallerView.as_view()),
    path('register/', RegisterDeviceView.as_view()),
    path('me/', MyDeviceView.as_view()),
    path('lookup/<str:desk_id>/', LookupDeviceView.as_view()),
    path('connect/', ConnectRemoteView.as_view()),
    path('sessions/', SessionListView.as_view()),
    path('sessions/<str:session_key>/', SessionActionView.as_view()),
    path('contacts/', AddressBookView.as_view()),
    path('conference/', ConferenceCreateView.as_view()),
]
