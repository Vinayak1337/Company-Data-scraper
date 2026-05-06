import os
import shutil
from getpass import getpass
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from agents.models import AgentProviderSetting
from agents.services import (
    HOSTED_API_PROVIDERS,
    PROVIDER_DEFAULTS,
    ensure_provider_settings,
    local_cli_enabled,
    provider_runtime_status,
    runtime_environment,
    selected_brain_provider,
    update_provider_setting,
)
from companies.services import import_company_watchlist_csv, run_due_company_scans
from notifications.services import (
    create_notification_events_for_scan_jobs,
    get_notification_preferences,
    send_queued_notification_events,
    update_notification_preferences,
)
from profiles.services import generate_search_strategy, get_profile, import_resume, update_profile


def provider_names() -> list[str]:
    return [item["provider"] for item in PROVIDER_DEFAULTS]


PROVIDER_ALIASES = {
    "gemini": "gemini_cli",
    "claude": "claude_code_cli",
    "claude_cli": "claude_code_cli",
    "codex": "codex_cli",
}


def provider_choices() -> list[str]:
    return [*provider_names(), *PROVIDER_ALIASES.keys()]


def normalize_provider_name(value: str) -> str:
    provider = str(value or "").strip()
    return PROVIDER_ALIASES.get(provider, provider)


