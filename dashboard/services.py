from collections import Counter

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from companies.models import Company, ScrapeLog
from jobs.models import Job
from scrapers_engine import detect_scraper, scrape


INDIA_STATE_CHOICES = [
    ("", "All states"),
    ("Andhra Pradesh", "Andhra Pradesh"),
    ("Delhi", "Delhi NCR"),
    ("Gujarat", "Gujarat"),
    ("Haryana", "Haryana"),
    ("Karnataka", "Karnataka"),
    ("Maharashtra", "Maharashtra"),
    ("Tamil Nadu", "Tamil Nadu"),
    ("Telangana", "Telangana"),
    ("Uttar Pradesh", "Uttar Pradesh"),
    ("West Bengal", "West Bengal"),
]

INDIA_CITY_CHOICES = [
    ("", "All cities"),
    ("Bengaluru", "Bengaluru"),
    ("Bangalore", "Bangalore"),
    ("Chennai", "Chennai"),
    ("Delhi", "Delhi"),
    ("Gurugram", "Gurugram"),
    ("Gurgaon", "Gurgaon"),
    ("Hyderabad", "Hyderabad"),
    ("Mumbai", "Mumbai"),
    ("Noida", "Noida"),
    ("Pune", "Pune"),
    ("Kolkata", "Kolkata"),
]

INDIA_STATE_ALIASES = {
    "Delhi": ["Delhi", "New Delhi", "DL,IN", "DL, IN"],
    "Haryana": ["Haryana", "HR,IN", "HR, IN", "Gurugram", "Gurgaon"],
    "Karnataka": ["Karnataka", "KA,IN", "KA, IN", "Bengaluru", "Bangalore"],
    "Maharashtra": ["Maharashtra", "MH,IN", "MH, IN", "Mumbai", "Pune"],
    "Tamil Nadu": ["Tamil Nadu", "TN,IN", "TN, IN", "Chennai"],
    "Telangana": ["Telangana", "TS,IN", "TS, IN", "Hyderabad"],
    "Uttar Pradesh": ["Uttar Pradesh", "UP,IN", "UP, IN", "Noida"],
    "West Bengal": ["West Bengal", "WB,IN", "WB, IN", "Kolkata"],
}


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
    filters = normalized_filters(params)
    query = filters["q"]
    title = filters["title"]
    company_id = filters["company"]
    location = filters["location"]
    country = filters["country"]
    state = filters["state"]
    city = filters["city"]
    tech = filters["tech"].lower()
    remote = filters["remote"]

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
    if country == "India":
        jobs = jobs.filter(india_location_q())
    if state:
        jobs = jobs.filter(location_alias_q(INDIA_STATE_ALIASES.get(state, [state])))
    if city:
        jobs = jobs.filter(location_alias_q([city]))
    if location:
        jobs = jobs.filter(location__icontains=location)
    if tech:
        jobs = jobs.filter(tags__icontains=tech)
    if remote:
        jobs = jobs.filter(remote_policy=remote)
    return jobs


def normalized_filters(params) -> dict:
    return {
        "q": params.get("q", "").strip(),
        "title": params.get("title", "").strip(),
        "company": params.get("company", "").strip(),
        "country": params.get("country", "India").strip() or "India",
        "state": params.get("state", "").strip(),
        "city": params.get("city", "").strip(),
        "location": params.get("location", "").strip(),
        "tech": params.get("tech", "").strip(),
        "remote": params.get("remote", "").strip(),
    }


def india_location_q() -> Q:
    return (
        Q(location__icontains="India")
        | Q(location__icontains=", IN")
        | Q(location__icontains=",IN")
        | Q(location__icontains=" IN,")
        | Q(location__iendswith=" IN")
        | Q(location__iendswith=",IN")
    )


def location_alias_q(aliases: list[str]) -> Q:
    query = Q()
    for alias in aliases:
        query |= Q(location__icontains=alias)
    return query


def dashboard_stats() -> dict:
    today = timezone.now().date()
    return {
        "total_jobs": Job.objects.count(),
        "active_companies": Company.objects.filter(is_active=True).count(),
        "jobs_today": Job.objects.filter(first_seen_at__date=today).count(),
        "last_log": ScrapeLog.objects.order_by("-started_at").first(),
    }


def tag_cloud() -> list[str]:
    counter: Counter[str] = Counter()
    for row in Job.objects.exclude(tags=[]).values_list("tags", flat=True):
        counter.update(row)
    return [tag for tag, _ in counter.most_common(40)]


def company_counts():
    return Company.objects.annotate(job_count=Count("jobs")).order_by("name")


def reset_all_jobs() -> dict:
    deleted_jobs, _ = Job.objects.all().delete()
    deleted_logs, _ = ScrapeLog.objects.all().delete()
    Company.objects.update(
        last_scraped_at=None,
        last_scrape_status="never",
        last_scrape_message="",
    )
    return {"jobs": deleted_jobs, "logs": deleted_logs}


def infer_name_from_url(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or url).replace("www.", "")
    parts = host.split(".")
    return (parts[-2] if len(parts) > 1 else parts[0]).replace("-", " ").title()
