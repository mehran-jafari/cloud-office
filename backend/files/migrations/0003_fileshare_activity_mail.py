from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0002_file_revision_fileversion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permission', models.CharField(choices=[('view', 'فقط مشاهده'), ('download', 'مشاهده و دانلود/کپی'), ('edit', 'ویرایش')], default='view', max_length=20)),
                ('message', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shares', to='files.file')),
                ('shared_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_shares', to=settings.AUTH_USER_MODEL)),
                ('shared_with', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_shares', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('file', 'shared_with')},
            },
        ),
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('upload', 'آپلود فایل'), ('download', 'دانلود فایل'), ('share', 'اشتراک‌گذاری'), ('edit', 'ویرایش'), ('login', 'ورود'), ('mail_sent', 'ارسال نامه'), ('mail_received', 'دریافت نامه'), ('support', 'پشتیبانی'), ('remote', 'اتصال امن'), ('admin', 'عملیات مدیریتی'), ('other', 'سایر')], default='other', max_length=30)),
                ('title', models.CharField(max_length=255)),
                ('detail', models.TextField(blank=True)),
                ('target_type', models.CharField(blank=True, max_length=50)),
                ('target_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Correspondence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=300)),
                ('body', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'پیش‌نویس'), ('sent', 'ارسال‌شده'), ('received', 'دریافت‌شده'), ('archived', 'بایگانی')], default='sent', max_length=20)),
                ('priority', models.CharField(choices=[('low', 'کم'), ('normal', 'عادی'), ('high', 'فوری')], default='normal', max_length=10)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='files.correspondence')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_mails', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_mails', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
