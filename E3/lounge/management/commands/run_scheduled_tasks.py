from django.core.management.base import BaseCommand

from lounge.scheduled_jobs import run_all_scheduled_jobs


class Command(BaseCommand):
    help = "Run Phase 1 scheduled task placeholders."

    def handle(self, *args, **options):
        logs = run_all_scheduled_jobs()
        self.stdout.write(self.style.SUCCESS(f"Scheduled task placeholders completed: {len(logs)}"))
