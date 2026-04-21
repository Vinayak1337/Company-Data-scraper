import os
import sys

from django.core.management.base import BaseCommand

from companies.models import Company
from companies.seed import TOP_TIER_COMPANIES


class Command(BaseCommand):
    help = "Seed a curated list of top-tier company career URLs."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name, careers_url, scraper_type in TOP_TIER_COMPANIES:
            company, was_created = Company.objects.get_or_create(
                careers_url=careers_url,
                defaults={"name": name, "scraper_type": scraper_type, "is_active": True},
            )
            if was_created:
                created += 1
                continue
            changed = False
            if company.name != name:
                company.name = name
                changed = True
            if company.scraper_type in {"unknown", "generic"} and scraper_type != company.scraper_type:
                company.scraper_type = scraper_type
                changed = True
            if changed:
                company.save(update_fields=["name", "scraper_type", "updated_at"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded companies. Created {created}, updated {updated}."))


if __name__ == "__main__":
    # Allow running directly: python seed_companies.py
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobhunt.settings")
    import django
    django.setup()
    from django.core.management import call_command
    call_command("seed_companies")
