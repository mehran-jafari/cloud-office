from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from accounts.models import AccessRole, SupportAgentPermission
from support.models import Conversation

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class QuotaAndSupportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser('admin_test', password='Password123!')
        self.user = User.objects.create_user('user_test', password='Password123!')
        self.client = APIClient(); self.client.force_authenticate(self.admin)
        self.user_client = APIClient(); self.user_client.force_authenticate(self.user)

    def test_admin_can_update_quota(self):
        response = self.client.patch(f'/api/admin/users/{self.user.id}/quota/', {'allocated_bytes': 10 * 1024**3}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['allocated_bytes'], 10 * 1024**3)

    def test_support_reply_requires_explicit_permission(self):
        conversation = self.user_client.post('/api/support/conversations/', {'subject': 'Test', 'body': 'Hello'}, format='json').data
        denied = self.client.post(f"/api/support/conversations/{conversation['id']}/messages/", {'body': 'Reply'}, format='json')
        self.assertEqual(denied.status_code, 403)
        SupportAgentPermission.objects.create(user=self.admin, can_reply=True, granted_by=self.admin)
        allowed = self.client.post(f"/api/support/conversations/{conversation['id']}/messages/", {'body': 'Reply'}, format='json')
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(Conversation.objects.get(pk=conversation['id']).messages.filter(is_ai=False).count(), 2)

    def test_only_owner_can_change_role(self):
        response = self.client.patch(f'/api/admin/roles/{self.user.id}/', {'role': 'auditor'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessRole.objects.get(user=self.user).role, 'auditor')
        denied = self.user_client.patch(f'/api/admin/roles/{self.admin.id}/', {'role': 'member'}, format='json')
        self.assertEqual(denied.status_code, 403)
