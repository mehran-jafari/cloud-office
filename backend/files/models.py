from django.conf import settings
from django.db import models


class Folder(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='deleted_folders'
    )

    def __str__(self):
        return self.name


class File(models.Model):
    name = models.CharField(max_length=255)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cloud_files')
    storage_key = models.CharField(max_length=500, blank=True)
    mime_type = models.CharField(max_length=150, default='application/octet-stream')
    size_bytes = models.PositiveBigIntegerField(default=0)
    current_version = models.PositiveIntegerField(default=1)
    revision = models.PositiveBigIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='deleted_files'
    )

    def __str__(self):
        return self.name


class FileVersion(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=500)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(max_length=64)
    provider_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        constraints = [
            models.UniqueConstraint(fields=['file', 'version_number'], name='unique_file_version')
        ]

    def __str__(self):
        return f'{self.file_id}:v{self.version_number}'


class FileShare(models.Model):
    """اشتراک فایل با کاربر مشخص + سطح دسترسی دقیق."""
    PERMISSION_CHOICES = [
        ('view', 'فقط مشاهده'),
        ('download', 'مشاهده + دانلود/کپی'),
        ('edit', 'مشاهده + دانلود + ویرایش'),
        ('full', 'کامل (ویرایش + اشتراک مجدد)'),
    ]
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_shares'
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_shares'
    )
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    can_view = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_reshare = models.BooleanField(default=False)
    message = models.CharField(max_length=300, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('file', 'shared_with')]
        ordering = ['-created_at']

    def apply_permission_level(self):
        """همگام‌سازی فلگ‌ها با سطح permission."""
        level = self.permission or 'view'
        self.can_view = True
        self.can_download = level in ('download', 'edit', 'full')
        self.can_edit = level in ('edit', 'full')
        self.can_reshare = level == 'full'

    def capabilities(self):
        return {
            'view': bool(self.can_view),
            'download': bool(self.can_download),
            'copy': bool(self.can_download),
            'edit': bool(self.can_edit),
            'reshare': bool(self.can_reshare),
        }

    def __str__(self):
        return f'{self.file_id} → {self.shared_with_id} ({self.permission})'


class ActivityLog(models.Model):
    """گزارش فعالیت فضای کاری."""
    ACTION_CHOICES = [
        ('upload', 'آپلود فایل'),
        ('download', 'دانلود فایل'),
        ('share', 'اشتراک‌گذاری'),
        ('edit', 'ویرایش'),
        ('delete', 'حذف'),
        ('login', 'ورود'),
        ('mail_sent', 'ارسال نامه'),
        ('mail_received', 'دریافت نامه'),
        ('support', 'پشتیبانی'),
        ('remote', 'اتصال امن'),
        ('admin', 'عملیات مدیریتی'),
        ('other', 'سایر'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default='other')
    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id}: {self.action} — {self.title}'


class Correspondence(models.Model):
    """مکاتبات سازمانی / اتوماسیون اداری ساده."""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('sent', 'ارسال‌شده'),
        ('received', 'دریافت‌شده'),
        ('archived', 'بایگانی'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'کم'),
        ('normal', 'عادی'),
        ('high', 'فوری'),
    ]
    subject = models.CharField(max_length=300)
    body = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_mails'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mails'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_read = models.BooleanField(default=False)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.subject



class Notification(models.Model):
    """اعلان درون‌برنامه‌ای: اشتراک، مکاتبه، پیام پشتیبانی."""
    KIND_CHOICES = [
        ('share', 'اشتراک فایل'),
        ('mail', 'مکاتبه'),
        ('support', 'پیام پشتیبانی'),
        ('system', 'سیستمی'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='system')
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id}: {self.title}'


class PublicShareLink(models.Model):
    """لینک عمومی اشتراک فایل با توکن، رمز اختیاری و تاریخ انقضا."""
    PERMISSION_CHOICES = [
        ('view', 'فقط مشاهده'),
        ('download', 'مشاهده + دانلود'),
    ]
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='public_links')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_public_links'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    password_hash = models.CharField(max_length=128, blank=True)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    expires_at = models.DateTimeField(null=True, blank=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        if not self.is_active:
            return True
        if self.expires_at and self.expires_at < timezone.now():
            return True
        if self.max_downloads is not None and self.download_count >= self.max_downloads:
            return True
        return False

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return True
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password or '', self.password_hash)

    def __str__(self):
        return f'public:{self.token[:8]}… → file {self.file_id}'
