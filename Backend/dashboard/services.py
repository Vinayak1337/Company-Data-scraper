from collections import Counter

from django.db.models import Count, Q
from django.utils import timezone

from companies import services as company_services
from companies.models import Company, ScrapeLog
from jobs.models import Job

create_company_from_url = company_services.create_company_from_url
delete_company = company_services.delete_company
detect_scraper = company_services.detect_scraper
infer_name_from_url = company_services.infer_name_from_url
pause_company = company_services.pause_company
resume_company = company_services.resume_company
scrape = company_services.scrape
update_company = company_services.update_company
upsert_job = company_services.upsert_job


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


def scrape_company_jobs(company: Company) -> ScrapeLog:
    return company_services.scrape_company_jobs(company, scraper=scrape)


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
        source_health="needs_setup",
        last_scraped_at=None,
        last_scrape_status="never",
        last_scrape_message="",
        last_successful_scan_at=None,
        last_failed_scan_at=None,
        consecutive_failure_count=0,
        last_new_role_at=None,
    )
    return {"jobs": deleted_jobs, "logs": deleted_logs}
