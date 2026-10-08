from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import AccessRole, StorageQuota, SupportAgentPermission
User = get_user_model()

class AccessRoleSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = AccessRole
        fields = ['user', 'username', 'role', 'updated_at']
        read_only_fields = ['user', 'username', 'updated_at']

class StorageQuotaSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    used_bytes = serializers.SerializerMethodField()
    remaining_bytes = serializers.SerializerMethodField()
    class Meta:
        model = StorageQuota
        fields = ['user', 'username', 'allocated_bytes', 'used_bytes', 'remaining_bytes', 'updated_at']
    def get_used_bytes(self, obj): return self.context.get('usage', {}).get(obj.user_id, 0) if self.context.get('usage') else 0
    def get_remaining_bytes(self, obj): return max(0, obj.allocated_bytes - self.get_used_bytes(obj))

class AgentPermissionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = SupportAgentPermission
        fields = ['user', 'username', 'can_reply', 'granted_by', 'updated_at']
        read_only_fields = ['user', 'username', 'granted_by', 'updated_at']
