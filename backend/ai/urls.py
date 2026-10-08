from django.urls import path
from .views import (
    AIConferenceDocView,
    AICreateFileView,
    AIProofreadView,
    AIDraftMailView,
    AIIndexFileView,
    AIMeetingSummaryView,
    AISemanticSearchView,
    AISpeechToTextView,
    AIStatusView,
    AISummarizeView,
    AISupportReplyView,
    AIUsageLogView,
)

urlpatterns = [
    path('status/', AIStatusView.as_view()),
    path('draft-mail/', AIDraftMailView.as_view()),
    path('create-file/', AICreateFileView.as_view()),
    path('proofread/', AIProofreadView.as_view()),
    path('conference-doc/', AIConferenceDocView.as_view()),
    path('summarize/', AISummarizeView.as_view()),
    path('support-reply/', AISupportReplyView.as_view()),
    path('stt/', AISpeechToTextView.as_view()),
    path('meeting-summary/', AIMeetingSummaryView.as_view()),
    path('index-file/', AIIndexFileView.as_view()),
    path('semantic-search/', AISemanticSearchView.as_view()),
    path('usage/', AIUsageLogView.as_view()),
]
