import secrets
import string

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_desk_id():
    """شناسه ۹ رقمی با CSPRNG (ماژول secrets) — نه random غیرامن."""
    for _ in range(50):
        desk_id = ''.join(secrets.choice(string.digits) for _ in range(9))
        try:
            if not Device.objects.filter(desk_id=desk_id).exists():
                return desk_id
        except Exception:
            return desk_id
    return ''.join(secrets.choice(string.digits) for _ in range(9))


def generate_token():
    return secrets.token_hex(32)


def generate_password():
    """رمز اتصال ۱۲ کاراکتری با CSPRNG."""
    return ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(12))


def default_password_hash():
    return make_password(generate_password())


class Device(models.Model):
    desk_id = models.CharField(max_length=9, unique=True, default=generate_desk_id)
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    alias = models.CharField(max_length=80, blank=True, default='')
    # هش امن Django — رمز خام هرگز در دیتابیس ذخیره نمی‌شود
    password = models.CharField(max_length=128, default=default_password_hash, editable=False)
    hostname = models.CharField(max_length=120, blank=True, default='')
    os_name = models.CharField(max_length=80, blank=True, default='')
    online = models.BooleanField(default=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='desk_devices',
    )
    last_seen = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f'{self.desk_id} ({self.alias or self.user_id})'

    def set_password(self, raw: str | None = None) -> str:
        """رمز جدید تولید و هش امن ذخیره می‌شود؛ مقدار خام فقط یک‌بار برگردانده می‌شود."""
        raw = raw or generate_password()
        self.password = make_password(raw)
        self.password_plain = raw  # transient
        return raw

    def verify_password(self, raw: str) -> bool:
        if not raw or not self.password:
            return False
        # سازگاری با نسخه‌های قدیمی که plaintext یا SHA256 ذخیره می‌کردند
        if len(self.password) <= 32 and not self.password.startswith('pbkdf2_'):
            # plaintext legacy
            import hmac
            return hmac.compare_digest(self.password, raw)
        if len(self.password) == 64 and all(c in '0123456789abcdef' for c in self.password.lower()):
            import hashlib
            import hmac
            return hmac.compare_digest(self.password, hashlib.sha256(raw.encode()).hexdigest())
        return check_password(raw, self.password)


class AddressBookEntry(models.Model):
    owner = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='contacts')
    desk_id = models.CharField(max_length=9)
    alias = models.CharField(max_length=80, blank=True, default='')
    last_connected = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'desk_id')
        ordering = ['-last_connected', '-created_at']


class DeskSession(models.Model):
    STATUS = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('rejected', 'Rejected'),
    ]
    session_key = models.CharField(max_length=64, unique=True, default=generate_token)
    host = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='hosted_sessions')
    client = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='client_sessions')
    status = models.CharField(max_length=16, choices=STATUS, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']


class DeskConference(models.Model):
    code = models.CharField(max_length=12, unique=True)
    title = models.CharField(max_length=120, blank=True, default='')
    host = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='hosted_conferences')
    status = models.CharField(max_length=16, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
