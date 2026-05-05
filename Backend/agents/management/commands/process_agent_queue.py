from django.core.management.base import BaseCommand

from agents.services import process_queued_agent_runs


class Command(BaseCommand):
    help = "Process queued Job Scout agent runs."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Maximum number of queued runs to process.")

    def handle(self, *args, **options):
        summary = process_queued_agent_runs(limit=options.get("limit"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Agent queue processed: {summary['selected']} selected, "
                f"{summary['completed']} completed, {summary['failed']} failed."
            )
        )
