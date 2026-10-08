from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'], PUBLIC_APP_URL='',
                   CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
class AgentInstallerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_script_contains_server_url_not_localhost_default(self):
        r = self.client.get('/api/desk/agent/linux/', {'app': 'http://localhost:3000'})
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('APP_URL="http://localhost:3000"', body)
        self.assertNotIn('__APP_URL__', body)

    def test_windows_script_is_crlf_and_ascii(self):
        r = self.client.get('/api/desk/agent/windows/', {'app': 'http://localhost:3000'})
        body = r.content
        self.assertIn(b'\r\n', body)
        body.decode('ascii')

    def test_malicious_or_unknown_app_param_is_ignored(self):
        for bad in ["http://evil.example", "http://localhost:3000'; rm -rf ~ #", 'javascript:alert(1)']:
            r = self.client.get('/api/desk/agent/macos/', {'app': bad})
            self.assertEqual(r.status_code, 200)
            self.assertNotIn('evil.example', r.content.decode())
            self.assertNotIn('rm -rf', r.content.decode())

    def test_unknown_platform_404(self):
        self.assertEqual(self.client.get('/api/desk/agent/amiga/').status_code, 404)
