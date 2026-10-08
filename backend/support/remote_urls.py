from django.urls import path
from .remote_views import RemoteSessionConsentView, RemoteSessionCreateView, RemoteSessionDetailView, RemoteSessionEndView, RemoteSessionJoinView
urlpatterns = [
    path('remote-sessions/', RemoteSessionCreateView.as_view()),
    path('remote-sessions/join/', RemoteSessionJoinView.as_view()),
    path('remote-sessions/<int:pk>/', RemoteSessionDetailView.as_view()),
    path('remote-sessions/<int:pk>/consent/', RemoteSessionConsentView.as_view()),
    path('remote-sessions/<int:pk>/end/', RemoteSessionEndView.as_view()),
]
