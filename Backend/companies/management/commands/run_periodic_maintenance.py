from django.core.management.base import BaseCommand

from companies.services import run_due_company_scans
from notifications.services import create_notification_events_for_scan_jobs, send_queued_notification_events


class Command(BaseCommand):
    help = "Run the local periodic loop once: due company crawls, match notification selection, then queued email delivery."

    def add_arguments(self, parser):
        parser.add_argument("--scan-limit", type=int, default=25)
        parser.add_argument("--notification-limit", type=int, default=25)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        scan_summary = run_due_company_scans(
            limit=options["scan_limit"],
            force=options["force"],
        )
        event_summary = create_notification_events_for_scan_jobs(scan_summary["scan_jobs"])
        notification_summary = send_queued_notification_events(
            limit=options["notification_limit"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Periodic maintenance complete: "
                f"{scan_summary['scanned']} scanned, "
                f"{scan_summary['failed']} scan failures, "
                f"{scan_summary['skipped']} skipped, "
                f"{scan_summary['alerts_created']} alerts created; "
                f"{event_summary['queued']} notification events queued from "
                f"{event_summary['reviewed']} reviewed jobs; "
                f"{notification_summary['sent']} emails sent, "
                f"{notification_summary['failed']} email failures, "
                f"{notification_summary['skipped']} skipped."
            )
        )
