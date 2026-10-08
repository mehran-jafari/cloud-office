from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('files', '0005_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='file',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='file',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_files', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='folder',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='folder',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='folder',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_folders', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='PublicShareLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('password_hash', models.CharField(blank=True, max_length=128)),
                ('permission', models.CharField(choices=[('view', 'فقط مشاهده'), ('download', 'مشاهده + دانلود')], default='view', max_length=20)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('max_downloads', models.PositiveIntegerField(blank=True, null=True)),
                ('download_count', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_public_links', to=settings.AUTH_USER_MODEL)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='public_links', to='files.file')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
