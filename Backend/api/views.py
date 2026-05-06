import json

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from agents.models import AgentDecision, AgentProviderSetting, AgentRun
from agents.services import (
    agent_runtime_status,
    cancel_agent_run,
    ensure_provider_settings,
    provider_runtime_status,
    retry_agent_run,
    set_agent_decision_status,
    start_agent_run,
    update_provider_setting,
)
from companies.models import Company, CompanyJobSource, JobAlert, ScanJob, ScrapeLog
from companies.services import (
    ScanAlreadyRunning,
    create_company,
    delete_company,
    discover_company_sources,
    import_company_watchlist_csv,
    pause_company,
    resume_company,
    run_company_scan,
    run_due_company_scans,
    update_company,
    upsert_company_job_source,
)
from jobs.models import Job
from matching.models import JobMatch, MatchFeedback
from matching.services import record_match_feedback, refresh_job_match, refresh_job_matches, serialize_job_match
from notifications.services import (
    create_notification_event,
    create_notification_events_for_company,
    get_notification_preferences,
    notification_preferences_status,
    serialize_notification_preferences,
    update_notification_preferences,
)
from profiles.models import CandidateProfile, ProfileClaim, SearchStrategy, TargetTitle, UserSearchPreference
from profiles.services import (
    apply_search_strategy_to_company_filters,
    apply_accepted_titles_to_company_filters,
    compute_profile_completeness,
    generate_search_strategy,
    generate_target_titles,
    get_profile,
    get_search_strategy,
    import_resume,
    set_claim_status,
    set_target_title_status,
    update_profile,
    update_search_strategy,
)


COMPANY_UPDATE_FIELDS = (
    "name",
    "domain",
    "homepage_url",
    "careers_url",
    "scraper_type",
    "priority_tier",
    "is_active",
    "scan_frequency_hours",
    "alert_new_roles",
    "notes",
)


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "error"}, status=500)
    return JsonResponse(
        {
            "status": "ok",
            "version": "v3",
            "auth_required": bool(getattr(settings, "JOB_SCOUT_REQUIRE_AUTH", False)),
            "auth_configured": bool(getattr(settings, "JOB_SCOUT_API_TOKEN", "")),
        }
    )


@require_GET
def diagnostics(request: HttpRequest) -> JsonResponse:
    profile = CandidateProfile.objects.order_by("id").first()
    preferences = get_notification_preferences()
    active_companies = Company.objects.filter(is_active=True).count()
    companies_needing_source = Company.objects.filter(source_health__in=["needs_source", "needs_review"]).count()
    return JsonResponse(
        {
            "database": "ok",
            "setup": {
                "profile_complete": bool(profile and compute_profile_completeness(profile) >= 70),
                "ai_configured": any(provider.enabled for provider in ensure_provider_settings()),
                "notifications_configured": notification_preferences_status(preferences)["configured"],
                "company_watchlist_ready": active_companies > 0,
            },
            "counts": {
                "companies": Company.objects.count(),
                "active_companies": active_companies,
                "companies_needing_source": companies_needing_source,
                "jobs": Job.objects.count(),
                "matches_to_notify": refresh_current_matches_count(),
                "crawl_runs": ScanJob.objects.count(),
            },
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def profile_detail(request: HttpRequest) -> JsonResponse:
    profile = get_profile()
    if request.method == "GET":
        return JsonResponse(serialize_profile(profile))

    try:
        profile = update_profile(profile, profile_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_profile(profile))


@csrf_exempt
@require_http_methods(["POST"])
def profile_import_resume(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    try:
        profile = import_resume(get_profile(), str(payload.get("resume_text") or payload.get("cv_text") or ""))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_profile(profile))


@csrf_exempt
@require_http_methods(["POST"])
def profile_generate_titles(request: HttpRequest) -> JsonResponse:
    profile = get_profile()
    generate_target_titles(profile)
    return JsonResponse(serialize_profile(profile))


@csrf_exempt
@require_http_methods(["POST"])
def target_title_status(request: HttpRequest, title_id: int, status: str) -> JsonResponse:
    try:
        target_title = set_target_title_status(get_object_or_404(TargetTitle, pk=title_id), status)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_target_title(target_title))


@csrf_exempt
@require_http_methods(["POST"])
def profile_claim_status(request: HttpRequest, claim_id: int, status: str) -> JsonResponse:
    try:
        claim = set_claim_status(get_object_or_404(ProfileClaim, pk=claim_id), status)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_profile_claim(claim))


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def profile_search_strategy_detail(request: HttpRequest) -> JsonResponse:
    strategy = get_search_strategy(get_profile())
    if request.method == "GET":
        return JsonResponse(serialize_search_strategy(strategy))
    try:
        strategy = update_search_strategy(strategy, search_strategy_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_search_strategy(strategy))


