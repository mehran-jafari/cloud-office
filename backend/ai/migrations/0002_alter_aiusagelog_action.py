from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ai', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aiusagelog',
            name='action',
            field=models.CharField(
                choices=[
                    ('draft_mail', 'پیش‌نویس نامه'),
                    ('summarize', 'خلاصه‌سازی'),
                    ('support_reply', 'پیشنهاد پاسخ پشتیبانی'),
                    ('stt', 'گفتار به متن'),
                    ('embed', 'بردارسازی فایل'),
                    ('semantic_search', 'جست‌وجوی معنایی'),
                    ('meeting_summary', 'خلاصه جلسه'),
                    ('auto_support', 'پاسخ خودکار پشتیبانی'),
                ],
                max_length=40,
            ),
        ),
    ]
