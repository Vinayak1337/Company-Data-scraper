from django.core.management.base import BaseCommand

from companies.services import run_due_company_scans


class Command(BaseCommand):
    help = "Run scans for active companies whose scan cadence is due."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25, help="Maximum due companies to scan.")
        parser.add_argument("--force", action="store_true", help="Treat every active company as due.")
        parser.add_argument("--dry-run", action="store_true", help="Report due companies without scanning.")

    def handle(self, *args, **options):
        summary = run_due_company_scans(
            limit=options["limit"],
            force=options["force"],
            dry_run=options["dry_run"],
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {summary['due_count']} due, {summary['selected_count']} selected, 0 scanned."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Scans complete: "
                f"{summary['scanned']} scanned, "
                f"{summary['failed']} failed, "
                f"{summary['skipped']} skipped, "
                f"{summary['alerts_created']} alerts created."
            )
        )
