from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from agents.models import AgentProviderSetting
from agents.services import ensure_provider_settings, local_cli_enabled, provider_runtime_status, runtime_environment, update_provider_setting
from companies.services import import_company_watchlist_csv, run_due_company_scans
from notifications.services import (
    create_notification_events_for_scan_jobs,
    get_notification_preferences,
    send_queued_notification_events,
    update_notification_preferences,
)
from profiles.services import generate_search_strategy, get_profile, import_resume, update_profile


class Command(BaseCommand):
    help = "Local-first Job Scout CLI for setup, status checks, watchlist import, and run-once maintenance."

    def add_arguments(self, parser):
        subcommands = parser.add_subparsers(dest="job_scout_command")

        status = subcommands.add_parser("status", help="Show local setup readiness.")
        status.add_argument("--json", action="store_true", help="Reserved for future machine-readable output.")

        setup = subcommands.add_parser("setup", help="Run the local interactive setup wizard.")
        setup.add_argument("--watchlist-csv", help="CSV file to import into the company watchlist.")
        setup.add_argument("--resume-file", help="Resume/profile text file to import.")
        setup.add_argument("--skip-migrate", action="store_true", help="Do not run database migrations first.")
        setup.add_argument("--non-interactive", action="store_true", help="Only apply provided files/options.")
        setup.add_argument(
            "--enable-local-cli",
            action="store_true",
            help="Enable selected local CLI providers when JOB_SCOUT_ENABLE_LOCAL_CLI=true and the command is installed.",
        )
        setup.add_argument(
            "--provider",
            action="append",
            choices=["gemini_cli", "claude_code_cli", "opencode"],
            help="Local CLI provider to enable during setup. Can be passed multiple times.",
        )

        import_watchlist = subcommands.add_parser("import-watchlist", help="Import a company watchlist CSV locally.")
        import_watchlist.add_argument("--csv", required=True, help="CSV file path.")

        run_once = subcommands.add_parser("run-once", help="Run due crawls, match review, and queued email delivery once.")
        run_once.add_argument("--scan-limit", type=int, default=25)
        run_once.add_argument("--notification-limit", type=int, default=25)
        run_once.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        command = options.get("job_scout_command") or "status"
        if command == "setup":
            self.handle_setup(options)
        elif command == "import-watchlist":
            self.import_watchlist(options["csv"])
        elif command == "run-once":
            self.run_once(options)
        else:
            self.print_status()

    def handle_setup(self, options):
        if not options["skip_migrate"]:
            self.stdout.write("Applying local database migrations...")
            call_command("migrate", interactive=False, verbosity=0)

        ensure_provider_settings()
        profile = get_profile()
        if options.get("resume_file"):
            profile = self.import_resume_file(profile, options["resume_file"])

        if not options["non_interactive"]:
            updates = self.prompt_profile_updates(profile)
            if updates:
                profile = update_profile(profile, updates)
            preference_updates = self.prompt_notification_updates()
            if preference_updates:
                update_notification_preferences(get_notification_preferences(), preference_updates)
            watchlist_path = self.prompt("Watchlist CSV path", default=options.get("watchlist_csv") or "", required=False)
            if watchlist_path:
                options["watchlist_csv"] = watchlist_path

        if options.get("watchlist_csv"):
            self.import_watchlist(options["watchlist_csv"])

        generate_search_strategy(profile)
        self.configure_local_cli_providers(options.get("provider") or [], enable=options["enable_local_cli"])
        self.stdout.write(self.style.SUCCESS("Local setup complete."))
        self.print_status()

    def prompt_profile_updates(self, profile):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Profile"))
        return {
            "full_name": self.prompt("Full name", default=profile.full_name, required=False),
            "headline": self.prompt("Target headline", default=profile.headline, required=False),
            "location": self.prompt("Location", default=profile.location, required=False),
            "skills": self.prompt_list("Skills", default=profile.skills),
            "target_locations": self.prompt_list("Target locations", default=profile.target_locations),
            "preferred_work_modes": self.prompt_list("Preferred work modes", default=profile.preferred_work_modes),
            "summary": self.prompt("Short profile summary", default=profile.summary, required=False),
        }

    def prompt_notification_updates(self):
        preference = get_notification_preferences()
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Notifications"))
        email = self.prompt("Email address", default=preference.email_address, required=False)
        channel_default = "email" if email else preference.digest_channel
        return {
            "email_address": email,
            "digest_channel": self.prompt("Channel (local/email)", default=channel_default, required=False),
            "digest_enabled": self.prompt_bool("Enable digest", default=preference.digest_enabled),
            "immediate_email_enabled": self.prompt_bool("Immediate email", default=preference.immediate_email_enabled),
            "minimum_match_score": self.prompt("Minimum match score", default=str(preference.minimum_match_score), required=False),
            "minimum_confidence_score": self.prompt("Minimum confidence score", default=str(preference.minimum_confidence_score), required=False),
        }

    def configure_local_cli_providers(self, providers, enable: bool):
        if not providers:
            return

        ensure_provider_settings()
        for provider_name in providers:
            setting = AgentProviderSetting.objects.get(provider=provider_name)
            metadata = provider_runtime_status(setting)
            if not enable:
                self.stdout.write(self.style.WARNING(f"{setting.label}: left disabled. Pass --enable-local-cli to enable it."))
                continue
            if not local_cli_enabled():
                self.stdout.write(
                    self.style.WARNING(
                        f"{setting.label}: not enabled. Start the command with JOB_SCOUT_ENABLE_LOCAL_CLI=true after local CLI login."
                    )
                )
                continue
            if not metadata["local_cli_command_found"]:
                self.stdout.write(self.style.WARNING(f"{setting.label}: `{metadata['local_cli_command']}` was not found in PATH."))
                continue
            update_provider_setting(setting, {"enabled": True, "consent_required": True})
            self.stdout.write(self.style.SUCCESS(f"{setting.label}: enabled for local worker use."))

    def import_resume_file(self, profile, path_value: str):
        path = Path(path_value).expanduser()
        if not path.exists():
            raise CommandError(f"Resume file does not exist: {path}")
        profile = import_resume(profile, path.read_text(encoding="utf-8"))
        self.stdout.write(self.style.SUCCESS(f"Imported resume text from {path}."))
        return profile

    def import_watchlist(self, path_value: str):
        path = Path(path_value).expanduser()
        if not path.exists():
            raise CommandError(f"Watchlist CSV does not exist: {path}")
        result = import_company_watchlist_csv(path.read_text(encoding="utf-8"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported watchlist: {result['created_or_updated']} created/updated, {len(result['errors'])} row errors."
            )
        )
        for error in result["errors"][:10]:
            self.stdout.write(self.style.WARNING(f"Row {error['row']}: {error['error']}"))

    def run_once(self, options):
        scan_summary = run_due_company_scans(limit=options["scan_limit"], force=options["force"])
        event_summary = create_notification_events_for_scan_jobs(scan_summary["scan_jobs"])
        notification_summary = send_queued_notification_events(limit=options["notification_limit"])
        self.stdout.write(
            self.style.SUCCESS(
                "Local run complete: "
                f"{scan_summary['scanned']} scanned, "
                f"{scan_summary['failed']} scan failures, "
                f"{event_summary['queued']} notification events queued, "
                f"{notification_summary['sent']} emails sent."
            )
        )

    def print_status(self):
        ensure_provider_settings()
        connection.ensure_connection()
        profile = get_profile()
        preference = get_notification_preferences()
        self.stdout.write(self.style.MIGRATE_HEADING("Job Scout local status"))
        self.stdout.write(f"Database: {connection.vendor}")
        self.stdout.write(f"Runtime: {runtime_environment()}")
        self.stdout.write(f"Local CLI enabled: {'yes' if local_cli_enabled() else 'no'}")
        self.stdout.write(f"Profile: {'ready' if profile.profile_completeness_score >= 70 else 'needs setup'} ({profile.profile_completeness_score}/100)")
        self.stdout.write(f"Notifications: {'email' if preference.email_address else preference.digest_channel}")
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Providers"))
        for provider in AgentProviderSetting.objects.order_by("provider"):
            metadata = provider_runtime_status(provider)
            enabled = "enabled" if provider.enabled else "disabled"
            scope = metadata["runtime_scope"]
            status = metadata["configuration_status"]
            self.stdout.write(f"- {provider.label}: {enabled}, {scope}, {status}")
            if metadata["setup_hint"]:
                self.stdout.write(f"  {metadata['setup_hint']}")
        self.stdout.write("")
        self.stdout.write("Useful commands:")
        self.stdout.write("  ./scripts/job-scout setup")
        self.stdout.write("  ./scripts/job-scout import-watchlist --csv companies.csv")
        self.stdout.write("  ./scripts/job-scout run-once --force")
        self.stdout.write("  JOB_SCOUT_ENABLE_LOCAL_CLI=true ./scripts/job-scout setup --provider gemini_cli --enable-local-cli")

    def prompt(self, label: str, default: str = "", required: bool = False) -> str:
        suffix = f" [{default}]" if default else ""
        while True:
            value = input(f"{label}{suffix}: ").strip()
            if value:
                return value
            if default:
                return default
            if not required:
                return ""
            self.stdout.write(self.style.ERROR(f"{label} is required."))

    def prompt_list(self, label: str, default: list[str] | None = None) -> list[str]:
        default = default or []
        value = self.prompt(label, default=", ".join(default), required=False)
        return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]

    def prompt_bool(self, label: str, default: bool = False) -> bool:
        default_text = "yes" if default else "no"
        value = self.prompt(f"{label} (yes/no)", default=default_text, required=False).lower()
        return value in {"1", "true", "yes", "y", "on"}
