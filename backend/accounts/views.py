from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from files.models import File
from .models import AccessRole, RoleDefinition, StorageQuota, SupportAgentPermission, UserProfile, UserRole
from .serializers import AccessRoleSerializer, AgentPermissionSerializer
from support.permissions import CanManageAccess, CanViewAdmin, has_perm, merged_permissions, role_codes_for, role_for
from .notifications import notify_user
User = get_user_model()


def password_error(password, user=None):
    """اعتبارسنجی رمز با AUTH_PASSWORD_VALIDATORS؛ متن خطا یا None."""
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        return ' '.join(exc.messages)
    return None

class LoginView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        response = Response({'access': serializer.validated_data['access']})
        response.set_cookie(settings.REFRESH_COOKIE_NAME, serializer.validated_data['refresh'], httponly=True, secure=settings.REFRESH_COOKIE_SECURE, samesite=settings.REFRESH_COOKIE_SAMESITE, path=settings.REFRESH_COOKIE_PATH, max_age=7 * 24 * 60 * 60)
        return response

class RefreshView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not token: return Response({'detail': 'refresh token missing'}, status=401)
        serializer = TokenRefreshSerializer(data={'refresh': token}); serializer.is_valid(raise_exception=True)
        response = Response({'access': serializer.validated_data['access']})
        if 'refresh' in serializer.validated_data:
            response.set_cookie(settings.REFRESH_COOKIE_NAME, serializer.validated_data['refresh'], httponly=True, secure=settings.REFRESH_COOKIE_SECURE, samesite=settings.REFRESH_COOKIE_SAMESITE, path=settings.REFRESH_COOKIE_PATH, max_age=7 * 24 * 60 * 60)
        return response

class LogoutView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if token:
            try: RefreshToken(token).blacklist()
            except Exception: pass
        response = Response(status=204); response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH); return response

class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Ensure quota + role exist even for users created before signals
        StorageQuota.objects.get_or_create(user=request.user)
        if request.user.is_superuser:
            AccessRole.objects.update_or_create(user=request.user, defaults={'role': 'owner'})
            SupportAgentPermission.objects.update_or_create(user=request.user, defaults={'can_reply': True})
        elif not AccessRole.objects.filter(user=request.user).exists():
            AccessRole.objects.create(user=request.user, role='admin' if request.user.is_staff else 'member')
        role = role_for(request.user)
        UserProfile.objects.get_or_create(user=request.user)
        perms = merged_permissions(request.user)
        codes = role_codes_for(request.user)
        profile = request.user.profile
        return Response({
            'id': request.user.id,
            'username': request.user.get_username(),
            'first_name': request.user.first_name or request.user.username,
            'last_name': request.user.last_name,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'is_support_online': profile.is_support_online,
            'role': role,
            'roles': codes,
            'phone': profile.phone,
            'permissions': {
                'manage_users': perms.get('manage_users', False),
                'manage_support': perms.get('manage_support', False),
                'reply_support': perms.get('reply_support', False),
                'view_admin': perms.get('view_admin', False) or role in {'owner', 'admin'},
                **perms,
            },
        })

def usage_for(user_id): return File.objects.filter(owner_id=user_id).aggregate(total=Sum('size_bytes')).get('total') or 0

def quota_payload(user):
    quota, _ = StorageQuota.objects.get_or_create(user=user)
    used = usage_for(user.id)
    return {'user': user.id, 'username': user.username, 'allocated_bytes': quota.allocated_bytes, 'used_bytes': used, 'remaining_bytes': max(0, quota.allocated_bytes - used), 'percent_used': round((used / quota.allocated_bytes) * 100, 2) if quota.allocated_bytes else 100}

class MyQuotaView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request): return Response(quota_payload(request.user))



