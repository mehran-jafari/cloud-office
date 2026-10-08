from django.core.management.base import BaseCommand
from support.services import run_escalations


class Command(BaseCommand):
    help = 'اجرای escalation مکالمات پشتیبانی بدون پاسخ (هر ۱–۵ دقیقه از cron صدا بزنید)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        result = run_escalations(limit=options['limit'])
        self.stdout.write(self.style.SUCCESS(
            f"escalated={result.get('escalated', 0)} admin_notified={result.get('admin_notified', 0)}"
        ))
