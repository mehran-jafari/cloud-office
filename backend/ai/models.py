from django.conf import settings
from django.db import models


class AIQuota(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_quota')
    monthly_tokens = models.PositiveIntegerField(default=200_000)
    used_tokens = models.PositiveIntegerField(default=0)
    period_start = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def remaining(self) -> int:
        return max(0, self.monthly_tokens - self.used_tokens)

    def __str__(self):
        return f'AIQuota({self.user_id}: {self.used_tokens}/{self.monthly_tokens})'


class AIUsageLog(models.Model):
    ACTION_CHOICES = [
        ('draft_mail', 'پیش‌نویس نامه'),
        ('summarize', 'خلاصه‌سازی'),
        ('support_reply', 'پیشنهاد پاسخ پشتیبانی'),
        ('stt', 'گفتار به متن'),
        ('embed', 'بردارسازی فایل'),
        ('semantic_search', 'جست‌وجوی معنایی'),
        ('meeting_summary', 'خلاصه جلسه'),
        ('auto_support', 'پاسخ خودکار پشتیبانی'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_usage_logs')
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    tokens_used = models.PositiveIntegerField(default=0)
    model_name = models.CharField(max_length=80, blank=True)
    success = models.BooleanField(default=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FileEmbedding(models.Model):
    """بردار معنایی برای جست‌وجوی فایل (JSON float list — بدون نیاز اجباری به pgvector)."""
    file = models.OneToOneField('files.File', on_delete=models.CASCADE, related_name='embedding')
    model_name = models.CharField(max_length=80, blank=True)
    dims = models.PositiveIntegerField(default=0)
    vector = models.JSONField(default=list, blank=True)
    text_preview = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Embedding(file={self.file_id}, dims={self.dims})'