class AdminCreateUserView(APIView):
    permission_classes = [CanManageAccess]

    def post(self, request):
        username = str(request.data.get('username') or '').strip()
        password = str(request.data.get('password') or '')
        first_name = str(request.data.get('first_name') or '').strip()
        last_name = str(request.data.get('last_name') or '').strip()
        role = str(request.data.get('role') or 'member').strip()
        is_staff = bool(request.data.get('is_staff', False))
        quota_gb = request.data.get('quota_gb', 5)

        if not username or len(username) < 3:
            return Response({'detail': 'نام کاربری حداقل ۳ کاراکتر باشد'}, status=400)
        if not password:
            return Response({'detail': 'رمز عبور الزامی است'}, status=400)
        err = password_error(password)
        if err:
            return Response({'detail': err}, status=400)
        if role not in dict(AccessRole.ROLE_CHOICES):
            return Response({'detail': 'نقش نامعتبر است'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'detail': 'این نام کاربری قبلاً ثبت شده است'}, status=400)
        if role == 'owner' and not request.user.is_superuser:
            return Response({'detail': 'فقط مالک فعلی می‌تواند مالک جدید تعیین کند'}, status=403)

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff or role in {'admin', 'support', 'owner'},
        )
        AccessRole.objects.update_or_create(user=user, defaults={'role': role})
        roles_in = request.data.get('roles')
        if isinstance(roles_in, list) and roles_in:
            UserRole.objects.filter(user=user).delete()
            for code in roles_in:
                rd = RoleDefinition.objects.filter(code=str(code)).first()
                if rd:
                    UserRole.objects.get_or_create(user=user, role=rd)
            role = str(roles_in[0])
            AccessRole.objects.update_or_create(user=user, defaults={'role': role if role in dict(AccessRole.ROLE_CHOICES) else 'member'})
        else:
            role_def = RoleDefinition.objects.filter(code=role).first()
            if role_def:
                UserRole.objects.get_or_create(user=user, role=role_def)
        try:
            allocated = int(float(quota_gb) * 1024 ** 3)
        except (TypeError, ValueError):
            allocated = 5 * 1024 ** 3
        StorageQuota.objects.update_or_create(user=user, defaults={'allocated_bytes': max(allocated, 100 * 1024 * 1024)})
        profile, _ = UserProfile.objects.get_or_create(user=user)
        phone = str(request.data.get('phone') or '').strip()
        if phone:
            profile.phone = phone[:20]
            profile.save(update_fields=['phone', 'updated_at'])
        if role in {'owner', 'admin', 'support'}:
            SupportAgentPermission.objects.update_or_create(user=user, defaults={'can_reply': True, 'granted_by': request.user})

        return Response({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role,
            'roles': [role],
            'phone': profile.phone,
            'is_staff': user.is_staff,
            'quota': quota_payload(user),
        }, status=201)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = role_for(request.user)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response({
            'id': request.user.id,
            'username': request.user.get_username(),
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': getattr(request.user, 'email', '') or '',
            'phone': profile.phone,
            'gender': profile.gender or 'male',
            'avatar_url': request.build_absolute_uri(profile.avatar.url) if profile.avatar else None,
            'notify_sms': profile.notify_sms,
            'notify_bale': profile.notify_bale,
            'notify_eitaa': profile.notify_eitaa,
            'notify_telegram': profile.notify_telegram,
            'is_support_online': profile.is_support_online,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'role': role,
            'roles': role_codes_for(request.user),
            'role_label': dict(AccessRole.ROLE_CHOICES).get(role, role),
            'quota': quota_payload(request.user),
            'date_joined': request.user.date_joined.isoformat() if request.user.date_joined else None,
        })

    def patch(self, request):
        user = request.user
        if 'first_name' in request.data:
            user.first_name = str(request.data.get('first_name') or '').strip()[:150]
        if 'last_name' in request.data:
            user.last_name = str(request.data.get('last_name') or '').strip()[:150]
        if 'email' in request.data:
            user.email = str(request.data.get('email') or '').strip()[:254]
        if request.data.get('password'):
            err = password_error(str(request.data['password']), user)
            if err:
                return Response({'detail': err}, status=400)
            user.set_password(str(request.data['password']))
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if 'phone' in request.data:
            profile.phone = str(request.data.get('phone') or '')[:20]
        if 'gender' in request.data and request.data['gender'] in ('male', 'female', 'other'):
            profile.gender = request.data['gender']
        for flag in ('notify_sms', 'notify_bale', 'notify_eitaa', 'notify_telegram'):
            if flag in request.data:
                setattr(profile, flag, bool(request.data[flag]))
        if 'is_support_online' in request.data:
            from support.services import can_agent_reply
            # آنلاین شدن فقط برای کسی که مجوز پاسخ دارد (وگرنه AI خاموش می‌شود و کسی جواب نمی‌دهد)
            if can_agent_reply(user) or not request.data['is_support_online']:
                profile.is_support_online = bool(request.data['is_support_online'])
        profile.save()
        return self.get(request)


