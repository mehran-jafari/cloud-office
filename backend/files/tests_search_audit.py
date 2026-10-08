from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import RoleDefinition, UserRole
from .models import ActivityLog, File, FileShare

User = get_user_model()


def make_file(owner, name, **kw):
    return File.objects.create(
        owner=owner,
        name=name,
        storage_key=f'tests/{owner.id}/{name}',
        mime_type=kw.pop('mime_type', 'text/plain'),
        size_bytes=kw.pop('size_bytes', 10),
        **kw,
    )


def give_role(user, code):
    role, _ = RoleDefinition.objects.get_or_create(code=code, defaults={'name': code})
    UserRole.objects.get_or_create(user=user, role=role)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class AdvancedSearchTests(TestCase):
    def setUp(self):
        self.me = User.objects.create_user('me', password='Password123!')
        self.other = User.objects.create_user('other', password='Password123!')
        self.client = APIClient()
        self.client.force_authenticate(self.me)
        self.mine = make_file(self.me, 'my-report.pdf', mime_type='application/pdf')

    def _share(self, file, **kw):
        defaults = {'shared_by': self.other, 'permission': 'view', 'can_view': True}
        defaults.update(kw)
        return FileShare.objects.create(file=file, shared_with=self.me, **defaults)

    def _names(self, **params):
        res = self.client.get('/api/files/search/', data=params)
        self.assertEqual(res.status_code, 200, res.content)
        return {row['name'] for row in res.json()['results']}

    def test_only_own_files_by_default(self):
        theirs = make_file(self.other, 'theirs.pdf')
        self._share(theirs)
        self.assertEqual(self._names(), {'my-report.pdf'})

    def test_shared_visible_file_is_included(self):
        self._share(make_file(self.other, 'shared-ok.pdf'))
        self.assertEqual(self._names(include_shared=1), {'my-report.pdf', 'shared-ok.pdf'})

    def test_share_without_can_view_is_excluded(self):
        self._share(make_file(self.other, 'hidden.pdf'), can_view=False)
        self.assertEqual(self._names(include_shared=1), {'my-report.pdf'})

    def test_expired_share_is_excluded(self):
        self._share(
            make_file(self.other, 'expired.pdf'),
            expires_at=timezone.now() - timedelta(days=1),
        )
        self._share(
            make_file(self.other, 'future.pdf'),
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(self._names(include_shared=1), {'my-report.pdf', 'future.pdf'})

    def test_trashed_files_are_excluded(self):
        make_file(self.me, 'old.pdf', is_deleted=True)
        self.assertEqual(self._names(), {'my-report.pdf'})

    def test_type_and_size_filters(self):
        make_file(self.me, 'pic.png', mime_type='image/png', size_bytes=5000)
        self.assertEqual(self._names(type='image'), {'pic.png'})
        self.assertEqual(self._names(min_size=1000), {'pic.png'})
        self.assertEqual(self._names(max_size=100), {'my-report.pdf'})

    def test_invalid_params_return_400_not_500(self):
        for params in (
            {'limit': 'abc'},
            {'min_size': 'x'},
            {'date_from': 'not-a-date'},
            {'folder': 'zzz'},
        ):
            res = self.client.get('/api/files/search/', data=params)
            self.assertEqual(res.status_code, 400, (params, res.content))

    def test_date_to_includes_the_whole_day(self):
        afternoon = timezone.now().replace(hour=15, minute=30, second=0, microsecond=0)
        File.objects.filter(pk=self.mine.pk).update(updated_at=afternoon)
        day = timezone.localtime(afternoon).date().isoformat()
        self.assertEqual(self._names(date_from=day, date_to=day), {'my-report.pdf'})

    def test_limit_is_clamped(self):
        res = self.client.get('/api/files/search/', data={'limit': -5})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

    def test_requires_authentication(self):
        res = APIClient().get('/api/files/search/')
        self.assertEqual(res.status_code, 401)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class AuditLogTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user('member', password='Password123!')
        self.auditor = User.objects.create_user('auditor', password='Password123!')
        self.root = User.objects.create_superuser(
            username='root',
            email='root@example.com',
            password='Password123!',
        )
        give_role(self.auditor, 'auditor')
        ActivityLog.objects.create(user=self.member, action='upload', title='a.txt')
        ActivityLog.objects.create(user=self.member, action='upload', title='b.txt')
        ActivityLog.objects.create(user=self.member, action='delete', title='c.txt')

    def _get(self, actor, **params):
        """actor = کاربر لاگین‌شده؛ params = query string (مثلاً user, action, limit)."""
        client = APIClient()
        client.force_authenticate(user=actor)
        return client.get('/api/files/audit/', data=params)

    def test_member_is_forbidden(self):
        self.assertEqual(self._get(self.member).status_code, 403)

    def test_auditor_and_superuser_allowed(self):
        self.assertEqual(self._get(self.auditor).status_code, 200)
        self.assertEqual(self._get(self.root).status_code, 200)

    def test_auditor_who_is_also_support_is_allowed(self):
        give_role(self.auditor, 'support')  # role_for() فقط بالاترین نقش را می‌داد
        self.assertEqual(self._get(self.auditor).status_code, 200)

    def test_summary_follows_filters(self):
        res = self._get(self.auditor, action='upload')
        body = res.json()
        self.assertEqual(body['count'], 2)
        self.assertEqual(body['summary'], [{'action': 'upload', 'count': 2}])

    def test_summary_without_filter_counts_everything(self):
        summary = {
            row['action']: row['count']
            for row in self._get(self.auditor).json()['summary']
        }
        self.assertEqual(summary['upload'], 2)
        self.assertEqual(summary['delete'], 1)

    def test_date_to_includes_the_whole_day(self):
        afternoon = timezone.now().replace(hour=15, minute=30, second=0, microsecond=0)
        ActivityLog.objects.all().update(created_at=afternoon)
        day = timezone.localtime(afternoon).date().isoformat()
        self.assertEqual(
            self._get(self.auditor, date_from=day, date_to=day).json()['count'],
            3,
        )

    def test_text_filter_and_limit(self):
        self.assertEqual(self._get(self.auditor, q='b.txt').json()['count'], 1)
        self.assertEqual(self._get(self.auditor, limit=2).json()['count'], 2)

    def test_delete_action_has_label(self):
        rows = self._get(self.auditor, action='delete').json()['results']
        self.assertEqual(rows[0]['action_label'], 'حذف')

    def test_invalid_params_return_400_not_500(self):
        for params in ({'limit': 'x'}, {'user': 'abc'}, {'date_to': '2026-99-99'}):
            res = self._get(self.auditor, **params)
            self.assertEqual(res.status_code, 400, (params, res.content))