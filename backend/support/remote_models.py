import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

class RemoteSession(models.Model):
    STATUS_CHOICES = [('pending', 'Pending consent'), ('active', 'Active'), ('ended', 'Ended'), ('expired', 'Expired')]
    MODE_CHOICES = [('screen_share', 'Screen share')]
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='remote_sessions_requested')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='remote_sessions_joined')
    conversation = models.ForeignKey('support.Conversation', on_delete=models.SET_NULL, null=True, blank=True, related_name='remote_sessions')
    code_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    mode = models.CharField(max_length=30, choices=MODE_CHOICES, default='screen_share')
    expires_at = models.DateTimeField()
    consented_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def create_code():
        raw = secrets.token_hex(6).upper()
        return raw, hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def hash_code(raw): return hashlib.sha256(raw.strip().upper().encode()).hexdigest()

    def is_expired(self): return self.status == 'pending' and timezone.now() >= self.expires_at
    def __str__(self): return f'Remote #{self.pk} ({self.status})'
