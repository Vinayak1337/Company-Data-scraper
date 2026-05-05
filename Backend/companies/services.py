import csv
from dataclasses import dataclass
from datetime import timedelta
import ipaddress
from io import StringIO
from urllib.parse import urlsplit

from django.db import IntegrityError, transaction
from django.utils import timezone

from companies.models import Company, CompanyJobSource, JobAlert, ScanJob, ScrapeLog
from jobs.models import Job
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
SOURCE_PATH_CANDIDATES = ("careers", "jobs", "open-roles", "openings", "join-us")


class ScanAlreadyRunning(ValueError):
    pass


@dataclass(frozen=True)
class ScheduledScanSummary:
    scanned: int = 0
    skipped: int = 0
    failed: int = 0
    alerts_created: int = 0
    scan_jobs: tuple[ScanJob, ...] = ()


def create_company(payload: dict) -> Company:
    name = str(payload.get("name") or payload.get("company") or "").strip()
    careers_url = str(payload.get("careers_url") or "").strip()
    homepage_url = str(payload.get("homepage_url") or payload.get("domain") or "").strip()
    domain = normalize_domain(payload.get("domain") or homepage_url or careers_url)
    priority_tier = normalize_priority_tier(payload.get("priority_tier") or payload.get("priority"))
    is_active = coerce_bool(payload.get("is_active", payload.get("active", True)))
    notes = str(payload.get("notes") or "").strip()
    filter_updates = normalize_company_filter_updates(payload)

    if careers_url:
        careers_url = validate_public_careers_url(careers_url)
    if homepage_url:
        homepage_url = normalize_homepage_url(homepage_url)
    if not name:
        name = infer_name_from_url(careers_url or homepage_url or domain)
    if not name:
        raise ValueError("company name is required")

    lookup = {}
    if careers_url:
        lookup["careers_url"] = careers_url
    elif domain:
        lookup["domain"] = domain
    else:
        lookup["name"] = name[:180]

    defaults = {
        "name": name[:180],
        "domain": domain[:180],
        "homepage_url": homepage_url,
        "careers_url": careers_url,
        "priority_tier": priority_tier,
        "is_active": is_active,
        "notes": notes,
        "source_health": "needs_source",
        **filter_updates,
    }
    if careers_url:
        defaults["scraper_type"] = detect_scraper(careers_url)
        defaults["source_health"] = "needs_setup"
        defaults["source_discovery_status"] = "manual"
        defaults["source_discovery_confidence"] = 100

    company, created = Company.objects.get_or_create(defaults=defaults, **lookup)
    if not created:
        update_company(company, defaults)

    if careers_url:
        upsert_company_job_source(
            company,
            careers_url,
            discovery_method="manual",
            confidence_score=100,
            status="active",
            make_primary=True,
        )
    return company


def create_company_from_url(url: str, name: str = "", priority_tier: str = "", filters: dict | None = None) -> Company:
    payload = {"careers_url": url, "name": name, "priority_tier": priority_tier}
    payload.update(filters or {})
    return create_company(payload)


