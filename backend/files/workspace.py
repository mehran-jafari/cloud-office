from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, Correspondence, File, FileShare, Notification
from .notifications import push_notification
from .serializers import (
    ActivityLogSerializer,
    CorrespondenceSerializer,
    FileShareSerializer,
    UserLookupSerializer,
)

User = get_user_model()


def log_activity(user, action, title, detail='', target_type='', target_id=None):
    return ActivityLog.objects.create(
        user=user,
        action=action,
        title=title,
        detail=detail,
        target_type=target_type or '',
        target_id=target_id,
    )


class FileShareListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        direction = request.query_params.get('direction', 'received')
        if direction == 'sent':
            qs = FileShare.objects.filter(shared_by=request.user).select_related(
                'file', 'shared_with', 'shared_by'
            )
        else:
            qs = FileShare.objects.filter(shared_with=request.user).select_related(
                'file', 'shared_with', 'shared_by'
            )
        return Response(FileShareSerializer(qs, many=True).data)

    def post(self, request):
        serializer = FileShareSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        share = serializer.save()
        log_activity(
            request.user,
            'share',
            f'اشتراک فایل «{share.file.name}» با {share.shared_with.username}',
            detail=f'سطح دسترسی: {share.permission}',
            target_type='fileshare',
            target_id=share.id,
        )
        push_notification(
            share.shared_with,
            'share',
            f'فایل جدید به اشتراک گذاشته شد',
            body=f'«{share.file.name}» از طرف {request.user.get_username()}',
            link='/shared',
            send_email=True,
        )
        return Response(FileShareSerializer(share).data, status=status.HTTP_201_CREATED)


class FileShareDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            share = FileShare.objects.get(pk=pk)
        except FileShare.DoesNotExist:
            return Response({'detail': 'اشتراک پیدا نشد'}, status=404)
        if share.shared_by_id != request.user.id and share.shared_with_id != request.user.id:
            return Response({'detail': 'دسترسی ندارید'}, status=403)
        share.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ActivityLog.objects.filter(user=request.user)[:100]
        # managers see org-wide
        from support.permissions import has_role
        if has_role(request.user, 'owner', 'admin', 'auditor'):
            qs = ActivityLog.objects.select_related('user').all()[:200]
        return Response(ActivityLogSerializer(qs, many=True).data)


class CorrespondenceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        box = request.query_params.get('box', 'inbox')
        if box == 'sent':
            qs = Correspondence.objects.filter(sender=request.user).select_related('sender', 'recipient')
        else:
            qs = Correspondence.objects.filter(recipient=request.user).select_related('sender', 'recipient')
        return Response(CorrespondenceSerializer(qs, many=True).data)

    def post(self, request):
        recipient_id = request.data.get('recipient')
        subject = str(request.data.get('subject') or '').strip()
        body = str(request.data.get('body') or '').strip()
        priority = request.data.get('priority') or 'normal'
        if not recipient_id or not subject or not body:
            return Response({'detail': 'گیرنده، موضوع و متن الزامی است'}, status=400)
        try:
            recipient = User.objects.get(pk=recipient_id, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': 'گیرنده پیدا نشد'}, status=404)
        mail = Correspondence.objects.create(
            subject=subject[:300],
            body=body,
            sender=request.user,
            recipient=recipient,
            status='sent',
            priority=priority if priority in {'low', 'normal', 'high'} else 'normal',
        )
        log_activity(
            request.user,
            'mail_sent',
            f'ارسال نامه: {mail.subject}',
            detail=f'به {recipient.username}',
            target_type='mail',
            target_id=mail.id,
        )
        log_activity(
            recipient,
            'mail_received',
            f'دریافت نامه: {mail.subject}',
            detail=f'از {request.user.username}',
            target_type='mail',
            target_id=mail.id,
        )
        push_notification(
            recipient,
            'mail',
            f'نامه جدید: {mail.subject}',
            body=f'از {request.user.get_username()}',
            link='/mail',
        )
        return Response(CorrespondenceSerializer(mail).data, status=201)


class CorrespondenceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            mail = Correspondence.objects.select_related('sender', 'recipient').get(pk=pk)
        except Correspondence.DoesNotExist:
            return Response({'detail': 'نامه پیدا نشد'}, status=404)
        if mail.sender_id != request.user.id and mail.recipient_id != request.user.id:
            return Response({'detail': 'دسترسی ندارید'}, status=403)
        if mail.recipient_id == request.user.id and not mail.is_read:
            mail.is_read = True
            mail.save(update_fields=['is_read'])
        return Response(CorrespondenceSerializer(mail).data)


class UserLookupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        qs = User.objects.filter(is_active=True).exclude(pk=request.user.id)
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        return Response(UserLookupSerializer(qs.order_by('username')[:30], many=True).data)


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.models import StorageQuota
        from django.db.models import Sum
        files_count = File.objects.filter(owner=request.user).count()
        shared_count = FileShare.objects.filter(
            Q(shared_with=request.user) | Q(shared_by=request.user)
        ).count()
        open_mails = Correspondence.objects.filter(recipient=request.user, is_read=False).count()
        quota, _ = StorageQuota.objects.get_or_create(user=request.user)
        used = File.objects.filter(owner=request.user).aggregate(t=Sum('size_bytes'))['t'] or 0
        return Response({
            'files_count': files_count,
            'shared_count': shared_count,
            'open_mails': open_mails,
            'used_bytes': used,
            'allocated_bytes': quota.allocated_bytes,
            'used_gb': round(used / (1024 ** 3), 2),
            'allocated_gb': round(quota.allocated_bytes / (1024 ** 3), 2),
        })



class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)[:50]
        return Response([
            {
                'id': n.id,
                'kind': n.kind,
                'title': n.title,
                'body': n.body,
                'link': n.link,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            }
            for n in qs
        ])


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        latest = Notification.objects.filter(user=request.user).first()
        return Response({
            'count': count,
            'latest_id': latest.id if latest else None,
            'latest_title': latest.title if latest else None,
            'latest_body': latest.body if latest else '',
            'latest_link': latest.link if latest else '',
            'latest_kind': latest.kind if latest else None,
            'latest_at': latest.created_at.isoformat() if latest else None,
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get('ids')
        qs = Notification.objects.filter(user=request.user, is_read=False)
        if isinstance(ids, list) and ids:
            qs = qs.filter(id__in=ids)
        updated = qs.update(is_read=True)
        return Response({'marked': updated})


# ---------------------------------------------------------------------------
# Trash (سطل زباله)
# ---------------------------------------------------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
import secrets

from .models import File, Folder, PublicShareLink
from .serializers import FileSerializer, FolderSerializer, PublicShareLinkSerializer
from .notifications import push_notification


class TrashListView(APIView):
    """لیست آیتم‌های داخل سطل زباله."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = File.objects.filter(owner=request.user, is_deleted=True).order_by('-deleted_at')
        folders = Folder.objects.filter(owner=request.user, is_deleted=True).order_by('-deleted_at')
        return Response({
            'files': FileSerializer(files, many=True, context={'request': request}).data,
            'folders': FolderSerializer(folders, many=True, context={'request': request}).data,
        })


class TrashRestoreView(APIView):
    """بازیابی از سطل زباله."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get('file_ids') or []
        folder_ids = request.data.get('folder_ids') or []
        files = File.objects.filter(owner=request.user, is_deleted=True, id__in=file_ids)
        folders = Folder.objects.filter(owner=request.user, is_deleted=True, id__in=folder_ids)
        n_f = files.update(is_deleted=False, deleted_at=None, deleted_by=None)
        n_d = folders.update(is_deleted=False, deleted_at=None, deleted_by=None)
        # restore children of restored folders
        for folder in Folder.objects.filter(owner=request.user, id__in=folder_ids):
            File.objects.filter(folder=folder, owner=request.user, is_deleted=True).update(
                is_deleted=False, deleted_at=None, deleted_by=None
            )
        return Response({'restored_files': n_f, 'restored_folders': n_d})


class TrashPurgeView(APIView):
    """حذف دائمی از سطل زباله."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_ids = request.data.get('file_ids') or []
        folder_ids = request.data.get('folder_ids') or []
        empty_all = bool(request.data.get('empty_all'))
        if empty_all:
            files = File.objects.filter(owner=request.user, is_deleted=True)
            folders = Folder.objects.filter(owner=request.user, is_deleted=True)
        else:
            files = File.objects.filter(owner=request.user, is_deleted=True, id__in=file_ids)
            folders = Folder.objects.filter(owner=request.user, is_deleted=True, id__in=folder_ids)
        n_files = 0
        for f in files:
            if f.storage_key and default_storage.exists(f.storage_key):
                try:
                    default_storage.delete(f.storage_key)
                except Exception:
                    pass
            f.delete()
            n_files += 1
        n_folders = folders.count()
        folders.delete()
        return Response({'purged_files': n_files, 'purged_folders': n_folders})


# ---------------------------------------------------------------------------
# Public Share Links
# ---------------------------------------------------------------------------
class PublicShareLinkListCreateView(APIView):
    """لیست و ساخت لینک عمومی برای فایل."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PublicShareLink.objects.filter(created_by=request.user).select_related('file')
        file_id = request.query_params.get('file')
        if file_id:
            qs = qs.filter(file_id=file_id)
        return Response(PublicShareLinkSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        file_id = request.data.get('file')
        if not file_id:
            raise ValidationError({'file': 'الزامی است'})
        try:
            f = File.objects.get(pk=file_id, owner=request.user, is_deleted=False)
        except File.DoesNotExist:
            raise NotFound('فایل پیدا نشد')
        permission = request.data.get('permission') or 'view'
        if permission not in ('view', 'download'):
            permission = 'view'
        expires_at = request.data.get('expires_at')  # ISO string or null
        max_downloads = request.data.get('max_downloads')
        password = request.data.get('password') or ''
        note = (request.data.get('note') or '')[:200]
        token = secrets.token_urlsafe(32)
        link = PublicShareLink.objects.create(
            file=f,
            created_by=request.user,
            token=token,
            password_hash=make_password(password) if password else '',
            permission=permission,
            expires_at=expires_at or None,
            max_downloads=int(max_downloads) if max_downloads not in (None, '') else None,
            note=note,
        )
        return Response(PublicShareLinkSerializer(link, context={'request': request}).data, status=201)


class PublicShareLinkDetailView(APIView):
    """لغو / غیرفعال کردن لینک عمومی."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            link = PublicShareLink.objects.get(pk=pk, created_by=request.user)
        except PublicShareLink.DoesNotExist:
            raise NotFound()
        link.is_active = False
        link.save(update_fields=['is_active'])
        return Response(status=204)

    def patch(self, request, pk):
        try:
            link = PublicShareLink.objects.get(pk=pk, created_by=request.user)
        except PublicShareLink.DoesNotExist:
            raise NotFound()
        if 'is_active' in request.data:
            link.is_active = bool(request.data['is_active'])
        if 'expires_at' in request.data:
            link.expires_at = request.data['expires_at'] or None
        if 'max_downloads' in request.data:
            val = request.data['max_downloads']
            link.max_downloads = int(val) if val not in (None, '') else None
        link.save()
        return Response(PublicShareLinkSerializer(link, context={'request': request}).data)


class PublicShareAccessView(APIView):
    """دسترسی عمومی به فایل از طریق توکن (بدون لاگین)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, token):
        try:
            link = PublicShareLink.objects.select_related('file', 'created_by').get(token=token)
        except PublicShareLink.DoesNotExist:
            raise NotFound('لینک معتبر نیست')
        if link.is_expired():
            raise PermissionDenied('لینک منقضی یا غیرفعال شده است')
        password = request.data.get('password') or ''
        if not link.check_password(password):
            raise PermissionDenied('رمز عبور نادرست است')
        f = link.file
        if f.is_deleted:
            raise NotFound('فایل دیگر در دسترس نیست')
        data = {
            'file_id': f.id,
            'file_name': f.name,
            'mime_type': f.mime_type,
            'size_bytes': f.size_bytes,
            'permission': link.permission,
            'can_download': link.permission == 'download',
        }
        return Response(data)

    def get(self, request, token):
        """دانلود مستقیم (اگر permission=download و بدون رمز یا رمز در query)."""
        try:
            link = PublicShareLink.objects.select_related('file').get(token=token)
        except PublicShareLink.DoesNotExist:
            raise NotFound('لینک معتبر نیست')
        if link.is_expired():
            raise PermissionDenied('لینک منقضی یا غیرفعال شده است')
        password = request.query_params.get('password') or ''
        if link.password_hash and not link.check_password(password):
            raise PermissionDenied('رمز عبور لازم است')
        if link.permission != 'download':
            raise PermissionDenied('این لینک فقط برای مشاهده است')
        f = link.file
        if f.is_deleted or not f.storage_key:
            raise NotFound('فایل در دسترس نیست')
        link.download_count += 1
        link.save(update_fields=['download_count'])
        from django.http import FileResponse
        fh = default_storage.open(f.storage_key, 'rb')
        resp = FileResponse(fh, as_attachment=True, filename=f.name)
        return resp


# ---------------------------------------------------------------------------
# Advanced search + Admin audit
# ---------------------------------------------------------------------------
import re
from datetime import datetime
from django.db.models import Count
from django.utils.dateparse import parse_date, parse_datetime

SEARCH_MAX_LIMIT = 200
AUDIT_DEFAULT_LIMIT = 100
AUDIT_MAX_LIMIT = 5000  # سقف خروجی CSV / گزارش کامل


def _int_param(request, name, default=None, *, minimum=None, maximum=None):
    """پارامتر عددی query؛ مقدار نامعتبر → ۴۰۰ (نه ۵۰۰)."""
    raw = request.query_params.get(name)
    if raw in (None, ''):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: 'مقدار باید عدد صحیح باشد.'})
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


