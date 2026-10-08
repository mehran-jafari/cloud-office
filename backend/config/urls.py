from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from accounts.views import (
    AdminCreateUserView,
    AdminUpdateUserView,
    AdminRolesView,
    AdminSupportAgentsView,
    AdminUserQuotaView,
    AdminUsersView,
    LoginView,
    LogoutView,
    MeView,
    MyQuotaView,
    OnlineSupportAgentsView,
    ProfileView,
    RefreshView,
    RoleDefinitionDetailView,
    RoleDefinitionListCreateView,
    SupportOnlineToggleView,
    AvatarUploadView,
)
from files.views import HealthView
from monitoring_views import metrics

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/metrics/', metrics, name='metrics'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/refresh/', RefreshView.as_view(), name='refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', MeView.as_view(), name='me'),
    path('api/account/quota/', MyQuotaView.as_view(), name='my-quota'),
    path('api/admin/users/', AdminUsersView.as_view(), name='admin-users'),
    path('api/admin/users/create/', AdminCreateUserView.as_view(), name='admin-create-user'),
    path('api/admin/users/<int:user_id>/update/', AdminUpdateUserView.as_view(), name='admin-update-user'),
    path('api/admin/roles-definitions/', RoleDefinitionListCreateView.as_view()),
    path('api/admin/roles-definitions/<int:pk>/', RoleDefinitionDetailView.as_view()),
    path('api/account/profile/', ProfileView.as_view(), name='profile'),
    path('api/account/avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
    path('api/support/online-agents/', OnlineSupportAgentsView.as_view()),
    path('api/support/online-toggle/', SupportOnlineToggleView.as_view()),
    path('api/admin/users/<int:user_id>/quota/', AdminUserQuotaView.as_view(), name='admin-user-quota'),
    path('api/admin/support-agents/', AdminSupportAgentsView.as_view(), name='admin-support-agents'),
    path('api/admin/support-agents/<int:user_id>/', AdminSupportAgentsView.as_view(), name='admin-support-agent-permission'),
    path('api/admin/roles/', AdminRolesView.as_view(), name='admin-roles'),
    path('api/admin/roles/<int:user_id>/', AdminRolesView.as_view(), name='admin-role'),
    path('api/files/', include('files.urls')),
    path('api/support/', include('support.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/desk/', include('desk.urls')),
    path('api/support/', include('support.remote_urls')),
]

if settings.DEBUG:
    # فقط آواتارها؛ فایل‌های خصوصی کاربران (uploads/) هرگز بدون احراز هویت سرو نمی‌شوند.
    urlpatterns += static(
        settings.MEDIA_URL + 'avatars/',
        document_root=settings.MEDIA_ROOT / 'avatars',
    )
