from django.urls import path
from .views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessageView,
    SupportEscalationRunView,
    SupportPerformanceReportView,
    SupportPresenceView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='support-conversations'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='support-conversation-detail'),
    path('conversations/<int:pk>/messages/', ConversationMessageView.as_view(), name='support-conversation-messages'),
    path('presence/', SupportPresenceView.as_view(), name='support-presence'),
    path('escalations/run/', SupportEscalationRunView.as_view(), name='support-escalations-run'),
    path('reports/performance/', SupportPerformanceReportView.as_view(), name='support-performance-report'),
]