@csrf_exempt
@require_http_methods(["POST"])
def profile_generate_search_strategy(request: HttpRequest) -> JsonResponse:
    return JsonResponse(serialize_search_strategy(generate_search_strategy(get_profile())))


@csrf_exempt
@require_http_methods(["POST"])
def profile_apply_search_strategy(request: HttpRequest) -> JsonResponse:
    try:
        result = apply_search_strategy_to_company_filters(get_profile())
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "updated_count": result["updated_count"],
            "strategy": serialize_search_strategy(result["strategy"]),
            "companies": [serialize_company(company) for company in result["companies"]],
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def profile_apply_titles_to_companies(request: HttpRequest) -> JsonResponse:
    try:
        result = apply_accepted_titles_to_company_filters(get_profile())
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "updated_count": result["updated_count"],
            "titles": result["titles"],
            "companies": [serialize_company(company) for company in result["companies"]],
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def notification_preferences_detail(request: HttpRequest) -> JsonResponse:
    preference = get_notification_preferences()
    if request.method == "GET":
        return JsonResponse(serialize_notification_preferences(preference))
    try:
        preference = update_notification_preferences(preference, notification_preferences_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_notification_preferences(preference))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def companies_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            company = create_company(request_payload(request))
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_company(company), status=201)

    companies = Company.objects.prefetch_related("job_sources").order_by("name")
    return JsonResponse({"count": companies.count(), "results": [serialize_company(company) for company in companies]})