_DATE_ONLY_RE = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')


def _date_param(request, name, *, end=False):
    """تاریخ یا datetime ISO؛ مقدار نامعتبر → ۴۰۰.

    تاریخ بدون ساعت (YYYY-MM-DD) = ابتدای روز، یا با end=True انتهای روز.
    (در پایتون ۳.۱۱+ parse_datetime ورودی date-only را هم به نیمه‌شب تبدیل می‌کند،
    پس date-only باید قبل از آن جدا شود تا date_to کل آن روز را شامل شود.)
    """
    raw = (request.query_params.get(name) or '').strip()
    if not raw:
        return None
    try:
        if _DATE_ONLY_RE.match(raw):
            day = parse_date(raw)
            if day is None:
                raise ValueError(raw)
            clock = datetime.max.time().replace(microsecond=0) if end else datetime.min.time()
            value = datetime.combine(day, clock)
        else:
            value = parse_datetime(raw)
            if value is None:
                raise ValueError(raw)
    except ValueError:
        raise ValidationError({name: 'تاریخ نامعتبر است (فرمت YYYY-MM-DD یا ISO 8601).'})
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value


class AdvancedSearchView(APIView):
    """جستجوی پیشرفته فایل‌ها با فیلتر نوع، تاریخ، حجم و پوشه."""
    permission_classes = [IsAuthenticated]

    TYPE_MAP = {
        'pdf': ('.pdf', 'application/pdf'),
        'doc': ('.doc', '.docx', '.odt', '.rtf', 'word'),
        'sheet': ('.xls', '.xlsx', '.csv', '.ods', 'spreadsheet'),
        'image': ('.png', '.jpg', '.jpeg', '.gif', '.webp', 'image/'),
        'video': ('.mp4', '.webm', '.mov', 'video/'),
        'audio': ('.mp3', '.wav', '.ogg', 'audio/'),
    }

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        file_type = (request.query_params.get('type') or '').strip().lower()
        folder_id = request.query_params.get('folder')
        include_shared = request.query_params.get('include_shared') in ('1', 'true', 'yes')
        limit = _int_param(request, 'limit', 50, minimum=1, maximum=SEARCH_MAX_LIMIT)
        min_size = _int_param(request, 'min_size', minimum=0)
        max_size = _int_param(request, 'max_size', minimum=0)
        date_from = _date_param(request, 'date_from')
        date_to = _date_param(request, 'date_to', end=True)

        qs = File.objects.filter(is_deleted=False).select_related('owner', 'folder')

        # مالک، یا اشتراک‌شده با من — فقط اشتراک‌های فعال با can_view و منقضی‌نشده
        # (همان قواعد files.access.get_file_for_user)
        visible = Q(owner=request.user)
        if include_shared:
            now = timezone.now()
            shared_ids = (
                FileShare.objects.filter(shared_with=request.user, can_view=True)
                .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
                .values_list('file_id', flat=True)
            )
            visible |= Q(id__in=shared_ids)
        qs = qs.filter(visible)

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(mime_type__icontains=q))

        if folder_id not in (None, '', 'null'):
            try:
                qs = qs.filter(folder_id=int(folder_id))
            except (TypeError, ValueError):
                raise ValidationError({'folder': 'شناسه پوشه نامعتبر است.'})

        if file_type in self.TYPE_MAP:
            type_q = Q()
            for token in self.TYPE_MAP[file_type]:
                if token.startswith('.'):
                    type_q |= Q(name__iendswith=token)
                else:
                    type_q |= Q(mime_type__icontains=token)
            qs = qs.filter(type_q)

        if date_from:
            qs = qs.filter(updated_at__gte=date_from)
        if date_to:
            qs = qs.filter(updated_at__lte=date_to)
        if min_size is not None:
            qs = qs.filter(size_bytes__gte=min_size)
        if max_size is not None:
            qs = qs.filter(size_bytes__lte=max_size)

        items = list(qs.order_by('-updated_at', '-id')[:limit])
        return Response({
            'count': len(items),
            'results': FileSerializer(items, many=True, context={'request': request}).data,
        })


class AuditLogView(APIView):
    """گزارش audit برای ادمین / حسابرس — فیلترپذیر؛ summary بر اساس همان فیلترها."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from support.permissions import has_role
        if not (request.user.is_superuser or has_role(request.user, 'owner', 'admin', 'auditor')):
            raise PermissionDenied('دسترسی به گزارش audit ندارید')

        limit = _int_param(request, 'limit', AUDIT_DEFAULT_LIMIT, minimum=1, maximum=AUDIT_MAX_LIMIT)
        user_id = _int_param(request, 'user', minimum=1)
        action = (request.query_params.get('action') or '').strip()
        q = (request.query_params.get('q') or '').strip()
        date_from = _date_param(request, 'date_from')
        date_to = _date_param(request, 'date_to', end=True)

        qs = ActivityLog.objects.select_related('user')
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if action:
            qs = qs.filter(action=action)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(detail__icontains=q))
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        summary = (
            qs.order_by()
            .values('action')
            .annotate(count=Count('id'))
            .order_by('-count', 'action')[:20]
        )
        items = list(qs.order_by('-created_at', '-id')[:limit])
        return Response({
            'results': ActivityLogSerializer(items, many=True).data,
            'summary': list(summary),
            'count': len(items),
        })
