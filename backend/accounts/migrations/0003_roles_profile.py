from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_roles(apps, schema_editor):
    RoleDefinition = apps.get_model('accounts', 'RoleDefinition')
    defaults = [
        ('owner', 'مالک سازمان', True, {
            'manage_users': True, 'manage_roles': True, 'manage_support': True,
            'reply_support': True, 'view_admin': True, 'view_files': True,
            'edit_files': True, 'view_mail': True, 'view_activity': True, 'view_remote': True,
        }),
        ('admin', 'مدیر سیستم', True, {
            'manage_users': True, 'manage_roles': False, 'manage_support': True,
            'reply_support': True, 'view_admin': True, 'view_files': True,
            'edit_files': True, 'view_mail': True, 'view_activity': True, 'view_remote': True,
        }),
        ('support', 'کارشناس پشتیبانی', True, {
            'manage_users': False, 'manage_roles': False, 'manage_support': False,
            'reply_support': True, 'view_admin': False, 'view_files': True,
            'edit_files': False, 'view_mail': True, 'view_activity': False, 'view_remote': True,
        }),
        ('auditor', 'حسابرس', True, {
            'manage_users': False, 'manage_roles': False, 'manage_support': False,
            'reply_support': False, 'view_admin': False, 'view_files': True,
            'edit_files': False, 'view_mail': True, 'view_activity': True, 'view_remote': False,
        }),
        ('member', 'کاربر فضای کاری', True, {
            'manage_users': False, 'manage_roles': False, 'manage_support': False,
            'reply_support': False, 'view_admin': False, 'view_files': True,
            'edit_files': True, 'view_mail': True, 'view_activity': True, 'view_remote': True,
        }),
    ]
    for code, name, is_system, perms in defaults:
        RoleDefinition.objects.get_or_create(code=code, defaults={
            'name': name, 'is_system': is_system, 'permissions': perms, 'description': name,
        })


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_accessrole'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RoleDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('permissions', models.JSONField(blank=True, default=dict)),
                ('is_system', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('notify_sms', models.BooleanField(default=False)),
                ('notify_bale', models.BooleanField(default=False)),
                ('notify_eitaa', models.BooleanField(default=False)),
                ('notify_telegram', models.BooleanField(default=False)),
                ('telegram_chat_id', models.CharField(blank=True, max_length=64)),
                ('bale_chat_id', models.CharField(blank=True, max_length=64)),
                ('eitaa_chat_id', models.CharField(blank=True, max_length=64)),
                ('avatar_color', models.CharField(default='#7667f7', max_length=20)),
                ('is_support_online', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='accounts.roledefinition')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('user', 'role')}},
        ),
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
    ]
