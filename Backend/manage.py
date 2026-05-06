#!/usr/bin/env python3
"""Django command-line utility for the job scraper project."""
import os
import sys
from pathlib import Path


RUNTIME_COMMANDS = {
    "process_agent_queue",
    "run_periodic_maintenance",
    "runserver",
    "scan_due_companies",
    "send_match_notifications",
}


def enforce_local_setup(argv: list[str]) -> None:
    command = next((arg for arg in argv[1:] if not arg.startswith("-")), "")
    if command not in RUNTIME_COMMANDS:
        return

    if os.environ.get("JOBSCOUT_ALLOW_UNINITIALIZED") == "true":
        return

    repo_root = Path(__file__).resolve().parent.parent
    setup_marker = repo_root / ".jobscout" / "setup.json"
    if setup_marker.exists():
        return

    sys.stderr.write(
        "Job Scout setup is not complete.\n\n"
        "Run this from the repository root before starting runtime processes:\n"
        "  ./jobscout init\n\n"
        "For CI-only runtime smoke tests, set JOBSCOUT_ALLOW_UNINITIALIZED=true.\n"
    )
    raise SystemExit(78)


def main() -> None:
    enforce_local_setup(sys.argv)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobhunt.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
