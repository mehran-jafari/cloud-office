from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_gender_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='support_last_seen',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_support_offline',
            field=models.BooleanField(
                default=True,
                help_text='اگر آفلاین بودم برای پیام‌های پشتیبانی جدید اعلان پیام‌رسان بگیرم',
            ),
        ),
    ]
