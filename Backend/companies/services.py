from dataclasses import dataclass
from datetime import timedelta
import ipaddress
from urllib.parse import urlsplit

from django.db import IntegrityError, transaction
from django.utils import timezone

from companies.models import Company, JobAlert, ScanJob, ScrapeLog
from jobs.models import Job
from notifications.mteane import publish_mteane_event
from scrapers_engine import detect_scraper, scrape


FAILURE_THRESHOLD = 3
ACTIVE_SCAN_STATUSES = ("queued", "running")
BLOCKED_TERMS = ("blocked", "forbidden", "403", "robots", "captcha", "rate limit", "too many requests")
PRIORITY_TIERS = {choice[0] for choice in Company.PRIORITY_CHOICES}
KEYWORD_FILTER_FIELDS = ("title_keywords", "negative_title_keywords", "location_keywords")
WORK_MODE_FILTERS = {choice[0] for choice in Company.WORK_MODE_CHOICES}
WORK_MODE_ALIASES = {
    "": "any",
    "all": "any",
    "anywhere": "remote",
    "in office": "onsite",
    "in-office": "onsite",
    "none": "any",
    "office": "onsite",
    "on site": "onsite",
    "on-site": "onsite",
    "wfh": "remote",
    "work from home": "remote",
}


class ScanAlreadyRunning(ValueError):
    pass


@dataclass(frozen=True)
class ScheduledScanSummary:
    scanned: int = 0
    skipped: int = 0
    failed: int = 0
    alerts_created: int = 0
    scan_jobs: tuple[ScanJob, ...] = ()


def create_company_from_url(url: str, name: str = "", priority_tier: str = "", filters: dict | None = None) -> Company:
    url = validate_public_careers_url(url)
    if not url:
        raise ValueError("careers_url is required")
    priority_tier = normalize_priority_tier(priority_tier)
    filter_updates = normalize_company_filter_updates(filters or {})
    scraper_type = detect_scraper(url)
    display_name = name.strip() or infer_name_from_url(url)
    defaults = {"name": display_name, "scraper_type": scraper_type}
    if priority_tier:
        defaults["priority_tier"] = priority_tier
    defaults.update(filter_updates)
    company, created = Company.objects.get_or_create(careers_url=url, defaults=defaults)
    update_fields = []
    if not created and company.scraper_type in {"unknown", ""}:
        company.scraper_type = scraper_type
        update_fields.append("scraper_type")
    if not created and priority_tier and company.priority_tier != priority_tier:
        company.priority_tier = priority_tier
        update_fields.append("priority_tier")
    if not created:
        for field, value in filter_updates.items():
            if getattr(company, field) != value:
                setattr(company, field, value)
                update_fields.append(field)
    if update_fields:
        company.save(update_fields=[*update_fields, "updated_at"])
    return company


