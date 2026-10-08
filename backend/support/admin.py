from django.contrib import admin
from .models import Conversation, Message, RemoteSession

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'created_at', 'is_staff_reply')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('subject', 'user__username')
    inlines = [MessageInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'is_staff_reply', 'created_at')
    list_filter = ('is_staff_reply',)

@admin.register(RemoteSession)
class RemoteSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'agent', 'status', 'mode', 'expires_at', 'consented_at', 'ended_at')
    list_filter = ('status', 'mode')
    search_fields = ('requester__username', 'agent__username')
    readonly_fields = ('code_hash', 'created_at', 'updated_at')
