from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'body',
            'is_staff_reply', 'is_ai', 'created_at',
        ]
        read_only_fields = fields

    def get_sender_name(self, obj):
        if obj.is_ai or not obj.sender_id:
            return 'دستیار هوشمند'
        return obj.sender.get_full_name() or obj.sender.username


class ConversationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    assigned_agent_name = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    unread_hint = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'user', 'user_name', 'subject', 'status',
            'assigned_agent', 'assigned_agent_name',
            'first_agent_response_at', 'last_user_message_at', 'last_agent_message_at',
            'next_escalate_at', 'escalation_count',
            'ai_handled', 'ai_confidence',
            'created_at', 'updated_at',
            'messages', 'unread_hint',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_assigned_agent_name(self, obj):
        if not obj.assigned_agent_id:
            return None
        return obj.assigned_agent.get_full_name() or obj.assigned_agent.username

    def get_unread_hint(self, obj):
        return obj.status in {'waiting_agent', 'escalated', 'open'}
