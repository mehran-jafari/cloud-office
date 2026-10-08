
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_roles_profile'),
    ]
    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'مرد'), ('female', 'زن'), ('other', 'سایر')], default='male', max_length=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),
    ]