class AdminUsersView(APIView):
    permission_classes = [CanManageAccess]
    def get(self, request):
        items = []
        for user in User.objects.filter(is_active=True).order_by('username'):
            payload = quota_payload(user)
            codes = role_codes_for(user)
            payload['role'] = codes[0] if codes else ('owner' if user.is_superuser else 'member')
            payload['roles'] = codes
            payload['first_name'] = user.first_name
            payload['last_name'] = user.last_name
            payload['is_staff'] = user.is_staff
            try:
                payload['phone'] = user.profile.phone
            except Exception:
                payload['phone'] = ''
            items.append(payload)
        return Response(items)

class AdminUserQuotaView(APIView):
    permission_classes = [CanManageAccess]
    def patch(self, request, user_id):
        try: user = User.objects.get(pk=user_id)
        except User.DoesNotExist: return Response({'detail': 'کاربر پیدا نشد'}, status=404)
        try: allocated = int(request.data.get('allocated_bytes'))
        except (TypeError, ValueError): return Response({'detail': 'allocated_bytes باید عدد باشد'}, status=400)
        if allocated < usage_for(user.id): return Response({'detail': 'سهمیه نمی‌تواند کمتر از مصرف فعلی باشد'}, status=400)
        quota, _ = StorageQuota.objects.get_or_create(user=user); quota.allocated_bytes = allocated; quota.save(update_fields=['allocated_bytes', 'updated_at'])
        return Response(quota_payload(user))

class AdminSupportAgentsView(APIView):
    permission_classes = [CanManageAccess]
    def get(self, request):
        permissions = {item.user_id: item for item in SupportAgentPermission.objects.select_related('user').all()}
        return Response([{'user': user.id, 'username': user.username, 'can_reply': permissions.get(user.id).can_reply if user.id in permissions else False, 'granted_by': permissions.get(user.id).granted_by_id if user.id in permissions else None, 'updated_at': permissions.get(user.id).updated_at if user.id in permissions else None} for user in User.objects.filter(is_staff=True, is_active=True).order_by('username')])
    def patch(self, request, user_id):
        if role_for(request.user) not in {'owner', 'admin'}: return Response({'detail': 'فقط مالک یا مدیر می‌تواند مجوز پاسخ‌گویی بدهد'}, status=403)
        try: user = User.objects.get(pk=user_id)
        except User.DoesNotExist: return Response({'detail': 'کاربر پیدا نشد'}, status=404)
        permission, _ = SupportAgentPermission.objects.get_or_create(user=user)
        permission.can_reply = bool(request.data.get('can_reply', False)); permission.granted_by = request.user; permission.save()
        return Response(AgentPermissionSerializer(permission).data)

