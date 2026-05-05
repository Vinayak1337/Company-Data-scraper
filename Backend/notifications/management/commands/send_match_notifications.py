from django.core.management.base import BaseCommand

from notifications.services import send_queued_notification_events


class Command(BaseCommand):
    help = "Send queued V3 match notification emails."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        result = send_queued_notification_events(limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {result['sent']} notification emails, skipped {result['skipped']}, failed {result['failed']}."
            )
        )