def update_company(company: Company, updates: dict) -> Company:
    update_fields = []

    if "name" in updates:
        name = str(updates.get("name") or "").strip()
        if name and company.name != name:
            company.name = name[:180]
            update_fields.append("name")

    scraper_type_supplied = "scraper_type" in updates
    if "careers_url" in updates:
        careers_url = validate_public_careers_url(str(updates.get("careers_url") or ""))
        if not careers_url:
            raise ValueError("careers_url cannot be blank")
        if company.careers_url != careers_url:
            company.careers_url = careers_url
            update_fields.append("careers_url")
            if not scraper_type_supplied:
                company.scraper_type = detect_scraper(careers_url)
                update_fields.append("scraper_type")

    if scraper_type_supplied:
        scraper_type = str(updates.get("scraper_type") or "").strip() or "unknown"
        if company.scraper_type != scraper_type:
            company.scraper_type = scraper_type[:40]
            update_fields.append("scraper_type")

    if "priority_tier" in updates:
        priority_tier = normalize_priority_tier(updates.get("priority_tier"))
        if company.priority_tier != priority_tier:
            company.priority_tier = priority_tier
            update_fields.append("priority_tier")

    for field in KEYWORD_FILTER_FIELDS:
        if field in updates:
            value = coerce_keyword_list(updates[field], field)
            if getattr(company, field) != value:
                setattr(company, field, value)
                update_fields.append(field)

    if "work_mode_filter" in updates:
        work_mode_filter = normalize_work_mode_filter(updates.get("work_mode_filter"))
        if company.work_mode_filter != work_mode_filter:
            company.work_mode_filter = work_mode_filter
            update_fields.append("work_mode_filter")

    if "is_active" in updates:
        is_active = coerce_bool(updates["is_active"])
        if company.is_active != is_active:
            company.is_active = is_active
            update_fields.append("is_active")
        next_health = health_for_company(company)
        if company.source_health != next_health:
            company.source_health = next_health
            update_fields.append("source_health")

    if "scan_frequency_hours" in updates:
        scan_frequency_hours = normalize_scan_frequency_hours(updates.get("scan_frequency_hours"))
        if company.scan_frequency_hours != scan_frequency_hours:
            company.scan_frequency_hours = scan_frequency_hours
            update_fields.append("scan_frequency_hours")

    if "alert_new_roles" in updates:
        alert_new_roles = coerce_bool(updates["alert_new_roles"])
        if company.alert_new_roles != alert_new_roles:
            company.alert_new_roles = alert_new_roles
            update_fields.append("alert_new_roles")

    if update_fields:
        company.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
    return company


def pause_company(company: Company) -> Company:
    company.is_active = False
    company.source_health = "paused"
    company.save(update_fields=["is_active", "source_health", "updated_at"])
    return company


def resume_company(company: Company) -> Company:
    company.is_active = True
    company.source_health = health_for_company(company)
    company.save(update_fields=["is_active", "source_health", "updated_at"])
    return company


def delete_company(company: Company) -> tuple[int, dict]:
    return company.delete()


