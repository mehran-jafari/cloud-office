import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('files', '0005_notification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AIQuota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monthly_tokens', models.PositiveIntegerField(default=200000)),
                ('used_tokens', models.PositiveIntegerField(default=0)),
                ('period_start', models.DateField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ai_quota', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AIUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('draft_mail', 'پیش‌نویس نامه'), ('summarize', 'خلاصه‌سازی'), ('support_reply', 'پیشنهاد پاسخ پشتیبانی'), ('stt', 'گفتار به متن'), ('embed', 'بردارسازی فایل'), ('semantic_search', 'جست‌وجوی معنایی'), ('meeting_summary', 'خلاصه جلسه')], max_length=40)),
                ('tokens_used', models.PositiveIntegerField(default=0)),
                ('model_name', models.CharField(blank=True, max_length=80)),
                ('success', models.BooleanField(default=True)),
                ('detail', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_usage_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='FileEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(blank=True, max_length=80)),
                ('dims', models.PositiveIntegerField(default=0)),
                ('vector', models.JSONField(blank=True, default=list)),
                ('text_preview', models.CharField(blank=True, max_length=500)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='embedding', to='files.file')),
            ],
        ),
    ]
