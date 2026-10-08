# Generated for strong password hashing

from django.db import migrations, models
import desk.models


class Migration(migrations.Migration):
    dependencies = [
        ('desk', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='password',
            field=models.CharField(
                default=desk.models.default_password_hash,
                editable=False,
                max_length=128,
            ),
        ),
    ]
