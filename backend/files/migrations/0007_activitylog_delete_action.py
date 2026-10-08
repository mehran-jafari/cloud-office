from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0006_trash_and_public_links'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(
                choices=[
                    ('upload', 'آپلود فایل'),
                    ('download', 'دانلود فایل'),
                    ('share', 'اشتراک‌گذاری'),
                    ('edit', 'ویرایش'),
                    ('delete', 'حذف'),
                    ('login', 'ورود'),
                    ('mail_sent', 'ارسال نامه'),
                    ('mail_received', 'دریافت نامه'),
                    ('support', 'پشتیبانی'),
                    ('remote', 'اتصال امن'),
                    ('admin', 'عملیات مدیریتی'),
                    ('other', 'سایر'),
                ],
                default='other',
                max_length=30,
            ),
        ),
    ]