def update_company(company: Company, updates: dict) -> Company:
    update_fields = []

    if "name" in updates:
        name = str(updates.get("name") or "").strip()
        if name and company.name != name:
            company.name = name[:180]
            update_fields.append("name")

    scraper_type_supplied = "scraper_type" in updates
    if "careers_url" in updates:
        raw_careers_url = str(updates.get("careers_url") or "").strip()
        careers_url = validate_public_careers_url(raw_careers_url) if raw_careers_url else ""
        if company.careers_url != careers_url:
            company.careers_url = careers_url
            update_fields.append("careers_url")
            if not scraper_type_supplied:
                company.scraper_type = detect_scraper(careers_url) if careers_url else "unknown"
                update_fields.append("scraper_type")
            if careers_url:
                upsert_company_job_source(
                    company,
                    careers_url,
                    discovery_method="manual",
                    confidence_score=100,
                    status="active",
                    make_primary=True,
                )

    if "domain" in updates:
        domain = normalize_domain(updates.get("domain"))
        if company.domain != domain:
            company.domain = domain[:180]
            update_fields.append("domain")

    if "homepage_url" in updates:
        homepage_url = normalize_homepage_url(updates.get("homepage_url"))
        if company.homepage_url != homepage_url:
            company.homepage_url = homepage_url
            update_fields.append("homepage_url")

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

    if "notes" in updates:
        notes = str(updates.get("notes") or "").strip()
        if company.notes != notes:
            company.notes = notes
            update_fields.append("notes")

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
    source = primary_job_source(company)
    log = ScrapeLog.objects.create(company=company, source=source, source_platform=(source.platform if source else company.scraper_type))
    if not company.is_active:
        message = "Company is paused; resume it before scanning."
        company.source_health = "paused"
        company.save(update_fields=["source_health", "updated_at"])
        log.finish("failed", message)
        return log
    if not source:
        message = "No active jobs source is configured for this company."
        company.source_health = "needs_source"
        company.last_scrape_status = "failed"
        company.last_scrape_message = message
        company.save(update_fields=["source_health", "last_scrape_status", "last_scrape_message", "updated_at"])
        log.finish("failed", message)
        return log

    try:
        result = scraper(source.url)
        if result.company_name and company.name == infer_name_from_url(company.careers_url or source.url):
            company.name = result.company_name[:180]
        company.scraper_type = result.source_platform
        company.save(update_fields=["name", "scraper_type", "updated_at"])
        source.platform = result.source_platform
        source.status = "active"
        source.last_checked_at = timezone.now()
        source.save(update_fields=["platform", "status", "last_checked_at", "updated_at"])

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
            source=primary_job_source(company),
            trigger=trigger,
            source_platform=company.scraper_type,
        )


def execute_scan_job(scan_job: ScanJob, scraper=None) -> ScrapeLog:
    started_at = timezone.now()
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
    return created


def run_due_company_scans(limit: int = 25, force: bool = False, dry_run: bool = False, now=None) -> dict:
    now = now or timezone.now()
    candidates = [
        company
        for company in Company.objects.filter(is_active=True).prefetch_related("job_sources").order_by("name")
        if primary_job_source(company) and (force or company_scan_is_due(company, now))
    ]
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
    if not primary_job_source(company):
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
    if not primary_job_source(company):
        return "needs_source"
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


def primary_job_source(company: Company) -> CompanyJobSource | None:
    sources = getattr(company, "_prefetched_objects_cache", {}).get("job_sources")
    if sources is not None:
        active_sources = [source for source in sources if source.status == "active"]
        primary_sources = [source for source in active_sources if source.is_primary]
        return sorted(primary_sources or active_sources, key=lambda source: (-source.confidence_score, source.id))[0] if active_sources else None
    return company.job_sources.filter(status="active").order_by("-is_primary", "-confidence_score", "id").first()


def upsert_company_job_source(
    company: Company,
    url: str,
    *,
    discovery_method: str = "deterministic_agent",
    confidence_score: int = 70,
    status: str = "needs_review",
    make_primary: bool = False,
    evidence: list[dict] | None = None,
    notes: str = "",
) -> CompanyJobSource:
    url = validate_public_careers_url(url)
    platform = detect_scraper(url)
    source, _ = CompanyJobSource.objects.update_or_create(
        url=url,
        defaults={
            "company": company,
            "source_type": "ats" if platform in {"greenhouse", "lever", "ashby", "microsoft"} else "careers",
            "platform": platform,
            "discovery_method": discovery_method,
            "confidence_score": clamp(confidence_score),
            "status": status,
            "evidence": evidence or [],
            "notes": notes[:2000],
        },
    )
    if make_primary or not company.job_sources.exclude(id=source.id).filter(is_primary=True).exists():
        company.job_sources.exclude(id=source.id).update(is_primary=False)
        source.is_primary = True
        source.status = "active" if status == "active" or confidence_score >= 85 else source.status
        source.save(update_fields=["is_primary", "status", "updated_at"])
        company.careers_url = source.url
        company.scraper_type = source.platform
        company.source_health = "needs_setup" if company.is_active else "paused"
        company.source_discovery_status = "manual" if discovery_method in {"manual", "csv"} else ("found" if source.status == "active" else "needs_review")
        company.source_discovery_confidence = source.confidence_score
        company.source_discovery_notes = source.notes
        company.save(
            update_fields=[
                "careers_url",
                "scraper_type",
                "source_health",
                "source_discovery_status",
                "source_discovery_confidence",
                "source_discovery_notes",
                "updated_at",
            ]
        )
    return source


