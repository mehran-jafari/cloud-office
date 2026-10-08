import hashlib
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import StorageQuota
from .access import get_file_for_user
from .convert import convert_file
from .models import File, FileShare, FileVersion, Folder
from .serializers import FileSerializer, FolderSerializer
from .workspace import log_activity

ALLOWED_UPLOAD_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf', 'txt',
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg',
    'mp4', 'webm', 'mov', 'mkv', 'mp3', 'wav', 'ogg', 'm4a', 'aac',
    'zip', 'csv',
}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB
SAFE_INLINE_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp',
    'application/pdf', 'text/plain', 'text/csv',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/aac', 'audio/webm',
    'video/mp4', 'video/webm', 'video/quicktime',
}

def validate_upload_file(uploaded):
    name = (getattr(uploaded, 'name', None) or '').lower()
    ext = name.rsplit('.', 1)[-1] if '.' in name else ''
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError({'detail': f'نوع فایل .{ext or "?"} مجاز نیست.'})
    size = getattr(uploaded, 'size', None) or 0
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError({'detail': 'حجم فایل بیش از ۱۰۰ مگابایت است.'})


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok', 'service': 'cloud-office-api'})


class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'upload'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['name']
    ordering_fields = ['name', 'updated_at', 'size_bytes']

    def get_queryset(self):
        return (
            File.objects.filter(owner=self.request.user, is_deleted=False)
            .select_related('owner')
            .order_by('-updated_at')
        )

    def perform_create(self, serializer):
        requested_size = int(serializer.validated_data.get('size_bytes') or 0)
        if requested_size < 0:
            raise ValidationError({'size_bytes': 'حجم فایل نمی‌تواند منفی باشد.'})
        quota, _ = StorageQuota.objects.get_or_create(user=self.request.user)
        used = (
            File.objects.filter(owner=self.request.user, is_deleted=False)
            .aggregate(total=Sum('size_bytes'))
            .get('total')
            or 0
        )
        if used + requested_size > quota.allocated_bytes:
            raise ValidationError({'detail': 'سهمیه فضای کاربر کافی نیست'})
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """پشتیبانی از آپلود واقعی فایل (multipart) + ایجاد متادیتا."""
        uploaded = request.FILES.get('file')
        if uploaded:
            validate_upload_file(uploaded)
            size = uploaded.size or 0
            quota, _ = StorageQuota.objects.get_or_create(user=request.user)
            used = (
                File.objects.filter(owner=request.user)
                .aggregate(total=Sum('size_bytes'))
                .get('total')
                or 0
            )
            if used + size > quota.allocated_bytes:
                return Response(
                    {'detail': 'سهمیه فضای کاربر کافی نیست'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ext = Path(uploaded.name).suffix
            storage_key = f'uploads/{request.user.id}/{uuid.uuid4().hex}{ext}'
            saved_path = default_storage.save(storage_key, uploaded)

            folder_id = request.data.get('folder')
            folder = None
            if folder_id:
                try:
                    folder = Folder.objects.get(pk=folder_id, owner=request.user)
                except Folder.DoesNotExist:
                    return Response({'detail': 'پوشه پیدا نشد'}, status=400)

            mime = getattr(uploaded, 'content_type', None) or 'application/octet-stream'
            obj = File.objects.create(
                name=uploaded.name[:255],
                owner=request.user,
                folder=folder,
                storage_key=saved_path,
                mime_type=mime,
                size_bytes=size,
            )
            with default_storage.open(saved_path, 'rb') as stored_file:
                checksum = hashlib.sha256(stored_file.read()).hexdigest()
            FileVersion.objects.create(
                file=obj,
                version_number=1,
                storage_key=saved_path,
                created_by=request.user,
                size_bytes=size,
                checksum=checksum,
                provider_key=f'upload-{obj.id}-{obj.revision}',
            )
            serializer = self.get_serializer(obj)
            log_activity(request.user, 'upload', f'آپلود فایل «{obj.name}»', target_type='file', target_id=obj.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user, is_deleted=False).order_by('name')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FileDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        inline = request.query_params.get('inline') in {'1', 'true', 'yes'}
        # پیش‌نمایش: view کافی است؛ دانلود واقعی: need_download
        obj, _share = get_file_for_user(
            request.user, pk, need_view=True, need_download=not inline, need_edit=False
        )
        if not obj.storage_key or not default_storage.exists(obj.storage_key):
            raise Http404('فایل روی دیسک پیدا نشد')
        fh = default_storage.open(obj.storage_key, 'rb')
        mime = (obj.mime_type or 'application/octet-stream').split(';', 1)[0].strip().lower()
        # پیش‌نمایش inline فقط برای انواع بی‌خطر؛ svg/html و ... همیشه attachment (جلوگیری از stored XSS)
        if inline and mime not in SAFE_INLINE_MIME_TYPES:
            inline = False
            if _share is not None and not _share.can_download:
                raise PermissionDenied('اجازه دانلود/کپی این فایل را ندارید.')
        response = FileResponse(fh, as_attachment=not inline, filename=obj.name)
        response['Content-Type'] = mime if (inline or mime in SAFE_INLINE_MIME_TYPES) else 'application/octet-stream'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class FileConvertView(APIView):
    """تبدیل PDF→Word یا Word→PDF؛ فایل جدید در فضای کاربر ذخیره می‌شود."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        target = str(request.data.get('target') or request.query_params.get('target') or '').strip()
        obj, _share = get_file_for_user(request.user, pk, need_view=True, need_download=True)
        # فقط مالک یا کسی با دانلود می‌تواند تبدیل کند؛ خروجی مال اوست
        try:
            new_file = convert_file(obj, request.user, target)
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError({'detail': str(e)})
        return Response(FileSerializer(new_file, context={'request': request}).data, status=status.HTTP_201_CREATED)


class FileBulkActionView(APIView):
    """عملیات دسته‌ای شبیه سیستم‌عامل: rename / move / copy / delete."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = str(request.data.get('action') or '').strip().lower()
        file_ids = request.data.get('file_ids') or []
        folder_ids = request.data.get('folder_ids') or []
        if not isinstance(file_ids, list):
            file_ids = []
        if not isinstance(folder_ids, list):
            folder_ids = []

        files = list(File.objects.filter(owner=request.user, is_deleted=False, id__in=file_ids))
        folders = list(Folder.objects.filter(owner=request.user, is_deleted=False, id__in=folder_ids))

        if action == 'rename':
            # فقط یک آیتم
            new_name = str(request.data.get('name') or '').strip()
            if not new_name:
                raise ValidationError({'detail': 'نام جدید الزامی است'})
            if len(files) == 1 and not folders:
                f = files[0]
                f.name = new_name[:255]
                f.save(update_fields=['name', 'updated_at'])
                log_activity(request.user, 'rename', f'تغییر نام به «{f.name}»', target_type='file', target_id=f.id)
                return Response(FileSerializer(f, context={'request': request}).data)
            if len(folders) == 1 and not files:
                folder = folders[0]
                folder.name = new_name[:255]
                folder.save(update_fields=['name'])
                return Response(FolderSerializer(folder, context={'request': request}).data)
            raise ValidationError({'detail': 'برای تغییر نام فقط یک آیتم انتخاب کنید'})

        if action == 'move':
            target_folder_id = request.data.get('target_folder_id')
            target = None
            if target_folder_id not in (None, '', 0, '0'):
                try:
                    target = Folder.objects.get(pk=target_folder_id, owner=request.user)
                except Folder.DoesNotExist:
                    raise ValidationError({'detail': 'پوشه مقصد پیدا نشد'})
            for f in files:
                f.folder = target
                f.save(update_fields=['folder', 'updated_at'])
            for folder in folders:
                if target and folder.id == target.id:
                    continue
                # جلوگیری از parent حلقه‌ای ساده
                if target and target.parent_id == folder.id:
                    continue
                folder.parent = target
                folder.save(update_fields=['parent'])
            log_activity(request.user, 'move', f'انتقال {len(files)} فایل و {len(folders)} پوشه')
            return Response({'moved_files': len(files), 'moved_folders': len(folders)})

        if action == 'copy':
            target_folder_id = request.data.get('target_folder_id')
            target = None
            if target_folder_id not in (None, '', 0, '0'):
                try:
                    target = Folder.objects.get(pk=target_folder_id, owner=request.user)
                except Folder.DoesNotExist:
                    raise ValidationError({'detail': 'پوشه مقصد پیدا نشد'})
            created = []
            for f in files:
                new_name = f.name
                base = Path(f.name)
                # اگر هم‌نام باشد پیشوند کپی
                if File.objects.filter(owner=request.user, folder=target, name=new_name).exists():
                    new_name = f'{base.stem} - کپی{base.suffix}'
                storage_key = ''
                size = f.size_bytes
                if f.storage_key and default_storage.exists(f.storage_key):
                    with default_storage.open(f.storage_key, 'rb') as fh:
                        data = fh.read()
                    storage_key = default_storage.save(
                        f'uploads/{request.user.id}/{uuid.uuid4().hex}{base.suffix}',
                        ContentFile(data),
                    )
                    size = len(data)
                obj = File.objects.create(
                    name=new_name[:255],
                    owner=request.user,
                    folder=target,
                    storage_key=storage_key,
                    mime_type=f.mime_type,
                    size_bytes=size,
                )
                created.append(obj)
            for folder in folders:
                # کپی سطحی پوشه خالی با همان نام
                name = folder.name
                if Folder.objects.filter(owner=request.user, parent=target, name=name).exists():
                    name = f'{name} - کپی'
                Folder.objects.create(name=name, owner=request.user, parent=target)
            log_activity(request.user, 'copy', f'کپی {len(created)} فایل')
            return Response({
                'copied': len(created),
                'files': FileSerializer(created, many=True, context={'request': request}).data,
            }, status=status.HTTP_201_CREATED)

        if action == 'delete':
            from django.utils import timezone
            now = timezone.now()
            n_files = len(files)
            n_folders = len(folders)
            # soft-delete (سطل زباله)
            for f in files:
                f.is_deleted = True
                f.deleted_at = now
                f.deleted_by = request.user
                f.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
            for folder in folders:
                folder.is_deleted = True
                folder.deleted_at = now
                folder.deleted_by = request.user
                folder.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
                # soft-delete children files
                File.objects.filter(folder=folder, owner=request.user, is_deleted=False).update(
                    is_deleted=True, deleted_at=now, deleted_by=request.user
                )
            log_activity(request.user, 'delete', f'انتقال به سطل زباله: {n_files} فایل و {n_folders} پوشه')
            return Response({'deleted_files': n_files, 'deleted_folders': n_folders, 'soft_delete': True})

        raise ValidationError({'detail': 'action نامعتبر است (rename|move|copy|delete)'})
