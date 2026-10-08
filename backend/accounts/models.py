from django.conf import settings
from django.db import models


class RoleDefinition(models.Model):
    """نقش داینامیک با مجوزهای قابل تنظیم."""
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # flags: manage_users, manage_roles, manage_support, reply_support, view_admin,
    # view_files, edit_files, view_mail, view_activity, view_remote
    permissions = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def has_perm(self, key: str) -> bool:
        return bool((self.permissions or {}).get(key))


class UserRole(models.Model):
    """چند نقش برای هر کاربر."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(RoleDefinition, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'role')]

    def __str__(self):
        return f'{self.user_id}:{self.role.code}'


class AccessRole(models.Model):
    """سازگاری با نسخه قبلی — نقش اصلی نمایشی."""
    ROLE_CHOICES = [
        ('owner', 'مالک سازمان'),
        ('admin', 'مدیر'),
        ('support', 'کارشناس پشتیبانی'),
        ('auditor', 'حسابرسی'),
        ('member', 'کاربر'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def can_manage_users(self):
        return self.role in {'owner', 'admin'}

    @property
    def can_manage_support(self):
        return self.role in {'owner', 'admin'}

    @property
    def can_reply_support(self):
        return self.role in {'owner', 'admin', 'support'}

    def __str__(self):
        return f'{self.user.username}: {self.role}'


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'مرد'), ('female', 'زن'), ('other', 'سایر')],
        default='male',
        blank=True,
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    # کانال‌های اطلاع‌رسانی: sms, bale, eitaa, telegram
    notify_sms = models.BooleanField(default=False)
    notify_bale = models.BooleanField(default=False)
    notify_eitaa = models.BooleanField(default=False)
    notify_telegram = models.BooleanField(default=False)
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    bale_chat_id = models.CharField(max_length=64, blank=True)
    eitaa_chat_id = models.CharField(max_length=64, blank=True)
    avatar_color = models.CharField(max_length=20, default='#7667f7')
    is_support_online = models.BooleanField(default=False)
    support_last_seen = models.DateTimeField(null=True, blank=True)
    notify_support_offline = models.BooleanField(
        default=True,
        help_text='اگر آفلاین بودم برای پیام‌های پشتیبانی جدید اعلان پیام‌رسان بگیرم',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'profile:{self.user_id}'


class StorageQuota(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='storage_quota')
    allocated_bytes = models.PositiveBigIntegerField(default=5 * 1024**3)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}: {self.allocated_bytes} bytes'


class SupportAgentPermission(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_permission')
    can_reply = models.BooleanField(default=False)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='granted_support_permissions'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}: can_reply={self.can_reply}'
