from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from rest_framework.test import APIClient

from .models import File, FileShare


class ShareAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner', password='Password123!')
        self.viewer = User.objects.create_user(username='viewer', password='Password123!')
        key = default_storage.save('tests/share.txt', ContentFile(b'hello-share'))
        self.file = File.objects.create(
            name='share.txt',
            owner=self.owner,
            storage_key=key,
            mime_type='text/plain',
            size_bytes=11,
        )
        self.client = APIClient()

    def test_view_only_cannot_download(self):
        FileShare.objects.create(
            file=self.file,
            shared_with=self.viewer,
            shared_by=self.owner,
            permission='view',
            can_view=True,
            can_download=False,
            can_edit=False,
            can_reshare=False,
        )
        self.client.force_authenticate(self.viewer)
        r = self.client.get(f'/api/files/{self.file.id}/download/')
        self.assertEqual(r.status_code, 403)
        r2 = self.client.get(f'/api/files/{self.file.id}/download/?inline=1')
        self.assertEqual(r2.status_code, 200)

    def test_download_share_can_download(self):
        FileShare.objects.create(
            file=self.file,
            shared_with=self.viewer,
            shared_by=self.owner,
            permission='download',
            can_view=True,
            can_download=True,
            can_edit=False,
            can_reshare=False,
        )
        self.client.force_authenticate(self.viewer)
        r = self.client.get(f'/api/files/{self.file.id}/download/')
        self.assertEqual(r.status_code, 200)

    def test_stranger_gets_404(self):
        stranger = get_user_model().objects.create_user(username='stranger', password='Password123!')
        self.client.force_authenticate(stranger)
        r = self.client.get(f'/api/files/{self.file.id}/download/?inline=1')
        self.assertEqual(r.status_code, 404)