class AdminRolesView(APIView):
    permission_classes = [CanManageAccess]
    def get(self, request):
        return Response(AccessRoleSerializer(AccessRole.objects.select_related('user').order_by('user__username'), many=True).data)
    def patch(self, request, user_id):
        if not request.user.is_superuser: return Response({'detail': 'تغییر نقش فقط برای مالک سازمان مجاز است'}, status=403)
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user: return Response({'detail': 'کاربر پیدا نشد'}, status=404)
        role = request.data.get('role')
        if role not in dict(AccessRole.ROLE_CHOICES): return Response({'detail': 'نقش نامعتبر است'}, status=400)
        if user == request.user and role != 'owner': return Response({'detail': 'نقش مالک فعلی قابل حذف نیست'}, status=400)
        access, _ = AccessRole.objects.get_or_create(user=user)
        access.role = role; access.save(update_fields=['role', 'updated_at'])
        role_def = RoleDefinition.objects.filter(code=role).first()
        if role_def:
            UserRole.objects.filter(user=user).delete()
            UserRole.objects.get_or_create(user=user, role=role_def)
        return Response(AccessRoleSerializer(access).data)


class AdminUpdateUserView(APIView):
    permission_classes = [CanManageAccess]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'کاربر پیدا نشد'}, status=404)
        if 'first_name' in request.data:
            user.first_name = str(request.data.get('first_name') or '')[:150]
        if 'last_name' in request.data:
            user.last_name = str(request.data.get('last_name') or '')[:150]
        if 'email' in request.data:
            user.email = str(request.data.get('email') or '')[:254]
        if request.data.get('password'):
            pwd = str(request.data['password'])
            err = password_error(pwd, user)
            if err:
                return Response({'detail': err}, status=400)
            user.set_password(pwd)
        if 'is_active' in request.data:
            user.is_active = bool(request.data['is_active'])
        if 'is_staff' in request.data:
            user.is_staff = bool(request.data['is_staff'])
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if 'phone' in request.data:
            profile.phone = str(request.data.get('phone') or '')[:20]
        if 'gender' in request.data and str(request.data.get('gender')) in ('male', 'female', 'other'):
            profile.gender = str(request.data['gender'])
        for flag in ('notify_sms', 'notify_bale', 'notify_eitaa', 'notify_telegram'):
            if flag in request.data:
                setattr(profile, flag, bool(request.data[flag]))
        for cid in ('telegram_chat_id', 'bale_chat_id', 'eitaa_chat_id'):
            if cid in request.data:
                setattr(profile, cid, str(request.data.get(cid) or '')[:64])
        if 'is_support_online' in request.data:
            profile.is_support_online = bool(request.data['is_support_online'])
        profile.save()
        # multiple roles
        if 'roles' in request.data and isinstance(request.data['roles'], list):
            codes = [str(c) for c in request.data['roles']]
            UserRole.objects.filter(user=user).delete()
            for code in codes:
                role_def = RoleDefinition.objects.filter(code=code).first()
                if role_def:
                    UserRole.objects.get_or_create(user=user, role=role_def)
            if codes:
                AccessRole.objects.update_or_create(user=user, defaults={'role': codes[0] if codes[0] in dict(AccessRole.ROLE_CHOICES) else 'member'})
        elif 'role' in request.data:
            role = str(request.data['role'])
            AccessRole.objects.update_or_create(user=user, defaults={'role': role})
            role_def = RoleDefinition.objects.filter(code=role).first()
            if role_def:
                UserRole.objects.filter(user=user).delete()
                UserRole.objects.get_or_create(user=user, role=role_def)
        payload = quota_payload(user)
        payload['roles'] = role_codes_for(user)
        payload['phone'] = profile.phone
        payload['first_name'] = user.first_name
        payload['last_name'] = user.last_name
        return Response(payload)


