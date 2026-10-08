from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from accounts.models import SupportAgentPermission

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class RemoteSessionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user('remote_owner', password='Password123!')
        self.agent = User.objects.create_user('remote_agent', password='Password123!', is_staff=True)
        self.other = User.objects.create_user('remote_other', password='Password123!')
        SupportAgentPermission.objects.update_or_create(user=self.agent, defaults={'can_reply': True, 'granted_by': self.agent})

    def test_consent_first_session_flow(self):
        owner_client = APIClient(); owner_client.force_authenticate(self.owner)
        created = owner_client.post('/api/support/remote-sessions/', {'mode': 'screen_share'}, format='json')
        self.assertEqual(created.status_code, 201); self.assertEqual(created.data['status'], 'pending')
        self.assertIsNotNone(created.data['conversation'])
        code = created.data['code']; session_id = created.data['id']
        agent_client = APIClient(); agent_client.force_authenticate(self.agent)
        joined = agent_client.post('/api/support/remote-sessions/join/', {'code': code}, format='json')
        self.assertEqual(joined.status_code, 200); self.assertEqual(joined.data['agent'], self.agent.id)
        consented = owner_client.post(f'/api/support/remote-sessions/{session_id}/consent/')
        self.assertEqual(consented.status_code, 200); self.assertEqual(consented.data['status'], 'active')
        ended = agent_client.post(f'/api/support/remote-sessions/{session_id}/end/')
        self.assertEqual(ended.status_code, 200); self.assertEqual(ended.data['status'], 'ended')

    def test_other_user_cannot_view_session(self):
        owner_client = APIClient(); owner_client.force_authenticate(self.owner)
        created = owner_client.post('/api/support/remote-sessions/', {}, format='json')
        other_client = APIClient(); other_client.force_authenticate(self.other)
        response = other_client.get(f"/api/support/remote-sessions/{created.data['id']}/")
        self.assertEqual(response.status_code, 403)

    def test_unassigned_support_agent_cannot_access_active_session(self):
        User = get_user_model()
        second_agent = User.objects.create_user('second_agent', password='Password123!', is_staff=True)
        SupportAgentPermission.objects.update_or_create(user=second_agent, defaults={'can_reply': True, 'granted_by': self.agent})
        owner_client = APIClient(); owner_client.force_authenticate(self.owner)
        created = owner_client.post('/api/support/remote-sessions/', {}, format='json')
        agent_client = APIClient(); agent_client.force_authenticate(self.agent)
        agent_client.post('/api/support/remote-sessions/join/', {'code': created.data['code']}, format='json')
        owner_client.post(f"/api/support/remote-sessions/{created.data['id']}/consent/")
        second_client = APIClient(); second_client.force_authenticate(second_agent)
        self.assertEqual(second_client.get(f"/api/support/remote-sessions/{created.data['id']}/").status_code, 403)
        self.assertEqual(second_client.post(f"/api/support/remote-sessions/{created.data['id']}/end/").status_code, 403)
