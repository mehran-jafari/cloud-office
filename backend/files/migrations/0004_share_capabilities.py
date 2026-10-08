
from django.db import migrations, models

def backfill(apps, schema_editor):
    FileShare = apps.get_model('files', 'FileShare')
    for s in FileShare.objects.all():
        level = s.permission or 'view'
        s.can_view = True
        s.can_download = level in ('download', 'edit', 'full')
        s.can_edit = level in ('edit', 'full')
        s.can_reshare = level == 'full'
        s.save()

class Migration(migrations.Migration):
    dependencies = [('files', '0003_fileshare_activity_mail')]
    operations = [
        migrations.AddField(model_name='fileshare', name='can_view', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='fileshare', name='can_download', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='fileshare', name='can_edit', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='fileshare', name='can_reshare', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='fileshare', name='expires_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(
            model_name='fileshare',
            name='permission',
            field=models.CharField(
                choices=[
                    ('view', 'فقط مشاهده'),
                    ('download', 'مشاهده + دانلود/کپی'),
                    ('edit', 'مشاهده + دانلود + ویرایش'),
                    ('full', 'کامل (ویرایش + اشتراک مجدد)'),
                ],
                default='view',
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