class RoleDefinitionListCreateView(APIView):
    permission_classes = [CanManageAccess]

    def get(self, request):
        items = RoleDefinition.objects.all()
        return Response([
            {'id': r.id, 'code': r.code, 'name': r.name, 'description': r.description,
             'permissions': r.permissions, 'is_system': r.is_system}
            for r in items
        ])

    def post(self, request):
        if not (has_perm(request.user, 'manage_roles') or request.user.is_superuser):
            return Response({'detail': 'مجوز مدیریت نقش‌ها ندارید'}, status=403)
        code = str(request.data.get('code') or '').strip().lower().replace(' ', '-')
        name = str(request.data.get('name') or '').strip()
        if not code or not name:
            return Response({'detail': 'کد و نام نقش الزامی است'}, status=400)
        if RoleDefinition.objects.filter(code=code).exists():
            return Response({'detail': 'این کد نقش قبلاً وجود دارد'}, status=400)
        perms = request.data.get('permissions') or {}
        role = RoleDefinition.objects.create(
            code=code, name=name, description=str(request.data.get('description') or ''),
            permissions=perms if isinstance(perms, dict) else {}, is_system=False,
        )
        return Response({'id': role.id, 'code': role.code, 'name': role.name, 'permissions': role.permissions}, status=201)


class RoleDefinitionDetailView(APIView):
    permission_classes = [CanManageAccess]

    def patch(self, request, pk):
        if not (has_perm(request.user, 'manage_roles') or request.user.is_superuser):
            return Response({'detail': 'مجوز مدیریت نقش‌ها ندارید'}, status=403)
        try:
            role = RoleDefinition.objects.get(pk=pk)
        except RoleDefinition.DoesNotExist:
            return Response({'detail': 'نقش پیدا نشد'}, status=404)
        if 'name' in request.data:
            role.name = str(request.data['name'])[:100]
        if 'description' in request.data:
            role.description = str(request.data['description'])
        if 'permissions' in request.data and isinstance(request.data['permissions'], dict):
            role.permissions = request.data['permissions']
        role.save()
        return Response({'id': role.id, 'code': role.code, 'name': role.name, 'permissions': role.permissions})

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({'detail': 'فقط مالک می‌تواند نقش حذف کند'}, status=403)
        try:
            role = RoleDefinition.objects.get(pk=pk)
        except RoleDefinition.DoesNotExist:
            return Response({'detail': 'نقش پیدا نشد'}, status=404)
        if role.is_system:
            return Response({'detail': 'نقش سیستمی قابل حذف نیست'}, status=400)
        role.delete()
        return Response(status=204)


class OnlineSupportAgentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from support.services import get_online_agents
        data = []
        for p in get_online_agents():
            avatar_url = None
            if p.avatar:
                try:
                    avatar_url = request.build_absolute_uri(p.avatar.url)
                except Exception:
                    avatar_url = None
            data.append({
                'id': p.user_id,
                'username': p.user.username,
                'first_name': p.user.first_name or p.user.username,
                'last_name': p.user.last_name,
                'avatar_color': p.avatar_color,
                'gender': p.gender or 'male',
                'avatar_url': avatar_url,
            })
        return Response(data)


class SupportOnlineToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        from support.services import can_agent_reply
        if not can_agent_reply(request.user):
            return Response({'detail': 'مجوز پاسخ‌گویی پشتیبانی برای شما فعال نشده است.'}, status=403)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        raw = request.data.get('online', not profile.is_support_online)
        online = raw if isinstance(raw, bool) else str(raw).lower() in {'1', 'true', 'yes', 'on'}
        profile.is_support_online = online
        profile.support_last_seen = timezone.now()
        profile.save(update_fields=['is_support_online', 'support_last_seen', 'updated_at'])
        return Response({
            'is_support_online': profile.is_support_online,
            'support_last_seen': profile.support_last_seen.isoformat(),
        })


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        f = request.FILES.get('avatar')
        if not f:
            return Response({'detail': 'فایل avatar الزامی است'}, status=400)
        if f.size > 5 * 1024 * 1024:
            return Response({'detail': 'حجم عکس حداکثر ۵ مگابایت'}, status=400)
        profile.avatar = f
        profile.save(update_fields=['avatar', 'updated_at'])
        url = request.build_absolute_uri(profile.avatar.url)
        return Response({'avatar_url': url, 'gender': profile.gender})
