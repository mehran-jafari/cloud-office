from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('support', '0002_remotesession'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='assigned_agent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_support_conversations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='conversation',
            name='first_agent_response_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='last_user_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='last_agent_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='next_escalate_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='escalation_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='conversation',
            name='ai_handled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='conversation',
            name='ai_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='conversation',
            name='status',
            field=models.CharField(
                choices=[
                    ('open', 'Open'),
                    ('waiting_agent', 'Waiting agent'),
                    ('waiting_user', 'Waiting user'),
                    ('ai_handling', 'AI handling'),
                    ('escalated', 'Escalated'),
                    ('closed', 'Closed'),
                ],
                default='open',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='is_ai',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='message',
            name='sender',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='SupportAlertLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(blank=True, max_length=20)),
                ('kind', models.CharField(
                    choices=[
                        ('new_message', 'New message'),
                        ('offline_broadcast', 'Offline broadcast'),
                        ('escalation', 'Escalation'),
                        ('admin_delay', 'Admin delay alert'),
                    ],
                    max_length=30,
                )),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('agent', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('conversation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='alert_logs',
                    to='support.conversation',
                )),
            ],
        ),
        migrations.AddIndex(
            model_name='supportalertlog',
            index=models.Index(fields=['conversation', 'kind', 'sent_at'], name='support_sup_convers_idx'),
        ),
    ]