def read_env_values(path: Path) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        return [], {}
    lines = path.read_text(encoding="utf-8").splitlines()
    values = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def write_env_values(path: Path, updates: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines, _ = read_env_values(path)
    rendered = []
    written = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            rendered.append(line)
            continue
        key, _ = stripped.split("=", 1)
        key = key.strip()
        if key in updates:
            rendered.append(f"{key}={quote_env_value(updates[key])}")
            written.add(key)
        else:
            rendered.append(line)
    if rendered and rendered[-1].strip():
        rendered.append("")
    for key, value in updates.items():
        if key in written:
            continue
        rendered.append(f"{key}={quote_env_value(value)}")
    path.write_text("\n".join(rendered).rstrip() + "\n", encoding="utf-8")


def quote_env_value(value: str) -> str:
    text = str(value)
    if not text or any(char.isspace() for char in text) or "#" in text or "{" in text or "}" in text:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


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
            "--provider",
            action="append",
            choices=provider_choices(),
            help="Brain provider to configure during setup.",
        )
        setup.add_argument("--env-file", default=str(settings.BASE_DIR / ".env"), help="Backend .env file to update.")

        providers = subcommands.add_parser("providers", help="Configure the local Job Scout brain provider.")
        providers.add_argument("--provider", choices=provider_choices(), help="Provider to configure without opening the selector.")
        providers.add_argument("--env-file", default=str(settings.BASE_DIR / ".env"), help="Backend .env file to update.")
        providers.add_argument("--api-key", help="API key to write for API providers. Prefer interactive input.")
        providers.add_argument("--command", help="CLI command template. Use {prompt} where the prompt should be inserted.")
        providers.add_argument("--non-interactive", action="store_true", help="Fail instead of prompting for missing values.")

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
        elif command == "providers":
            self.configure_brain_provider(options)
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

        if options.get("provider") or not options["non_interactive"]:
            self.configure_brain_provider(
                {
                    "provider": (options.get("provider") or [None])[-1],
                    "env_file": options["env_file"],
                    "api_key": "",
                    "command": "",
                    "non_interactive": options["non_interactive"],
                }
            )

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

    def configure_brain_provider(self, options):
        ensure_provider_settings()
        provider_name = normalize_provider_name(options.get("provider"))
        if not provider_name:
            if options.get("non_interactive"):
                raise CommandError("--provider is required in non-interactive mode.")
            provider_name = self.select_provider()

        setting = AgentProviderSetting.objects.get(provider=provider_name)
        metadata = provider_runtime_status(setting)
        env_path = Path(options.get("env_file") or settings.BASE_DIR / ".env").expanduser()
        updates = {
            "JOB_SCOUT_RUNTIME_ENV": "local",
            "JOB_SCOUT_BRAIN_PROVIDER": provider_name,
        }

        if metadata["is_local_only"]:
            command = metadata["local_cli_command"]
            command_path = shutil.which(command) if command else ""
            if not command_path:
                self.stdout.write(self.style.WARNING(f"`{command}` was not found in PATH. Install and log in before running this provider."))
            if not options.get("non_interactive"):
                confirmed = self.prompt_bool(f"Have you already logged in to {setting.label} in this terminal", default=bool(command_path))
                if not confirmed:
                    self.stdout.write(self.style.WARNING("Provider will be written to .env, but runs will fail until the CLI login works."))
            command_template = options.get("command") or self.default_cli_command_template(provider_name)
            if not options.get("non_interactive"):
                command_template = self.prompt("CLI command template", default=command_template, required=True)
            updates["JOB_SCOUT_ENABLE_LOCAL_CLI"] = "True"
            updates["JOB_SCOUT_CLI_TIMEOUT_SECONDS"] = "120"
            updates[f"JOB_SCOUT_{provider_name.upper()}_COMMAND"] = command_template
            self.apply_runtime_env(updates)
            update_provider_setting(setting, {"enabled": True, "consent_required": True})
        elif provider_name == "direct_api":
            self.apply_runtime_env(updates)
            update_provider_setting(setting, {"enabled": True, "consent_required": False})
        elif provider_name in HOSTED_API_PROVIDERS or setting.api_key_env_var:
            api_key = options.get("api_key") or ""
            if not api_key and not options.get("non_interactive") and setting.api_key_env_var:
                api_key = self.prompt_secret(f"{setting.api_key_env_var}", default=os.environ.get(setting.api_key_env_var, ""))
            if setting.api_key_env_var and api_key:
                updates[setting.api_key_env_var] = api_key
            self.apply_runtime_env(updates)
            if setting.api_key_env_var and not os.environ.get(setting.api_key_env_var) and provider_name in HOSTED_API_PROVIDERS:
                raise CommandError(f"{setting.api_key_env_var} is required to enable {setting.label}.")
            update_provider_setting(setting, {"enabled": True, "consent_required": provider_name != "direct_api"})

        write_env_values(env_path, updates)
        self.stdout.write(self.style.SUCCESS(f"{setting.label} is now the local Job Scout brain."))
        self.stdout.write(f"Updated {env_path}")

    def apply_runtime_env(self, updates: dict[str, str]) -> None:
        os.environ.update(updates)
        if "JOB_SCOUT_RUNTIME_ENV" in updates:
            settings.JOB_SCOUT_RUNTIME_ENV = updates["JOB_SCOUT_RUNTIME_ENV"]
        if "JOB_SCOUT_BRAIN_PROVIDER" in updates:
            settings.JOB_SCOUT_BRAIN_PROVIDER = updates["JOB_SCOUT_BRAIN_PROVIDER"]
        if "JOB_SCOUT_ENABLE_LOCAL_CLI" in updates:
            settings.JOB_SCOUT_ENABLE_LOCAL_CLI = updates["JOB_SCOUT_ENABLE_LOCAL_CLI"].lower() in {"1", "true", "yes"}
        if "JOB_SCOUT_CLI_TIMEOUT_SECONDS" in updates:
            settings.JOB_SCOUT_CLI_TIMEOUT_SECONDS = int(updates["JOB_SCOUT_CLI_TIMEOUT_SECONDS"])

    def select_provider(self) -> str:
        providers = {provider.provider: provider for provider in ensure_provider_settings()}
        ordered = [name for name in provider_names() if name in providers]
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Select local brain provider"))
        for index, provider_name in enumerate(ordered, start=1):
            provider = providers[provider_name]
            metadata = provider_runtime_status(provider)
            brain_marker = " current" if provider_name == selected_brain_provider() else ""
            scope = "local CLI" if metadata["is_local_only"] else "API"
            self.stdout.write(f"{index}. {provider.label} [{scope}]{brain_marker}")
        choice = self.prompt("Provider number", default="1", required=True)
        try:
            index = int(choice)
        except ValueError as exc:
            raise CommandError("Provider selection must be a number.") from exc
        if index < 1 or index > len(ordered):
            raise CommandError("Provider selection is out of range.")
        return ordered[index - 1]

    def default_cli_command_template(self, provider_name: str) -> str:
        defaults = {
            "gemini_cli": "gemini -p {prompt}",
            "claude_code_cli": "claude -p {prompt}",
            "codex_cli": "codex exec {prompt}",
            "opencode": "opencode run {prompt}",
        }
        return defaults.get(provider_name, f"{provider_name} {{prompt}}")

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
        self.stdout.write(f"Brain provider: {selected_brain_provider()}")
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
            brain_marker = ", brain" if metadata["is_brain"] else ""
            self.stdout.write(f"- {provider.label}: {enabled}, {scope}, {status}{brain_marker}")
            if metadata["setup_hint"]:
                self.stdout.write(f"  {metadata['setup_hint']}")
        self.stdout.write("")
        self.stdout.write("Useful commands:")
        self.stdout.write("  ./jobscout init")
        self.stdout.write("  ./jobscout providers")
        self.stdout.write("  ./jobscout setup")
        self.stdout.write("  ./jobscout import-watchlist --csv companies.csv")
        self.stdout.write("  ./jobscout run-once --force")

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

    def prompt_secret(self, label: str, default: str = "") -> str:
        suffix = " [already set]" if default else ""
        value = getpass(f"{label}{suffix}: ").strip()
        return value or default

    def prompt_list(self, label: str, default: list[str] | None = None) -> list[str]:
        default = default or []
        value = self.prompt(label, default=", ".join(default), required=False)
        return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]

    def prompt_bool(self, label: str, default: bool = False) -> bool:
        default_text = "yes" if default else "no"
        value = self.prompt(f"{label} (yes/no)", default=default_text, required=False).lower()
        return value in {"1", "true", "yes", "y", "on"}