def discover_company_sources(company: Company) -> list[CompanyJobSource]:
    candidates = source_candidates_for_company(company)
    created_sources = []
    for candidate in candidates:
        source = upsert_company_job_source(
            company,
            candidate["url"],
            discovery_method="deterministic_agent",
            confidence_score=candidate["confidence_score"],
            status="active" if candidate["confidence_score"] >= 85 else "needs_review",
            make_primary=candidate["confidence_score"] >= 85 and not primary_job_source(company),
            evidence=candidate["evidence"],
            notes=candidate["notes"],
        )
        created_sources.append(source)

    if created_sources:
        best = sorted(created_sources, key=lambda item: item.confidence_score, reverse=True)[0]
        company.source_discovery_status = "found" if best.status == "active" else "needs_review"
        company.source_discovery_confidence = best.confidence_score
        company.source_discovery_notes = best.notes
    else:
        company.source_discovery_status = "failed"
        company.source_discovery_confidence = 0
        company.source_discovery_notes = "No domain, homepage, or careers URL was available for deterministic source discovery."
    company.source_health = health_for_company(company)
    company.save(update_fields=["source_discovery_status", "source_discovery_confidence", "source_discovery_notes", "source_health", "updated_at"])
    return created_sources


def source_candidates_for_company(company: Company) -> list[dict]:
    if company.careers_url:
        return [
            {
                "url": company.careers_url,
                "confidence_score": 100,
                "evidence": [{"kind": "manual_url", "message": "Careers URL already exists on company.", "values": [company.careers_url]}],
                "notes": "Existing careers URL promoted to primary source.",
            }
        ]

    base_url = company.homepage_url or (f"https://{company.domain}" if company.domain else "")
    if not base_url:
        return []

    parsed = urlsplit(normalize_homepage_url(base_url))
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates = []
    for index, path in enumerate(SOURCE_PATH_CANDIDATES):
        confidence = 82 if path in {"careers", "jobs"} else 68
        candidates.append(
            {
                "url": f"{root}/{path}",
                "confidence_score": confidence - index,
                "evidence": [{"kind": "known_path", "message": "Generated from common careers path.", "values": [path]}],
                "notes": f"Deterministic candidate from {company.name} homepage/domain.",
            }
        )
    return candidates


def import_company_watchlist_csv(raw_csv: str) -> dict:
    if not raw_csv.strip():
        raise ValueError("CSV content is required")

    reader = csv.DictReader(StringIO(raw_csv))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row")

    companies = []
    errors = []
    for index, row in enumerate(reader, start=2):
        payload = normalize_csv_company_row(row)
        try:
            company = create_company(payload)
            if not primary_job_source(company) and payload.get("auto_discover", True):
                discover_company_sources(company)
            companies.append(company)
        except Exception as exc:
            errors.append({"row": index, "error": str(exc), "input": row})

    return {"created_or_updated": len(companies), "errors": errors, "companies": companies}


def normalize_csv_company_row(row: dict) -> dict:
    lower = {str(key or "").strip().lower(): value for key, value in row.items()}
    return {
        "name": lower.get("company") or lower.get("name") or "",
        "domain": lower.get("domain") or "",
        "homepage_url": lower.get("homepage_url") or lower.get("website") or "",
        "careers_url": lower.get("careers_url") or lower.get("jobs_url") or "",
        "priority_tier": lower.get("priority") or lower.get("priority_tier") or "normal",
        "is_active": lower.get("active", lower.get("is_active", True)),
        "notes": lower.get("notes") or "",
    }


def normalize_domain(value) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or value).strip().lower().removeprefix("www.")
    if not host or "." not in host:
        return ""
    return host[:180]


def normalize_homepage_url(value) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlsplit(candidate)
    if not parsed.netloc:
        raise ValueError("homepage_url must include a public hostname")
    return validate_public_careers_url(f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/"))


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


def clamp(value: int) -> int:
    return max(0, min(100, int(value)))
