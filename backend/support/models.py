from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('waiting_agent', 'Waiting agent'),
        ('waiting_user', 'Waiting user'),
        ('ai_handling', 'AI handling'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_conversations'
    )
    subject = models.CharField(max_length=200, default='درخواست پشتیبانی')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_support_conversations',
    )
    first_agent_response_at = models.DateTimeField(null=True, blank=True)
    last_user_message_at = models.DateTimeField(null=True, blank=True)
    last_agent_message_at = models.DateTimeField(null=True, blank=True)
    next_escalate_at = models.DateTimeField(null=True, blank=True)
    escalation_count = models.PositiveSmallIntegerField(default=0)
    ai_handled = models.BooleanField(default=False)
    ai_confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'#{self.pk} {self.subject}'

    def mark_user_message(self):
        now = timezone.now()
        self.last_user_message_at = now
        if self.status in {'waiting_user', 'ai_handling', 'closed'}:
            self.status = 'waiting_agent'
        elif self.status == 'open':
            self.status = 'waiting_agent'
        # زمان escalation بعدی (۱۵ دقیقه)
        self.next_escalate_at = now + timedelta(minutes=15)
        self.save(update_fields=[
            'last_user_message_at', 'status', 'next_escalate_at', 'updated_at',
        ])

    def mark_agent_message(self, agent):
        now = timezone.now()
        self.last_agent_message_at = now
        self.status = 'waiting_user'
        self.next_escalate_at = None
        if not self.first_agent_response_at:
            self.first_agent_response_at = now
        if not self.assigned_agent_id:
            self.assigned_agent = agent
        self.save(update_fields=[
            'last_agent_message_at', 'status', 'next_escalate_at',
            'first_agent_response_at', 'assigned_agent', 'updated_at',
        ])


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    body = models.TextField(max_length=5000)
    is_staff_reply = models.BooleanField(default=False)
    is_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class SupportAlertLog(models.Model):
    """لاگ اعلان‌های پیام‌رسان برای جلوگیری از اسپم و ردیابی escalation."""
    KIND_CHOICES = [
        ('new_message', 'New message'),
        ('offline_broadcast', 'Offline broadcast'),
        ('escalation', 'Escalation'),
        ('admin_delay', 'Admin delay alert'),
    ]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='alert_logs'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    channel = models.CharField(max_length=20, blank=True)  # telegram/bale/eitaa/sms/inapp
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['conversation', 'kind', 'sent_at'], name='support_sup_convers_idx'),
        ]


from .remote_models import RemoteSession  # noqa: E402,F401
