from rest_framework import serializers
from .remote_models import RemoteSession

class RemoteSessionSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    class Meta:
        model = RemoteSession
        fields = ['id', 'requester', 'requester_name', 'agent', 'agent_name', 'conversation', 'status', 'mode', 'expires_at', 'consented_at', 'started_at', 'ended_at', 'created_at', 'updated_at']
        read_only_fields = fields
    def get_requester_name(self, obj): return obj.requester.get_full_name() or obj.requester.username
    def get_agent_name(self, obj): return (obj.agent.get_full_name() or obj.agent.username) if obj.agent else None

class RemoteSessionCreateSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    mode = serializers.ChoiceField(choices=['screen_share'], default='screen_share')

class RemoteSessionJoinSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=12, max_length=12, trim_whitespace=True)
