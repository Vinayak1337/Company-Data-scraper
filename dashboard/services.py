from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from companies.models import Company, ScrapeLog
from jobs.models import Job
from scrapers_engine import detect_scraper, scrape


def create_company_from_url(url: str, name: str = "") -> Company:
    scraper_type = detect_scraper(url)
    display_name = name.strip() or infer_name_from_url(url)
    company, created = Company.objects.get_or_create(
        careers_url=url,
        defaults={"name": display_name, "scraper_type": scraper_type},
    )
    if not created and company.scraper_type in {"unknown", ""}:
        company.scraper_type = scraper_type
        company.save(update_fields=["scraper_type", "updated_at"])
    return company


def scrape_company_jobs(company: Company) -> ScrapeLog:
    log = ScrapeLog.objects.create(company=company, source_platform=company.scraper_type)
    try:
        result = scrape(company.careers_url)
        if result.company_name and company.name == infer_name_from_url(company.careers_url):
            company.name = result.company_name[:180]
        company.scraper_type = result.source_platform
        company.save(update_fields=["name", "scraper_type", "updated_at"])

        created = 0
        updated = 0
        with transaction.atomic():
            for item in result.jobs:
                _, was_created = upsert_job(company, item)
                if was_created:
                    created += 1
                else:
                    updated += 1
        message = f"Found {len(result.jobs)} jobs. Created {created}, updated {updated}."
        company.mark_scrape_result("success", message)
        log.source_platform = result.source_platform
        log.finish("success", message, len(result.jobs), created, updated)
    except Exception as exc:
        message = str(exc)
        company.mark_scrape_result("failed", message)
        log.finish("failed", message)
    return log


def upsert_job(company: Company, item) -> tuple[Job, bool]:
    defaults = {
        "title": item.title[:255],
        "location": item.location[:255],
        "description": item.description,
        "source_url": item.source_url,
        "source_platform": item.source_platform,
        "external_id": item.external_id[:255],
        "posted_at": item.posted_at,
        "tags": item.tags,
        "remote_policy": item.remote_policy,
        "last_seen_at": timezone.now(),
    }
    try:
        return Job.objects.update_or_create(company=company, apply_url=item.apply_url, defaults=defaults)
    except IntegrityError:
        existing = Job.objects.get(company=company, apply_url=item.apply_url)
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()
        return existing, False


def filter_jobs(params):
    jobs = Job.objects.select_related("company").all()
    query = params.get("q", "").strip()
    title = params.get("title", "").strip()
    company_id = params.get("company", "").strip()
    location = params.get("location", "").strip()
    tech = params.get("tech", "").strip().lower()
    remote = params.get("remote", "").strip()

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(location__icontains=query)
            | Q(company__name__icontains=query)
        )
    if title:
        jobs = jobs.filter(title__icontains=title)
    if company_id:
        jobs = jobs.filter(company_id=company_id)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if tech:
        jobs = jobs.filter(tags__icontains=tech)
    if remote:
        jobs = jobs.filter(remote_policy=remote)
    return jobs


def dashboard_stats() -> dict:
    today = timezone.now().date()
    return {
        "total_jobs": Job.objects.count(),
        "active_companies": Company.objects.filter(is_active=True).count(),
        "jobs_today": Job.objects.filter(first_seen_at__date=today).count(),
        "last_log": ScrapeLog.objects.order_by("-started_at").first(),
    }


def tag_cloud() -> list[str]:
    tags = []
    for row in Job.objects.exclude(tags=[]).values_list("tags", flat=True):
        tags.extend(row)
    return sorted(set(tags))[:40]


def company_counts():
    return Company.objects.annotate(job_count=Count("jobs")).order_by("name")


def infer_name_from_url(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or url).replace("www.", "")
    parts = host.split(".")
    return (parts[-2] if len(parts) > 1 else parts[0]).replace("-", " ").title()
