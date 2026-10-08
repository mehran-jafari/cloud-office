import desk.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('desk_id', models.CharField(default=desk.models.generate_desk_id, max_length=9, unique=True)),
                ('token', models.CharField(default=desk.models.generate_token, max_length=64, unique=True)),
                ('alias', models.CharField(blank=True, default='', max_length=80)),
                ('password', models.CharField(default=desk.models.generate_password, max_length=32)),
                ('hostname', models.CharField(blank=True, default='', max_length=120)),
                ('os_name', models.CharField(blank=True, default='', max_length=80)),
                ('online', models.BooleanField(default=False)),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='desk_devices', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-last_seen']},
        ),
        migrations.CreateModel(
            name='DeskConference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=12, unique=True)),
                ('title', models.CharField(blank=True, default='', max_length=120)),
                ('status', models.CharField(default='active', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosted_conferences', to='desk.device')),
            ],
        ),
        migrations.CreateModel(
            name='DeskSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(default=desk.models.generate_token, max_length=64, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('ended', 'Ended'), ('rejected', 'Rejected')], default='pending', max_length=16)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_sessions', to='desk.device')),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosted_sessions', to='desk.device')),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='AddressBookEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('desk_id', models.CharField(max_length=9)),
                ('alias', models.CharField(blank=True, default='', max_length=80)),
                ('last_connected', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='desk.device')),
            ],
            options={'ordering': ['-last_connected', '-created_at'], 'unique_together': {('owner', 'desk_id')}},
        ),
    ]
