from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .editor import EditorConfigView, EditorDownloadView, FileVersionsView, OnlyOfficeCallbackView, RestoreVersionView
from .views import FileBulkActionView, FileConvertView, FileDownloadView, FileViewSet, FolderViewSet
from .workspace import (
    ActivityListView,
    CorrespondenceDetailView,
    CorrespondenceListCreateView,
    DashboardStatsView,
    FileShareDeleteView,
    FileShareListCreateView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
    UserLookupView,
    TrashListView,
    TrashRestoreView,
    TrashPurgeView,
    PublicShareLinkListCreateView,
    PublicShareLinkDetailView,
    PublicShareAccessView,
    AdvancedSearchView,
    AuditLogView,
)

router = DefaultRouter()
router.register('items', FileViewSet, basename='file')
router.register('folders', FolderViewSet, basename='folder')

urlpatterns = [
    path('bulk/', FileBulkActionView.as_view(), name='file-bulk'),
    path('<int:pk>/download/', FileDownloadView.as_view(), name='file-download'),
    path('<int:pk>/convert/', FileConvertView.as_view(), name='file-convert'),
    path('<int:pk>/editor-config/', EditorConfigView.as_view(), name='editor-config'),
    path('<int:pk>/editor-download/', EditorDownloadView.as_view(), name='editor-download'),
    path('<int:pk>/onlyoffice-callback/', OnlyOfficeCallbackView.as_view(), name='onlyoffice-callback'),
    path('<int:pk>/versions/', FileVersionsView.as_view(), name='file-versions'),
    path('<int:pk>/restore/<int:version>/', RestoreVersionView.as_view(), name='restore-version'),
    path('shares/', FileShareListCreateView.as_view()),
    path('shares/<int:pk>/', FileShareDeleteView.as_view()),
    path('activity/', ActivityListView.as_view()),
    path('mail/', CorrespondenceListCreateView.as_view()),
    path('mail/<int:pk>/', CorrespondenceDetailView.as_view()),
    path('users/lookup/', UserLookupView.as_view()),
    path('dashboard-stats/', DashboardStatsView.as_view()),
    path('notifications/', NotificationListView.as_view()),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view()),
    path('notifications/mark-read/', NotificationMarkReadView.as_view()),
    # Trash
    path('trash/', TrashListView.as_view()),
    path('trash/restore/', TrashRestoreView.as_view()),
    path('trash/purge/', TrashPurgeView.as_view()),
    # Public share links
    path('public-links/', PublicShareLinkListCreateView.as_view()),
    path('public-links/<int:pk>/', PublicShareLinkDetailView.as_view()),
    path('public/share/<str:token>/', PublicShareAccessView.as_view()),
    path('search/', AdvancedSearchView.as_view()),
    path('audit/', AuditLogView.as_view()),
    path('', include(router.urls)),
]
