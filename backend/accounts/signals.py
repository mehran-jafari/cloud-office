from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccessRole, RoleDefinition, StorageQuota, UserProfile, UserRole


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_defaults(sender, instance, created, **kwargs):
    """برای هر کاربر جدید سهمیه، پروفایل و نقش پایه بساز."""
    StorageQuota.objects.get_or_create(user=instance)
    UserProfile.objects.get_or_create(user=instance)
    if created or instance.is_superuser:
        role = 'owner' if instance.is_superuser else 'member'
        AccessRole.objects.update_or_create(
            user=instance,
            defaults={'role': role},
        )
        role_def = RoleDefinition.objects.filter(code=role).first()
        if role_def:
            UserRole.objects.get_or_create(user=instance, role=role_def)
