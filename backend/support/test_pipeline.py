import os
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import SupportAgentPermission, UserProfile
from files.editor import validate_provider_url
from support import services
from support.models import Conversation

NO_AI_KEY = {'AI_API_KEY': '', 'OPENAI_API_KEY': ''}


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class SupportPipelineTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user('cust', password='Password123!')
        self.agent = User.objects.create_user('agent', password='Password123!')
        SupportAgentPermission.objects.create(user=self.agent, can_reply=True, granted_by=self.agent)
        self.c = APIClient(); self.c.force_authenticate(self.customer)
        self.a = APIClient(); self.a.force_authenticate(self.agent)

    def _make_agent_online(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.agent)
        profile.is_support_online = True
        profile.support_last_seen = timezone.now()
        profile.save()

    @mock.patch.dict(os.environ, NO_AI_KEY)
    def test_ai_replies_when_no_agent_online(self):
        r = self.c.post('/api/support/conversations/', {'subject': 'x', 'body': 'سلام'}, format='json')
        self.assertEqual(r.status_code, 201)
        conv = Conversation.objects.get(pk=r.data['id'])
        self.assertTrue(conv.messages.filter(is_ai=True).exists())

    @mock.patch.dict(os.environ, NO_AI_KEY)
    def test_no_ai_when_agent_online(self):
        self._make_agent_online()
        r = self.c.post('/api/support/conversations/', {'subject': 'x', 'body': 'سلام'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertFalse(Conversation.objects.get(pk=r.data['id']).messages.filter(is_ai=True).exists())

    def test_online_requires_reply_permission(self):
        denied = self.c.post('/api/support/presence/', {'online': True}, format='json')
        self.assertEqual(denied.status_code, 403)
        ok = self.a.post('/api/support/presence/', {'online': True}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(len(services.get_online_agents()), 1)

    def test_escalation_skips_ai_handling_and_caps(self):
        ai_conv = Conversation.objects.create(user=self.customer, subject='a', status='ai_handling',
                                              next_escalate_at=timezone.now() - timedelta(minutes=1))
        waiting = Conversation.objects.create(user=self.customer, subject='b', status='waiting_agent',
                                              last_user_message_at=timezone.now(),
                                              next_escalate_at=timezone.now() - timedelta(minutes=1),
                                              escalation_count=services.MAX_ESCALATIONS - 1)
        services.run_escalations()
        ai_conv.refresh_from_db(); waiting.refresh_from_db()
        self.assertEqual(ai_conv.status, 'ai_handling')
        self.assertEqual(waiting.status, 'escalated')
        self.assertIsNone(waiting.next_escalate_at)


class ProviderUrlTests(SimpleTestCase):
    @override_settings(ONLYOFFICE_URL='http://onlyoffice.internal', ONLYOFFICE_ALLOWED_HOSTS=[])
    def test_blocks_file_scheme_and_foreign_hosts(self):
        with self.assertRaises(ValueError):
            validate_provider_url('file:///etc/passwd')
        with self.assertRaises(ValueError):
            validate_provider_url('http://169.254.169.254/latest/meta-data')
        self.assertTrue(validate_provider_url('http://onlyoffice.internal/cache/x.docx'))

    def test_provider_module_imports(self):
        import ai.provider  # noqa: F401
