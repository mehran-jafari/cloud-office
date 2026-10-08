import hashlib
import hmac
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import jwt
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import get_file_for_user
from .models import File, FileVersion
from accounts.models import StorageQuota

SAVE_STATUSES = {2, 6}  # ready-for-saving and force-save
ERROR_STATUSES = {3, 7}


def owned_file(user, file_id, *, need_edit=True):
    """مالک یا کاربر با اشتراک ویرایش (یا مشاهده در حالت read-only)."""
    obj, share = get_file_for_user(
        user, file_id, need_view=True, need_edit=need_edit, need_download=False
    )
    return obj



def extension_info(name):
    ext = Path(name).suffix.lower().lstrip('.')
    if ext in {'doc', 'docx', 'odt', 'rtf', 'txt'}: return 'word', ext or 'docx'
    if ext in {'xls', 'xlsx', 'ods', 'csv'}: return 'cell', ext or 'xlsx'
    if ext in {'ppt', 'pptx', 'odp'}: return 'slide', ext or 'pptx'
    raise ValueError('This file type is not supported by OnlyOffice')


def signed_download_token(file_obj, user_id):
    return signing.dumps({'file_id': file_obj.id, 'user_id': user_id, 'revision': file_obj.revision}, salt=settings.EDITOR_SIGNING_SALT)