@csrf_exempt
@require_http_methods(["POST"])
def companies_import_csv(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    raw_csv = str(payload.get("csv") or payload.get("content") or "")
    try:
        result = import_company_watchlist_csv(raw_csv)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "created_or_updated": result["created_or_updated"],
            "errors": result["errors"],
            "companies": [serialize_company(company) for company in result["companies"]],
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
def company_detail(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company.objects.prefetch_related("job_sources"), pk=company_id)
    if request.method == "GET":
        return JsonResponse(serialize_company(company))
    if request.method == "DELETE":
        deleted_id = company.id
        delete_company(company)
        return JsonResponse({"deleted": True, "id": deleted_id})
    try:
        company = update_company(company, company_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_company(company))


@csrf_exempt
@require_http_methods(["POST"])
def company_pause(request: HttpRequest, company_id: int) -> JsonResponse:
    return JsonResponse(serialize_company(pause_company(get_object_or_404(Company, pk=company_id))))


@csrf_exempt
@require_http_methods(["POST"])
def company_resume(request: HttpRequest, company_id: int) -> JsonResponse:
    return JsonResponse(serialize_company(resume_company(get_object_or_404(Company, pk=company_id))))


@csrf_exempt
@require_http_methods(["POST"])
def company_discover_source(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    sources = discover_company_sources(company)
    company.refresh_from_db()
    return JsonResponse({"company": serialize_company(company), "sources": [serialize_company_source(source) for source in sources]})


@csrf_exempt
@require_http_methods(["POST"])
def company_sources_list(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    payload = request_payload(request)
    try:
        source = upsert_company_job_source(
            company,
            str(payload.get("url") or ""),
            discovery_method=str(payload.get("discovery_method") or "manual"),
            confidence_score=positive_int(payload.get("confidence_score"), default=100, maximum=100),
            status=str(payload.get("status") or "active"),
            make_primary=bool(payload.get("is_primary", True)),
            notes=str(payload.get("notes") or ""),
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_company_source(source), status=201)


@csrf_exempt
@require_http_methods(["PATCH", "PUT", "DELETE"])
def company_source_detail(request: HttpRequest, company_id: int, source_id: int) -> JsonResponse:
    source = get_object_or_404(CompanyJobSource, pk=source_id, company_id=company_id)
    if request.method == "DELETE":
        source.delete()
        return JsonResponse({"deleted": True, "id": source_id})
    payload = request_payload(request)
    update_fields = []
    for field in ("status", "notes"):
        if field in payload:
            setattr(source, field, str(payload.get(field) or "")[:2000])
            update_fields.append(field)
    if "confidence_score" in payload:
        source.confidence_score = positive_int(payload.get("confidence_score"), default=source.confidence_score, maximum=100)
        update_fields.append("confidence_score")
    if "is_primary" in payload and bool(payload.get("is_primary")):
        source.company.job_sources.exclude(id=source.id).update(is_primary=False)
        source.is_primary = True
        update_fields.append("is_primary")
    if update_fields:
        source.save(update_fields=[*set(update_fields), "updated_at"])
    return JsonResponse(serialize_company_source(source))


@csrf_exempt
@require_http_methods(["POST"])
def company_crawl(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    try:
        crawl_run, log = run_company_scan(company, trigger="manual", force=True)
    except (ValueError, ScanAlreadyRunning) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    refresh_new_job_matches(company)
    return scrape_response(company, log, crawl_run)


@require_GET
def crawl_runs_list(request: HttpRequest) -> JsonResponse:
    runs = ScanJob.objects.select_related("company", "source").order_by("-requested_at")
    if request.GET.get("company_id"):
        runs = runs.filter(company_id=request.GET["company_id"])
    limit = positive_int(request.GET.get("limit"), default=50, maximum=200)
    items = list(runs[:limit])
    return JsonResponse({"count": len(items), "results": [serialize_crawl_run(item) for item in items]})


@csrf_exempt
@require_http_methods(["POST"])
def crawl_run_due(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    try:
        result = run_due_company_scans(
            limit=positive_int(payload.get("limit"), default=25, maximum=200),
            force=bool(payload.get("force", False)),
            dry_run=bool(payload.get("dry_run", False)),
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    for crawl_run in result.get("scan_jobs", []):
        refresh_new_job_matches(crawl_run.company)
    return JsonResponse(
        {
            "scanned": result["scanned"],
            "skipped": result["skipped"],
            "failed": result["failed"],
            "alerts_created": result["alerts_created"],
            "due_count": result["due_count"],
            "selected_count": result["selected_count"],
            "crawl_runs": [serialize_crawl_run(crawl_run) for crawl_run in result["scan_jobs"]],
        }
    )


@require_GET
def company_logs_all(request: HttpRequest) -> JsonResponse:
    logs = ScrapeLog.objects.select_related("company", "source").order_by("-started_at")
    if request.GET.get("company_id"):
        logs = logs.filter(company_id=request.GET["company_id"])
    limit = positive_int(request.GET.get("limit"), default=20, maximum=100)
    items = list(logs[:limit])
    return JsonResponse({"count": len(items), "results": [serialize_scrape_log(log) for log in items]})


@require_GET
def jobs_list(request: HttpRequest) -> JsonResponse:
    jobs = Job.objects.select_related("company").order_by("-first_seen_at")
    if request.GET.get("company"):
        jobs = jobs.filter(company_id=request.GET["company"])
    if request.GET.get("status"):
        jobs = jobs.filter(status=request.GET["status"])
    if request.GET.get("q"):
        q = request.GET["q"]
        jobs = jobs.filter(title__icontains=q) | jobs.filter(company__name__icontains=q)
    limit = positive_int(request.GET.get("limit"), default=200, maximum=500)
    job_objects = list(jobs[:limit])
    matches = refresh_job_matches(job_objects)
    serialized = [serialize_job(job, match=matches.get(job.id)) for job in job_objects]
    if str(request.GET.get("strong_fit_first", "true")).lower() not in {"0", "false", "no"}:
        serialized.sort(key=lambda item: (item["match"]["should_notify"], item["match"]["overall_score"], item["match"]["confidence_score"]), reverse=True)
    return JsonResponse({"count": len(serialized), "results": serialized})


@require_GET
def job_detail(request: HttpRequest, job_id: int) -> JsonResponse:
    job = get_object_or_404(Job.objects.select_related("company"), pk=job_id)
    return JsonResponse(serialize_job(job, refresh_job_match(job)))


@csrf_exempt
@require_http_methods(["POST"])
def job_feedback(request: HttpRequest, job_id: int) -> JsonResponse:
    job = get_object_or_404(Job.objects.select_related("company"), pk=job_id)
    payload = request_payload(request)
    try:
        feedback = record_match_feedback(job, str(payload.get("feedback_type") or ""), str(payload.get("notes") or ""))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    job.refresh_from_db()
    match = refresh_job_match(job)
    if match.should_notify:
        create_notification_event(match)
    return JsonResponse({"feedback": serialize_match_feedback(feedback), "match": serialize_job_match(match)})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def agent_providers_list(request: HttpRequest) -> JsonResponse:
    providers = ensure_provider_settings()
    return JsonResponse({"count": len(providers), "results": [serialize_agent_provider(provider) for provider in providers]})


@csrf_exempt
@require_http_methods(["PATCH", "PUT"])
def agent_provider_detail(request: HttpRequest, provider: str) -> JsonResponse:
    ensure_provider_settings()
    provider_setting = get_object_or_404(AgentProviderSetting, provider=provider)
    try:
        provider_setting = update_provider_setting(provider_setting, agent_provider_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_provider(provider_setting))


@require_GET
def agent_runtime_detail(request: HttpRequest) -> JsonResponse:
    return JsonResponse(agent_runtime_status())


@csrf_exempt
@require_http_methods(["GET", "POST"])
def agent_runs_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        try:
            run = start_agent_run(
                agent_type=str(payload.get("agent_type") or ""),
                provider=str(payload.get("provider") or "direct_api"),
                tool_policy=str(payload.get("tool_policy") or "read_only"),
                user_consent=bool(payload.get("user_consent", False)),
            )
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_agent_run(run), status=201)

    runs = AgentRun.objects.prefetch_related("steps", "artifacts", "decisions").order_by("-requested_at")
    limit = positive_int(request.GET.get("limit"), default=50, maximum=200)
    items = list(runs[:limit])
    return JsonResponse({"count": len(items), "results": [serialize_agent_run(item) for item in items]})


@require_GET
def agent_run_detail(request: HttpRequest, run_id: int) -> JsonResponse:
    return JsonResponse(serialize_agent_run(get_object_or_404(AgentRun.objects.prefetch_related("steps", "artifacts", "decisions"), pk=run_id)))


@csrf_exempt
@require_http_methods(["POST"])
def agent_run_cancel(request: HttpRequest, run_id: int) -> JsonResponse:
    try:
        run = cancel_agent_run(get_object_or_404(AgentRun, pk=run_id))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_run(run))


@csrf_exempt
@require_http_methods(["POST"])
def agent_run_retry(request: HttpRequest, run_id: int) -> JsonResponse:
    try:
        run = retry_agent_run(get_object_or_404(AgentRun, pk=run_id))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_run(run))


@csrf_exempt
@require_http_methods(["POST"])
def agent_decision_status(request: HttpRequest, decision_id: int, status: str) -> JsonResponse:
    try:
        decision = set_agent_decision_status(get_object_or_404(AgentDecision, pk=decision_id), status)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_decision(decision))


def request_payload(request: HttpRequest) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc
        return payload if isinstance(payload, dict) else {}
    return request.POST.dict()


def company_updates_from_payload(payload: dict) -> dict:
    return {field: payload[field] for field in COMPANY_UPDATE_FIELDS if field in payload}


def profile_updates_from_payload(payload: dict) -> dict:
    allowed = (
        "full_name",
        "headline",
        "location",
        "remote_preference",
        "target_locations",
        "preferred_work_modes",
        "links",
        "skills",
        "summary",
        "dealbreakers",
        "compensation_expectation",
        "cv_markdown",
        "profile_markdown",
        "profile_yml",
        "proof_points",
        "skill_inventory",
        "career_timeline",
        "role_framing",
    )
    updates = {field: payload[field] for field in allowed if field in payload}
    links = dict(updates.get("links") or {})
    for key in ("github_url", "linkedin_url", "portfolio_url"):
        if key in payload:
            links[key.removesuffix("_url")] = payload[key]
    if links:
        updates["links"] = links
    return updates


def search_strategy_updates_from_payload(payload: dict) -> dict:
    allowed = (
        "role_families",
        "target_title_keywords",
        "negative_keywords",
        "seniority_levels",
        "location_keywords",
        "work_mode_preferences",
        "notes",
    )
    return {field: payload[field] for field in allowed if field in payload}


def notification_preferences_updates_from_payload(payload: dict) -> dict:
    allowed = (
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "timezone",
        "digest_enabled",
        "digest_frequency",
        "digest_time",
        "digest_channel",
        "email_address",
        "immediate_email_enabled",
        "minimum_match_score",
        "minimum_confidence_score",
        "max_digest_items",
    )
    return {field: payload[field] for field in allowed if field in payload}


def agent_provider_updates_from_payload(payload: dict) -> dict:
    allowed = (
        "label",
        "model_name",
        "enabled",
        "worker_only",
        "api_key_env_var",
        "default_tool_policy",
        "consent_required",
        "daily_run_limit",
        "monthly_budget_cents",
        "estimated_cost_per_run_cents",
        "notes",
    )
    return {field: payload[field] for field in allowed if field in payload}


def refresh_current_matches_count() -> int:
    # Diagnostics must stay read-only. The jobs endpoint refreshes match scores;
    # doing that here too can create concurrent writes during page load.
    return JobMatch.objects.filter(should_notify=True).count()


def refresh_new_job_matches(company: Company) -> None:
    create_notification_events_for_company(company)


def scrape_response(company: Company, log, crawl_run: ScanJob | None = None) -> JsonResponse:
    return JsonResponse(
        {
            "status": log.status,
            "message": log.message,
            "jobs_found": log.jobs_found,
            "jobs_created": log.jobs_created,
            "jobs_updated": log.jobs_updated,
            "company": serialize_company(company),
            "log": serialize_scrape_log(log),
            "crawl_run": serialize_crawl_run(crawl_run) if crawl_run else None,
            "alerts_created": crawl_run.alerts_created if crawl_run else 0,
        }
    )


def serialize_company(company: Company) -> dict:
    sources = list(company.job_sources.all()) if hasattr(company, "_prefetched_objects_cache") and "job_sources" in company._prefetched_objects_cache else list(company.job_sources.all())
    primary_source = next((source for source in sources if source.is_primary), sources[0] if sources else None)
    return {
        "id": company.id,
        "name": company.name,
        "domain": company.domain,
        "homepage_url": company.homepage_url,
        "careers_url": company.careers_url,
        "priority": company.priority_tier,
        "priority_tier": company.priority_tier,
        "scraper_type": company.scraper_type,
        "is_active": company.is_active,
        "is_paused": not company.is_active,
        "state": "active" if company.is_active else "paused",
        "source_health": company.source_health,
        "source_discovery_status": company.source_discovery_status,
        "source_discovery_confidence": company.source_discovery_confidence,
        "source_discovery_notes": company.source_discovery_notes,
        "notes": company.notes,
        "primary_source": serialize_company_source(primary_source) if primary_source else None,
        "sources": [serialize_company_source(source) for source in sources],
        "last_scraped_at": company.last_scraped_at.isoformat() if company.last_scraped_at else None,
        "last_scrape_status": company.last_scrape_status,
        "last_scrape_message": company.last_scrape_message,
        "last_successful_scan_at": company.last_successful_scan_at.isoformat() if company.last_successful_scan_at else None,
        "last_failed_scan_at": company.last_failed_scan_at.isoformat() if company.last_failed_scan_at else None,
        "consecutive_failure_count": company.consecutive_failure_count,
        "last_new_role_at": company.last_new_role_at.isoformat() if company.last_new_role_at else None,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
        "title_keywords": company.title_keywords,
        "negative_title_keywords": company.negative_title_keywords,
        "location_keywords": company.location_keywords,
        "work_mode_filter": company.work_mode_filter,
        "scan_frequency_hours": company.scan_frequency_hours,
        "alert_new_roles": company.alert_new_roles,
    }


def serialize_company_source(source: CompanyJobSource | None) -> dict | None:
    if not source:
        return None
    return {
        "id": source.id,
        "company_id": source.company_id,
        "url": source.url,
        "source_type": source.source_type,
        "platform": source.platform,
        "discovery_method": source.discovery_method,
        "confidence_score": source.confidence_score,
        "status": source.status,
        "is_primary": source.is_primary,
        "evidence": source.evidence,
        "notes": source.notes,
        "last_checked_at": source.last_checked_at.isoformat() if source.last_checked_at else None,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
    }


def serialize_scrape_log(log: ScrapeLog) -> dict:
    return {
        "id": log.id,
        "company_id": log.company_id,
        "company_name": log.company.name,
        "source_id": log.source_id,
        "source_url": log.source.url if log.source else "",
        "status": log.status,
        "source_platform": log.source_platform,
        "jobs_found": log.jobs_found,
        "jobs_created": log.jobs_created,
        "jobs_updated": log.jobs_updated,
        "message": log.message,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }


def serialize_crawl_run(crawl_run: ScanJob) -> dict:
    return {
        "id": crawl_run.id,
        "company_id": crawl_run.company_id,
        "company_name": crawl_run.company.name,
        "source_id": crawl_run.source_id,
        "source_url": crawl_run.source.url if crawl_run.source else "",
        "status": crawl_run.status,
        "trigger": crawl_run.trigger,
        "source_platform": crawl_run.source_platform,
        "message": crawl_run.message,
        "jobs_found": crawl_run.jobs_found,
        "jobs_created": crawl_run.jobs_created,
        "jobs_updated": crawl_run.jobs_updated,
        "alerts_created": crawl_run.alerts_created,
        "requested_at": crawl_run.requested_at.isoformat() if crawl_run.requested_at else None,
        "started_at": crawl_run.started_at.isoformat() if crawl_run.started_at else None,
        "finished_at": crawl_run.finished_at.isoformat() if crawl_run.finished_at else None,
        "created_at": crawl_run.created_at.isoformat() if crawl_run.created_at else None,
        "updated_at": crawl_run.updated_at.isoformat() if crawl_run.updated_at else None,
    }


def serialize_job(job: Job, match=None) -> dict:
    match = match or refresh_job_match(job)
    return {
        "id": job.id,
        "company_id": job.company_id,
        "company_name": job.company.name,
        "title": job.title,
        "location": job.location,
        "description": job.description,
        "apply_url": job.apply_url,
        "source_url": job.source_url,
        "source_platform": job.source_platform,
        "external_id": job.external_id,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "tags": job.tags,
        "remote_policy": job.remote_policy,
        "status": job.status,
        "first_seen_at": job.first_seen_at.isoformat() if job.first_seen_at else None,
        "last_seen_at": job.last_seen_at.isoformat() if job.last_seen_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "match": serialize_job_match(match),
    }


def serialize_match_feedback(feedback: MatchFeedback) -> dict:
    return {
        "id": feedback.id,
        "job_id": feedback.job_id,
        "match_id": feedback.match_id,
        "profile_id": feedback.profile_id,
        "feedback_type": feedback.feedback_type,
        "notes": feedback.notes,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


def serialize_profile(profile: CandidateProfile) -> dict:
    preference, _ = UserSearchPreference.objects.get_or_create(profile=profile)
    return {
        "id": profile.id,
        "full_name": profile.full_name,
        "headline": profile.headline,
        "location": profile.location,
        "remote_preference": profile.remote_preference,
        "target_locations": profile.target_locations,
        "preferred_work_modes": profile.preferred_work_modes,
        "links": profile.links,
        "skills": profile.skills,
        "summary": profile.summary,
        "dealbreakers": profile.dealbreakers,
        "compensation_expectation": profile.compensation_expectation,
        "cv_markdown": profile.cv_markdown,
        "profile_markdown": profile.profile_markdown,
        "profile_yml": profile.profile_yml,
        "proof_points": profile.proof_points,
        "skill_inventory": profile.skill_inventory,
        "career_timeline": profile.career_timeline,
        "role_framing": profile.role_framing,
        "profile_completeness_score": compute_profile_completeness(profile),
        "search_preferences": serialize_search_preferences(preference),
        "target_titles": [serialize_target_title(title) for title in profile.target_titles.all()],
        "claims": [serialize_profile_claim(claim) for claim in profile.claims.all()],
        "search_strategy": serialize_search_strategy(get_search_strategy(profile)),
        "last_generated_at": profile.last_generated_at.isoformat() if profile.last_generated_at else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def serialize_search_preferences(preference: UserSearchPreference) -> dict:
    return {
        "id": preference.id,
        "minimum_match_score": preference.minimum_match_score,
        "minimum_confidence_score": preference.minimum_confidence_score,
        "match_strictness": preference.match_strictness,
        "preferred_seniority": preference.preferred_seniority,
        "excluded_keywords": preference.excluded_keywords,
        "excluded_companies": preference.excluded_companies,
        "feedback_weights": preference.feedback_weights,
    }


def serialize_target_title(target_title: TargetTitle) -> dict:
    return {
        "id": target_title.id,
        "title": target_title.title,
        "fit_bucket": target_title.fit_bucket,
        "confidence_score": target_title.confidence_score,
        "knowledge_accuracy": target_title.knowledge_accuracy,
        "evidence": target_title.evidence,
        "source": target_title.source,
        "status": target_title.status,
        "created_at": target_title.created_at.isoformat() if target_title.created_at else None,
        "updated_at": target_title.updated_at.isoformat() if target_title.updated_at else None,
    }


def serialize_profile_claim(claim: ProfileClaim) -> dict:
    return {
        "id": claim.id,
        "claim_type": claim.claim_type,
        "text": claim.text,
        "evidence": claim.evidence,
        "source": claim.source,
        "status": claim.status,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
    }


def serialize_search_strategy(strategy: SearchStrategy) -> dict:
    return {
        "id": strategy.id,
        "role_families": strategy.role_families,
        "target_title_keywords": strategy.target_title_keywords,
        "negative_keywords": strategy.negative_keywords,
        "seniority_levels": strategy.seniority_levels,
        "location_keywords": strategy.location_keywords,
        "work_mode_preferences": strategy.work_mode_preferences,
        "generated_from": strategy.generated_from,
        "notes": strategy.notes,
        "last_generated_at": strategy.last_generated_at.isoformat() if strategy.last_generated_at else None,
        "applied_at": strategy.applied_at.isoformat() if strategy.applied_at else None,
    }


def serialize_agent_provider(provider: AgentProviderSetting) -> dict:
    runtime_status = provider_runtime_status(provider)
    return {
        "id": provider.id,
        "provider": provider.provider,
        "label": provider.label,
        "model_name": provider.model_name,
        "enabled": provider.enabled,
        "worker_only": provider.worker_only,
        "api_key_env_var": provider.api_key_env_var,
        "api_key_configured": runtime_status["api_key_configured"],
        "default_tool_policy": provider.default_tool_policy,
        "consent_required": provider.consent_required,
        "daily_run_limit": provider.daily_run_limit,
        "monthly_budget_cents": provider.monthly_budget_cents,
        "estimated_cost_per_run_cents": provider.estimated_cost_per_run_cents,
        "notes": provider.notes,
        **runtime_status,
    }


def serialize_agent_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "provider": run.provider,
        "model_name": run.model_name,
        "tool_policy": run.tool_policy,
        "prompt_version": run.prompt_version,
        "result_summary": run.result_summary,
        "error": run.error,
        "user_safe_error": run.user_safe_error,
        "input_snapshot": run.input_snapshot,
        "output_snapshot": run.output_snapshot,
        "requested_at": run.requested_at.isoformat() if run.requested_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "steps": [serialize_agent_step(step) for step in run.steps.all()],
        "artifacts": [serialize_agent_artifact(artifact) for artifact in run.artifacts.all()],
        "decisions": [serialize_agent_decision(decision) for decision in run.decisions.all()],
    }


def serialize_agent_step(step) -> dict:
    return {"id": step.id, "name": step.name, "status": step.status, "message": step.message}


def serialize_agent_artifact(artifact) -> dict:
    return {
        "id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "content": artifact.content,
        "metadata": artifact.metadata,
    }


def serialize_agent_decision(decision) -> dict:
    return {
        "id": decision.id,
        "decision_type": decision.decision_type,
        "status": decision.status,
        "question": decision.question,
        "proposed_changes": decision.proposed_changes,
        "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }


def positive_int(value, default: int, maximum: int) -> int:
    if value in {None, ""}:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(parsed, maximum))
