from rest_framework.permissions import BasePermission
from accounts.models import AccessRole, RoleDefinition, SupportAgentPermission, UserRole


def role_codes_for(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return ['owner']
    codes = list(UserRole.objects.filter(user=user).values_list('role__code', flat=True))
    if codes:
        return codes
    legacy = AccessRole.objects.filter(user=user).values_list('role', flat=True).first()
    if legacy:
        return [legacy]
    if user.is_staff:
        return ['admin']
    return ['member']


def has_role(user, *codes):
    """آیا کاربر حداقل یکی از نقش‌های داده‌شده را دارد؟ (برای کاربران چندنقشه؛ role_for فقط بالاترین نقش را برمی‌گرداند.)"""
    return bool(set(role_codes_for(user)) & set(codes))


def role_for(user):
    """نقش اصلی (اولین/بالاترین) برای سازگاری با کد قدیمی."""
    codes = role_codes_for(user)
    priority = ['owner', 'admin', 'support', 'auditor', 'member']
    for p in priority:
        if p in codes:
            return p
    return codes[0] if codes else 'member'


def merged_permissions(user) -> dict:
    if not user or not user.is_authenticated:
        return {}
    if user.is_superuser:
        return {
            'manage_users': True, 'manage_roles': True, 'manage_support': True,
            'view_admin': True, 'view_files': True,
            'edit_files': True, 'view_mail': True, 'view_activity': True, 'view_remote': True,
        }
    perms = {}
    roles = RoleDefinition.objects.filter(user_roles__user=user)
    if not roles.exists():
        code = role_for(user)
        roles = RoleDefinition.objects.filter(code=code)
    for role in roles:
        for k, v in (role.permissions or {}).items():
            if v:
                perms[k] = True
    perms.pop('reply_support', None)
    # Support replies are enabled only through the explicit staff toggle.
    if SupportAgentPermission.objects.filter(user=user, can_reply=True).exists():
        perms['reply_support'] = True
    return perms


def has_perm(user, key: str) -> bool:
    return bool(merged_permissions(user).get(key))


class CanManageAccess(BasePermission):
    message = 'فقط مالک یا مدیر سازمان به مدیریت دسترسی‌ها دسترسی دارد.'

    def has_permission(self, request, view):
        return has_perm(request.user, 'manage_users') or role_for(request.user) in {'owner', 'admin'}


class CanViewAdmin(BasePermission):
    message = 'دسترسی به پنل مدیریت ندارید.'

    def has_permission(self, request, view):
        return has_perm(request.user, 'view_admin') or role_for(request.user) in {'owner', 'admin'}


class CanReplySupport(BasePermission):
    message = 'مجوز پاسخ‌گویی پشتیبانی فعال نیست.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return SupportAgentPermission.objects.filter(user=request.user, can_reply=True).exists()
