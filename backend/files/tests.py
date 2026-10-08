import hashlib
import hmac
import json
from unittest.mock import patch
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from rest_framework.test import APIClient
from .models import File, FileVersion

class OnlyOfficeEditorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='owner', password='Password123!')
        self.other = get_user_model().objects.create_user(username='other', password='Password123!')
        key = default_storage.save('tests/original.docx', ContentFile(b'original'))
        self.file = File.objects.create(name='original.docx', owner=self.user, storage_key=key, mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', size_bytes=8)
        FileVersion.objects.create(
            file=self.file,
            version_number=1,
            storage_key=key,
            created_by=self.user,
            size_bytes=8,
            checksum=hashlib.sha256(b'original').hexdigest(),
            provider_key=f'test-initial-{self.file.id}',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_editor_config_contains_signed_download_and_callback(self):
        response = self.client.get(f'/api/files/{self.file.id}/editor-config/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('callbackUrl', response.data['config']['editorConfig'])
        self.assertIn('token=', response.data['config']['document']['url'])
        payload = jwt.decode(response.data['token'], settings.ONLYOFFICE_CALLBACK_SECRET, algorithms=['HS256'])
        self.assertEqual(payload['document']['key'], f'cloud-office-file-{self.file.id}-revision-{self.file.revision}')

    def test_other_user_cannot_get_editor_config(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/files/{self.file.id}/editor-config/').status_code, 404)

    def test_stale_document_key_is_rejected(self):
        payload = {'status': 2, 'key': 'cloud-office-file-1-revision-0', 'url': 'https://office.test/result.docx'}
        raw = json.dumps(payload).encode()
        signature = hmac.new(settings.ONLYOFFICE_CALLBACK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        response = self.client.post(f'/api/files/{self.file.id}/onlyoffice-callback/', data=raw, content_type='application/json', HTTP_X_ONLYOFFICE_SIGNATURE=signature)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(FileVersion.objects.filter(file=self.file).count(), 1)

    @patch('files.editor.download_provider_file', return_value=(b'new content', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
    def test_callback_requires_hmac_and_is_idempotent(self, _download):
        payload = {'status': 2, 'key': f'cloud-office-file-{self.file.id}-revision-{self.file.revision}', 'url': 'https://office.test/result.docx'}
        raw = json.dumps(payload).encode()
        signature = hmac.new(settings.ONLYOFFICE_CALLBACK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        response = self.client.post(f'/api/files/{self.file.id}/onlyoffice-callback/', data=raw, content_type='application/json', HTTP_X_ONLYOFFICE_SIGNATURE=signature)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FileVersion.objects.filter(file=self.file).count(), 2)
        response = self.client.post(f'/api/files/{self.file.id}/onlyoffice-callback/', data=raw, content_type='application/json', HTTP_X_ONLYOFFICE_SIGNATURE=signature)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FileVersion.objects.filter(file=self.file).count(), 2)

    @patch('files.editor.download_provider_file', return_value=(b'jwt saved content', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
    def test_callback_accepts_native_jwt_and_creates_version(self, _download):
        payload = {
            'status': 2,
            'key': f'cloud-office-file-{self.file.id}-revision-{self.file.revision}',
            'url': 'https://office.test/result.docx',
        }
        raw = json.dumps(payload).encode()
        token = jwt.encode({'document': {'key': payload['key']}}, settings.ONLYOFFICE_CALLBACK_SECRET, algorithm='HS256')
        response = self.client.post(
            f'/api/files/{self.file.id}/onlyoffice-callback/',
            data=raw,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        self.file.refresh_from_db()
        self.assertEqual(self.file.current_version, 2)
        self.assertEqual(FileVersion.objects.filter(file=self.file).count(), 2)

    def test_callback_rejects_invalid_jwt(self):
        payload = {
            'status': 2,
            'key': f'cloud-office-file-{self.file.id}-revision-{self.file.revision}',
            'url': 'https://office.test/result.docx',
        }
        raw = json.dumps(payload).encode()
        token = jwt.encode({'document': {'key': payload['key']}}, 'wrong-secret-' + ('x' * 24), algorithm='HS256')
        response = self.client.post(
            f'/api/files/{self.file.id}/onlyoffice-callback/',
            data=raw,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(FileVersion.objects.filter(file=self.file).count(), 1)

    @patch('files.editor.download_provider_file', return_value=(b'restored version content', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
    def test_version_can_be_restored_after_callback(self, _download):
        payload = {
            'status': 2,
            'key': f'cloud-office-file-{self.file.id}-revision-{self.file.revision}',
            'url': 'https://office.test/result.docx',
        }
        raw = json.dumps(payload).encode()
        signature = hmac.new(settings.ONLYOFFICE_CALLBACK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        response = self.client.post(
            f'/api/files/{self.file.id}/onlyoffice-callback/',
            data=raw,
            content_type='application/json',
            HTTP_X_ONLYOFFICE_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f'/api/files/{self.file.id}/restore/1/')
        self.assertEqual(response.status_code, 200)
        self.file.refresh_from_db()
        self.assertEqual(self.file.current_version, 1)
        self.assertEqual(self.file.revision, 3)