def validate_public_careers_url(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        raise ValueError("careers_url is required")

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("careers_url must use http or https")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError("careers_url must include a public hostname")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "0.0.0.0"} or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError("careers_url must use a public hostname")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise ValueError("careers_url must use a public hostname")
    else:
        if (
            address.is_loopback
            or address.is_private
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise ValueError("careers_url must use a public hostname")

    return url


def scrape_company_jobs(company: Company, scraper=None) -> ScrapeLog:
    scraper = scraper or scrape
    log = ScrapeLog.objects.create(company=company, source_platform=company.scraper_type)
    if not company.is_active:
        message = "Company is paused; resume it before scanning."
        company.source_health = "paused"
        company.save(update_fields=["source_health", "updated_at"])
        log.finish("failed", message)
        return log

    try:
        result = scraper(company.careers_url)
        if result.company_name and company.name == infer_name_from_url(company.careers_url):
            company.name = result.company_name[:180]
        company.scraper_type = result.source_platform
        company.save(update_fields=["name", "scraper_type", "updated_at"])

        matched_jobs = [item for item in result.jobs if job_matches_company_filters(company, item)]
        created = 0
        updated = 0
        with transaction.atomic():
            for item in matched_jobs:
                _, was_created = upsert_job(company, item)
                if was_created:
                    created += 1
                else:
                    updated += 1
        message = filter_scan_message(len(result.jobs), len(matched_jobs), created, updated)
        mark_company_scan_success(company, message, jobs_created=created)
        log.source_platform = result.source_platform
        log.finish("success", message, len(result.jobs), created, updated)
    except Exception as exc:
        message = str(exc)
        mark_company_scan_failure(company, message)
        log.finish("failed", message)
    return log


def run_company_scan(company: Company, trigger: str = "manual", force: bool = False, scraper=None) -> tuple[ScanJob, ScrapeLog]:
    scan_job = queue_company_scan(company, trigger=trigger, force=force)
    log = execute_scan_job(scan_job, scraper=scraper)
    scan_job.refresh_from_db()
    return scan_job, log


def queue_company_scan(company: Company, trigger: str = "manual", force: bool = False) -> ScanJob:
    trigger = normalize_scan_trigger(trigger)
    with transaction.atomic():
        active_scan = (
            ScanJob.objects.select_for_update()
            .filter(company=company, status__in=ACTIVE_SCAN_STATUSES)
            .order_by("-requested_at")
            .first()
        )
        if active_scan and not force:
            raise ScanAlreadyRunning(f"{company.name} already has a {active_scan.status} scan.")
        return ScanJob.objects.create(
            company=company,
            trigger=trigger,
            source_platform=company.scraper_type,
        )


def execute_scan_job(scan_job: ScanJob, scraper=None) -> ScrapeLog:
    started_at = timezone.now()
    previous_failure_count = scan_job.company.consecutive_failure_count
    scan_job.status = "running"
    scan_job.started_at = started_at
    scan_job.message = ""
    scan_job.save(update_fields=["status", "started_at", "message", "updated_at"])

    log = scrape_company_jobs(scan_job.company, scraper=scraper)
    scan_job.scrape_log = log
    scan_job.source_platform = log.source_platform or scan_job.company.scraper_type
    scan_job.jobs_found = log.jobs_found
    scan_job.jobs_created = log.jobs_created
    scan_job.jobs_updated = log.jobs_updated
    scan_job.message = log.message
    scan_job.finished_at = log.finished_at or timezone.now()
    scan_job.alerts_created = create_new_role_alerts(scan_job)

    if not scan_job.company.is_active:
        scan_job.status = "skipped"
    elif log.status == "success":
        scan_job.status = "success"
    else:
        scan_job.status = "failed"

    scan_job.save(
        update_fields=[
            "scrape_log",
            "source_platform",
            "jobs_found",
            "jobs_created",
            "jobs_updated",
            "message",
            "finished_at",
            "alerts_created",
            "status",
            "updated_at",
        ]
    )
    publish_scan_job_event(scan_job, previous_failure_count)
    return log


def create_new_role_alerts(scan_job: ScanJob) -> int:
    company = scan_job.company
    if not company.alert_new_roles or scan_job.jobs_created == 0:
        return 0

    created = 0
    jobs = Job.objects.filter(company=company, first_seen_at__gte=scan_job.started_at or scan_job.requested_at)
    for job in jobs.order_by("-first_seen_at", "title")[: scan_job.jobs_created + 25]:
        alert, was_created = JobAlert.objects.get_or_create(
            company=company,
            job=job,
            alert_type="new_role",
            defaults={
                "scan_job": scan_job,
                "title": f"New role at {company.name}: {job.title}",
                "message": new_role_alert_message(job),
            },
        )
        if was_created:
            created += 1
            publish_new_role_event(alert)
    return created


def publish_new_role_event(alert: JobAlert) -> None:
    job = alert.job
    company = alert.company
    publish_mteane_event(
        "job.new_role",
        {
            "alert_id": alert.id,
            "job_id": job.id,
            "company_id": company.id,
            "company_name": company.name,
            "company_priority": company.priority_tier,
            "source_health": company.source_health,
            "job_title": job.title,
            "job_location": job.location,
            "remote_policy": job.remote_policy,
            "source_platform": job.source_platform,
            "apply_url": job.apply_url,
            "first_seen_at": job.first_seen_at.isoformat() if job.first_seen_at else None,
        },
        idempotency_key=f"job-alert-{alert.id}",
    )


def publish_scan_job_event(scan_job: ScanJob, previous_failure_count: int = 0) -> None:
    company = scan_job.company
    base_payload = {
        "scan_job_id": scan_job.id,
        "company_id": company.id,
        "company_name": company.name,
        "company_priority": company.priority_tier,
        "source_platform": scan_job.source_platform,
        "source_health": company.source_health,
        "jobs_found": scan_job.jobs_found,
        "jobs_created": scan_job.jobs_created,
        "jobs_updated": scan_job.jobs_updated,
        "alerts_created": scan_job.alerts_created,
        "finished_at": scan_job.finished_at.isoformat() if scan_job.finished_at else None,
    }
    if scan_job.status == "failed":
        publish_mteane_event(
            "scan.failed",
            {
                **base_payload,
                "message": scan_job.message[:500],
                "consecutive_failure_count": company.consecutive_failure_count,
            },
            idempotency_key=f"scan-failed-{scan_job.id}",
        )
    elif scan_job.status == "success" and previous_failure_count:
        publish_mteane_event(
            "scan.recovered",
            {
                **base_payload,
                "previous_failure_count": previous_failure_count,
            },
            idempotency_key=f"scan-recovered-{scan_job.id}",
        )


def run_due_company_scans(limit: int = 25, force: bool = False, dry_run: bool = False, now=None) -> dict:
    now = now or timezone.now()
    candidates = [company for company in Company.objects.filter(is_active=True).order_by("name") if force or company_scan_is_due(company, now)]
    selected = candidates[: max(limit, 0)]
    scan_jobs = []
    scanned = 0
    skipped = 0
    failed = 0
    alerts_created = 0

    if dry_run:
        return {
            "scanned": 0,
            "skipped": 0,
            "failed": 0,
            "alerts_created": 0,
            "due_count": len(candidates),
            "selected_count": len(selected),
            "scan_jobs": [],
        }

    for company in selected:
        try:
            scan_job, _ = run_company_scan(company, trigger="scheduled", force=False)
        except ScanAlreadyRunning:
            skipped += 1
            continue
        scan_jobs.append(scan_job)
        scanned += 1
        alerts_created += scan_job.alerts_created
        if scan_job.status == "failed":
            failed += 1
        if scan_job.status == "skipped":
            skipped += 1

    return {
        "scanned": scanned,
        "skipped": skipped,
        "failed": failed,
        "alerts_created": alerts_created,
        "due_count": len(candidates),
        "selected_count": len(selected),
        "scan_jobs": scan_jobs,
    }


def company_scan_is_due(company: Company, now=None) -> bool:
    if not company.is_active:
        return False
    if not company.last_scraped_at:
        return True
    now = now or timezone.now()
    frequency = max(company.scan_frequency_hours or 24, 1)
    return company.last_scraped_at <= now - timedelta(hours=frequency)


def mark_alert_read(alert: JobAlert) -> JobAlert:
    alert.status = "read"
    alert.read_at = timezone.now()
    alert.save(update_fields=["status", "read_at"])
    return alert


def dismiss_alert(alert: JobAlert) -> JobAlert:
    alert.status = "dismissed"
    alert.dismissed_at = timezone.now()
    alert.save(update_fields=["status", "dismissed_at"])
    return alert


def mark_company_scan_success(company: Company, message: str = "", jobs_created: int = 0) -> Company:
    now = timezone.now()
    company.last_scraped_at = now
    company.last_scrape_status = "success"
    company.last_scrape_message = message[:1000]
    company.last_successful_scan_at = now
    company.consecutive_failure_count = 0
    company.source_health = "active"
    update_fields = [
        "last_scraped_at",
        "last_scrape_status",
        "last_scrape_message",
        "last_successful_scan_at",
        "consecutive_failure_count",
        "source_health",
        "updated_at",
    ]
    if jobs_created:
        company.last_new_role_at = now
        update_fields.append("last_new_role_at")
    company.save(update_fields=update_fields)
    return company


def mark_company_scan_failure(company: Company, message: str = "") -> Company:
    now = timezone.now()
    company.last_scraped_at = now
    company.last_scrape_status = "failed"
    company.last_scrape_message = message[:1000]
    company.last_failed_scan_at = now
    company.consecutive_failure_count += 1
    company.source_health = failure_health(company.consecutive_failure_count, message)
    company.save(
        update_fields=[
            "last_scraped_at",
            "last_scrape_status",
            "last_scrape_message",
            "last_failed_scan_at",
            "consecutive_failure_count",
            "source_health",
            "updated_at",
        ]
    )
    return company


def health_for_company(company: Company) -> str:
    if not company.is_active:
        return "paused"
    if company.last_scrape_status == "success":
        return "active"
    if company.consecutive_failure_count:
        return failure_health(company.consecutive_failure_count, company.last_scrape_message)
    return "needs_setup"


def failure_health(consecutive_failure_count: int, message: str = "") -> str:
    if any(term in message.lower() for term in BLOCKED_TERMS):
        return "blocked"
    return "failing" if consecutive_failure_count >= FAILURE_THRESHOLD else "degraded"


def coerce_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", ""}
    return bool(value)


def normalize_company_filter_updates(payload: dict) -> dict:
    updates = {}
    for field in KEYWORD_FILTER_FIELDS:
        if field in payload:
            updates[field] = coerce_keyword_list(payload[field], field)
    work_mode_key = "work_mode_filter"
    if work_mode_key not in payload:
        for alias in ("work_mode", "remote_policy", "remote"):
            if alias in payload:
                work_mode_key = alias
                break
    if work_mode_key in payload:
        updates["work_mode_filter"] = normalize_work_mode_filter(payload.get(work_mode_key))
    if "scan_frequency_hours" in payload:
        updates["scan_frequency_hours"] = normalize_scan_frequency_hours(payload.get("scan_frequency_hours"))
    if "alert_new_roles" in payload:
        updates["alert_new_roles"] = coerce_bool(payload.get("alert_new_roles"))
    return updates


def normalize_scan_frequency_hours(value) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("scan_frequency_hours must be a number")
    if parsed < 1 or parsed > 720:
        raise ValueError("scan_frequency_hours must be between 1 and 720")
    return parsed


def normalize_scan_trigger(value) -> str:
    trigger = str(value or "manual").strip().lower()
    allowed = {choice[0] for choice in ScanJob.TRIGGER_CHOICES}
    if trigger not in allowed:
        raise ValueError(f"trigger must be one of: {', '.join(sorted(allowed))}")
    return trigger


def coerce_keyword_list(value, field_name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        items = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        raise ValueError(f"{field_name} must be a list or comma-separated string")

    keywords = []
    seen = set()
    for item in items:
        keyword = str(item or "").strip()
        if not keyword:
            continue
        key = keyword.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(keyword[:120])
    return keywords


def normalize_work_mode_filter(value) -> str:
    work_mode_filter = str(value or "").strip().casefold()
    work_mode_filter = WORK_MODE_ALIASES.get(work_mode_filter, work_mode_filter)
    if work_mode_filter not in WORK_MODE_FILTERS:
        raise ValueError(f"work_mode_filter must be one of: {', '.join(sorted(WORK_MODE_FILTERS))}")
    return work_mode_filter


def normalize_priority_tier(value) -> str:
    priority_tier = str(value or "").strip() or "normal"
    if priority_tier not in PRIORITY_TIERS:
        raise ValueError(f"priority_tier must be one of: {', '.join(sorted(PRIORITY_TIERS))}")
    return priority_tier


def job_matches_company_filters(company: Company, item) -> bool:
    title = item.title.casefold()
    location = item.location.casefold()
    title_keywords = [keyword.casefold() for keyword in company.title_keywords]
    negative_title_keywords = [keyword.casefold() for keyword in company.negative_title_keywords]
    location_keywords = [keyword.casefold() for keyword in company.location_keywords]

    if title_keywords and not any(keyword in title for keyword in title_keywords):
        return False
    if negative_title_keywords and any(keyword in title for keyword in negative_title_keywords):
        return False
    if location_keywords and not any(keyword in location for keyword in location_keywords):
        return False
    if company.work_mode_filter != "any" and item.remote_policy != company.work_mode_filter:
        return False
    return True


def filter_scan_message(jobs_found: int, jobs_matched: int, jobs_created: int, jobs_updated: int) -> str:
    if jobs_found == jobs_matched:
        return f"Found {jobs_found} jobs. Created {jobs_created}, updated {jobs_updated}."
    return f"Found {jobs_found} jobs. Matched {jobs_matched} filters. Created {jobs_created}, updated {jobs_updated}."


def new_role_alert_message(job: Job) -> str:
    details = [job.title]
    if job.location:
        details.append(job.location)
    if job.remote_policy and job.remote_policy != "unknown":
        details.append(job.remote_policy)
    return " | ".join(details)


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


def infer_name_from_url(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or url).replace("www.", "")
    parts = host.split(".")
    return (parts[-2] if len(parts) > 1 else parts[0]).replace("-", " ").title()
