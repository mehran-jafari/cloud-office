from django.contrib import admin
from .models import AccessRole, StorageQuota, SupportAgentPermission

@admin.register(AccessRole)
class AccessRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('role',)

@admin.register(StorageQuota)
class StorageQuotaAdmin(admin.ModelAdmin):
    list_display = ('user', 'allocated_bytes', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('updated_at',)

@admin.register(SupportAgentPermission)
class SupportAgentPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'can_reply', 'granted_by', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('can_reply',)