def verify_callback(request):
    provided = request.headers.get('X-OnlyOffice-Signature', '').removeprefix('sha256=')
    expected = hmac.new(settings.ONLYOFFICE_CALLBACK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if provided and hmac.compare_digest(provided, expected): return True
    authorization = request.headers.get('Authorization', '')
    if authorization.startswith('Bearer '):
        try:
            jwt.decode(authorization[7:], settings.ONLYOFFICE_CALLBACK_SECRET, algorithms=['HS256'])
            return True
        except jwt.PyJWTError:
            pass
    return False


def provider_key(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _allowed_provider_hosts():
    hosts = {h.lower() for h in getattr(settings, 'ONLYOFFICE_ALLOWED_HOSTS', []) if h}
    configured = urlparse(settings.ONLYOFFICE_URL or '').hostname
    if configured:
        hosts.add(configured.lower())
    return hosts


def validate_provider_url(url):
    """فقط http/https و فقط از میزبان‌های Document Server مجاز (جلوگیری از SSRF / file://)."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError('invalid provider url')
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('provider url scheme is not allowed')
    if parsed.hostname.lower() not in _allowed_provider_hosts():
        raise ValueError('provider url host is not allowed')
    return url


def download_provider_file(url):
    validate_provider_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': 'CloudOffice/1.0'})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=30) as response:
        content_type = response.headers.get('Content-Type', 'application/octet-stream').split(';', 1)[0]
        try:
            length = int(response.headers.get('Content-Length', '0') or 0)
        except ValueError:
            length = 0
        if length > settings.EDITOR_MAX_DOWNLOAD_BYTES: raise ValueError('provider file is too large')
        content = response.read(settings.EDITOR_MAX_DOWNLOAD_BYTES + 1)
    if len(content) > settings.EDITOR_MAX_DOWNLOAD_BYTES: raise ValueError('provider file is too large')
    return content, content_type


def _editor_user_from_payload(payload, fallback):
    """کاربری که واقعاً ویرایش کرده (اگر در payload باشد و فعال باشد)، وگرنه fallback."""
    from django.contrib.auth import get_user_model
    users = payload.get('users')
    if isinstance(users, list) and users:
        try:
            uid = int(users[0])
        except (TypeError, ValueError):
            return fallback
        user = get_user_model().objects.filter(pk=uid, is_active=True).first()
        if user:
            return user
    return fallback


class EditorConfigView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        file_obj, share = get_file_for_user(request.user, pk, need_view=True, need_edit=False)
        can_edit = share is None or share.can_edit
        try: document_type, file_type = extension_info(file_obj.name)
        except ValueError as exc: return Response({'detail': str(exc)}, status=415)
        if not file_obj.storage_key: return Response({'detail': 'فایل هنوز در storage ثبت نشده است'}, status=409)
        token = signed_download_token(file_obj, request.user.id)
        base = settings.APP_PUBLIC_URL or request.build_absolute_uri('/').rstrip('/')
        download_url = f'{base}{reverse("editor-download", kwargs={"pk": file_obj.id})}?token={signing.b64_encode(token.encode()).decode()}'
        callback_url = f'{base}{reverse("onlyoffice-callback", kwargs={"pk": file_obj.id})}'
        key = f'cloud-office-file-{file_obj.id}-revision-{file_obj.revision}'
        config = {
            'document': {
                'fileType': file_type,
                'key': key,
                'title': file_obj.name,
                'url': download_url,
            },
            'documentType': document_type,
            'editorConfig': {
                'mode': 'edit' if can_edit else 'view',
                'callbackUrl': callback_url,
                'user': {
                    'id': str(request.user.id),
                    'name': request.user.get_full_name() or request.user.username,
                },
            },
        }
        # Native OnlyOffice JWT lets the Document Server authenticate callbacks
        # with Authorization: Bearer <token> using the same HS256 secret.
        config_token = jwt.encode(config, settings.ONLYOFFICE_CALLBACK_SECRET, algorithm='HS256')
        return Response({
            'documentServerUrl': settings.ONLYOFFICE_URL,
            'config': config,
            'token': config_token,
        })


class EditorDownloadView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        raw = request.query_params.get('token', '')
        try:
            token = signing.b64_decode(raw.encode()).decode()
            data = signing.loads(token, salt=settings.EDITOR_SIGNING_SALT, max_age=settings.EDITOR_URL_TTL_SECONDS)
            if int(data['file_id']) != int(pk): raise ValueError('file mismatch')
            file_obj = File.objects.get(id=pk, revision=data['revision'])
        except (signing.BadSignature, signing.SignatureExpired, ValueError, KeyError, TypeError, File.DoesNotExist):
            return Response({'detail': 'download token نامعتبر یا منقضی است'}, status=403)
        if not file_obj.storage_key or not default_storage.exists(file_obj.storage_key): return Response({'detail': 'فایل پیدا نشد'}, status=404)
        return FileResponse(default_storage.open(file_obj.storage_key, 'rb'), as_attachment=False, filename=file_obj.name, content_type=file_obj.mime_type)


class OnlyOfficeCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request, pk):
        if not verify_callback(request): return Response({'error': 1, 'detail': 'invalid callback signature'}, status=401)
        try: payload = json.loads(request.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError): return Response({'error': 1, 'detail': 'invalid JSON'}, status=400)
        if not isinstance(payload, dict): return Response({'error': 1, 'detail': 'invalid payload'}, status=400)
        try: file_obj = File.objects.get(id=pk)
        except File.DoesNotExist: return Response({'error': 1, 'detail': 'file not found'}, status=404)
        try: status_code = int(payload.get('status', 0))
        except (TypeError, ValueError): return Response({'error': 1, 'detail': 'invalid status'}, status=400)
        provider_id = provider_key(payload)
        if FileVersion.objects.filter(provider_key=provider_id).exists(): return Response({'error': 0}, status=200)
        expected_key = f'cloud-office-file-{file_obj.id}-revision-{file_obj.revision}'
        if payload.get('key') != expected_key:
            return Response({'error': 1, 'detail': 'stale or unknown document key'}, status=409)
        if status_code in ERROR_STATUSES: return Response({'error': 1}, status=200)
        if status_code not in SAVE_STATUSES: return Response({'error': 0}, status=200)
        source_url = payload.get('url')
        if not source_url: return Response({'error': 1, 'detail': 'callback url missing'}, status=400)
        try: content, content_type = download_provider_file(source_url)
        except Exception: return Response({'error': 1}, status=502)
        checksum = hashlib.sha256(content).hexdigest()
        with transaction.atomic():
            locked = File.objects.select_for_update().get(pk=file_obj.pk)
            if FileVersion.objects.filter(provider_key=provider_id).exists(): return Response({'error': 0}, status=200)
            quota, _ = StorageQuota.objects.get_or_create(user=locked.owner)
            current_usage = File.objects.filter(owner=locked.owner).aggregate(total=Sum('size_bytes')).get('total') or 0
            if current_usage - locked.size_bytes + len(content) > quota.allocated_bytes:
                return Response({'error': 1, 'detail': 'سهمیه فضای کاربر کافی نیست'}, status=507)
            next_version = (locked.versions.order_by('-version_number').values_list('version_number', flat=True).first() or locked.current_version) + 1
            filename = f'files/{locked.id}/versions/{next_version}-{uuid4().hex}-{Path(locked.name).name}'
            saved_key = default_storage.save(filename, ContentFile(content))
            version = FileVersion.objects.create(file=locked, version_number=next_version, storage_key=saved_key, created_by=_editor_user_from_payload(payload, locked.owner), size_bytes=len(content), checksum=checksum, provider_key=provider_id)
            locked.storage_key = saved_key
            locked.size_bytes = len(content)
            locked.mime_type = content_type or mimetypes.guess_type(locked.name)[0] or 'application/octet-stream'
            locked.current_version = version.version_number
            locked.revision += 1
            locked.save(update_fields=['storage_key', 'size_bytes', 'mime_type', 'current_version', 'revision', 'updated_at'])
        return Response({'error': 0}, status=200)


class FileVersionsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        file_obj, _share = get_file_for_user(request.user, pk, need_view=True, need_edit=False)
        return Response([{'version': v.version_number, 'size_bytes': v.size_bytes, 'checksum': v.checksum, 'created_at': v.created_at, 'created_by': v.created_by.get_username()} for v in file_obj.versions.select_related('created_by').all()])


class RestoreVersionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk, version):
        file_obj, _share = get_file_for_user(request.user, pk, need_view=True, need_edit=True)
        with transaction.atomic():
            version_obj = file_obj.versions.get(version_number=version)
            file_obj.storage_key = version_obj.storage_key
            file_obj.size_bytes = version_obj.size_bytes
            file_obj.current_version = version_obj.version_number
            file_obj.revision += 1
            file_obj.save(update_fields=['storage_key', 'size_bytes', 'current_version', 'revision', 'updated_at'])
        return Response({'current_version': file_obj.current_version, 'revision': file_obj.revision})
