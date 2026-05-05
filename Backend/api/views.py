import json
import os
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, connection
from django.db.migrations.recorder import MigrationRecorder
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from agents.models import AgentDecision, AgentProviderSetting, AgentRun
from agents.services import (
    agent_runtime_status,
    cancel_agent_run,
    ensure_provider_settings,
    retry_agent_run,
    set_agent_decision_status,
    start_agent_run,
    update_provider_setting,
)
from agents.observability import langsmith_status
from analytics.models import AlertFeedback, LearningChange, MatchScoreCorrection, WeeklyReview
from analytics.services import (
    analytics_overview,
    generate_weekly_review,
    record_alert_feedback,
    record_match_score_correction,
    serialize_alert_feedback,
    serialize_learning_change,
    serialize_match_score_correction,
    serialize_weekly_review,
    undo_learning_change,
)
from applications.models import Application, ApplicationArtifact, TodayAction
from applications.services import (
    create_application_artifact,
    create_or_update_application,
    dismiss_today_action,
    generate_tailoring_artifacts,
    mark_today_action_done,
    save_alert_as_application,
    set_application_artifact_status,
    skip_alert,
    sync_today_actions,
    update_application,
)
from companies.models import Company, JobAlert, ScanJob, ScrapeLog
from companies.services import (
    ScanAlreadyRunning,
    coerce_bool,
    company_scan_is_due,
    create_company_from_url,
    delete_company,
    dismiss_alert,
    mark_alert_read,
    normalize_company_filter_updates,
    pause_company,
    resume_company,
    run_company_scan,
    run_due_company_scans,
    update_company,
)
from dashboard.services import filter_jobs
from discovery.models import ManualUrlInboxItem
from discovery.services import create_manual_url_item, dismiss_manual_url_item, import_manual_url_item
from intelligence.models import CompanyIntelligence, RecruiterContact
from intelligence.services import create_recruiter_contact, generate_company_intelligence
from interviews.models import InterviewPrep, OfferSupport
from interviews.services import generate_interview_prep, generate_offer_support
from jobs.models import Job
from matching.models import JobMatch
from matching.services import refresh_job_match, refresh_job_matches, serialize_job_match
from notifications.services import (
    get_notification_preferences,
    notification_preferences_status,
    serialize_notification_preferences,
    update_notification_preferences,
)
from notifications.mteane import mteane_status
from profiles.models import CandidateProfile, ProfileClaim, SearchStrategy, TargetTitle
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
    update_search_strategy,
    update_profile,
)
from api.data_ownership import (
    delete_all_personal_data,
    import_workspace_export,
    redaction_audit,
)


COMPANY_UPDATE_FIELDS = (
    "name",
    "careers_url",
    "scraper_type",
    "priority_tier",
    "is_active",
    "scan_frequency_hours",
    "alert_new_roles",
)
AI_CONFIG_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
SMTP_CONFIG_KEYS = ("SMTP_HOST", "EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "SMTP_USERNAME", "SMTP_PASSWORD")
EXPORT_APP_VERSION = "0.1.0"


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    try:
        connection.ensure_connection()
        return JsonResponse(
            {
                "status": "ok",
                "auth_required": bool(getattr(settings, "JOB_SCOUT_REQUIRE_AUTH", False)),
                "auth_configured": bool(getattr(settings, "JOB_SCOUT_API_TOKEN", "")),
            }
        )
    except Exception:
        return JsonResponse({"status": "error"}, status=500)


@require_GET
def jobs_list(request: HttpRequest) -> JsonResponse:
    job_objects = list(filter_jobs(request.GET).select_related("company")[:200])
    matches = refresh_job_matches(job_objects)
    serialized = [serialize_job(job, match=matches.get(job.id)) for job in job_objects]
    if coerce_bool(request.GET.get("strong_fit_first", True)):
        serialized.sort(key=lambda item: (item["match"]["overall_score"], item["match"]["confidence_score"]), reverse=True)
    return JsonResponse({"count": len(serialized), "results": serialized})


@require_GET
def job_detail(request: HttpRequest, job_id: int) -> JsonResponse:
    job = get_object_or_404(Job.objects.select_related("company"), pk=job_id)
    return JsonResponse(serialize_job(job, match=refresh_job_match(job)))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def discovery_inbox_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        try:
            item = create_manual_url_item(
                str(payload.get("url") or ""),
                str(payload.get("item_type") or "unknown"),
                str(payload.get("title") or ""),
                str(payload.get("notes") or ""),
            )
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_manual_url_item(item), status=201)

    status = request.GET.get("status", "pending")
    items = ManualUrlInboxItem.objects.select_related("company", "job").order_by("status", "-created_at")
    if status and status != "all":
        items = items.filter(status=status)
    limit = positive_int(request.GET.get("limit"), default=50, maximum=200)
    serialized = [serialize_manual_url_item(item) for item in items[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["POST"])
def discovery_inbox_import(request: HttpRequest, item_id: int) -> JsonResponse:
    item = get_object_or_404(ManualUrlInboxItem.objects.select_related("company", "job"), pk=item_id)
    try:
        item = import_manual_url_item(item)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_manual_url_item(item))


@csrf_exempt
@require_http_methods(["POST"])
def discovery_inbox_dismiss(request: HttpRequest, item_id: int) -> JsonResponse:
    item = dismiss_manual_url_item(get_object_or_404(ManualUrlInboxItem, pk=item_id))
    return JsonResponse(serialize_manual_url_item(item))


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
    strategy = generate_search_strategy(get_profile())
    return JsonResponse(serialize_search_strategy(strategy))


@csrf_exempt
@require_http_methods(["POST"])
def profile_apply_search_strategy(request: HttpRequest) -> JsonResponse:
    result = apply_search_strategy_to_company_filters(get_profile())
    return JsonResponse(
        {
            "updated_count": result["updated_count"],
            "strategy": serialize_search_strategy(result["strategy"]),
            "companies": [serialize_company(company) for company in result["companies"]],
        }
    )


@csrf_exempt
@require_http_methods(["GET"])
def agent_providers_list(request: HttpRequest) -> JsonResponse:
    providers = ensure_provider_settings()
    return JsonResponse({"count": len(providers), "results": [serialize_agent_provider(provider) for provider in providers]})


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def agent_provider_detail(request: HttpRequest, provider: str) -> JsonResponse:
    ensure_provider_settings()
    provider_setting = get_object_or_404(AgentProviderSetting, provider=provider)
    if request.method == "GET":
        return JsonResponse(serialize_agent_provider(provider_setting))

    try:
        provider_setting = update_provider_setting(provider_setting, agent_provider_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_provider(provider_setting))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def agent_runs_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        try:
            run = start_agent_run(
                str(payload.get("agent_type") or "profile_builder").strip(),
                provider=str(payload.get("provider") or "direct_api").strip(),
                model_name=str(payload.get("model_name") or "").strip(),
                tool_policy=str(payload.get("tool_policy") or "").strip(),
                user_consent=coerce_bool(payload.get("user_consent", False)),
            )
        except AgentProviderSetting.DoesNotExist:
            return JsonResponse({"error": "Unknown agent provider."}, status=400)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_agent_run(run), status=201)

    runs = agent_run_queryset()
    status = str(request.GET.get("status") or "").strip()
    agent_type = str(request.GET.get("agent_type") or "").strip()
    provider = str(request.GET.get("provider") or "").strip()
    if status:
        runs = runs.filter(status=status)
    if agent_type:
        runs = runs.filter(agent_type=agent_type)
    if provider:
        runs = runs.filter(provider=provider)
    limit = positive_int(request.GET.get("limit"), 50, 200)
    serialized = [serialize_agent_run(run) for run in runs[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@require_GET
def agent_run_detail(request: HttpRequest, run_id: int) -> JsonResponse:
    return JsonResponse(serialize_agent_run(get_object_or_404(agent_run_queryset(), pk=run_id)))


@csrf_exempt
@require_http_methods(["POST"])
def agent_run_cancel(request: HttpRequest, run_id: int) -> JsonResponse:
    run = cancel_agent_run(get_object_or_404(AgentRun, pk=run_id))
    return JsonResponse(serialize_agent_run(agent_run_queryset().get(pk=run.id)))


@csrf_exempt
@require_http_methods(["POST"])
def agent_run_retry(request: HttpRequest, run_id: int) -> JsonResponse:
    try:
        run = retry_agent_run(get_object_or_404(AgentRun, pk=run_id))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_run(run), status=201)


@csrf_exempt
@require_http_methods(["POST"])
def agent_decision_status(request: HttpRequest, decision_id: int, status: str) -> JsonResponse:
    try:
        decision = set_agent_decision_status(get_object_or_404(AgentDecision.objects.select_related("run"), pk=decision_id), status)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_agent_decision(decision))


@require_GET
def agent_runtime_detail(request: HttpRequest) -> JsonResponse:
    return JsonResponse(agent_runtime_status())


@require_GET
def analytics_overview_detail(request: HttpRequest) -> JsonResponse:
    return JsonResponse(analytics_overview(limit=positive_int(request.GET.get("limit"), 12, 50)))


@csrf_exempt
@require_http_methods(["POST"])
def analytics_weekly_review_generate(request: HttpRequest) -> JsonResponse:
    review = generate_weekly_review()
    return JsonResponse(serialize_weekly_review(review), status=201)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def analytics_feedback_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        alert = get_object_or_404(JobAlert.objects.select_related("company", "job"), pk=payload.get("alert_id"))
        try:
            feedback = record_alert_feedback(
                alert,
                str(payload.get("rating") or "").strip(),
                reason=str(payload.get("reason") or "").strip(),
                tags=payload.get("tags"),
            )
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_alert_feedback(feedback), status=201)

    feedback = AlertFeedback.objects.select_related("alert", "company", "job").all()
    rating = str(request.GET.get("rating") or "").strip()
    if rating:
        feedback = feedback.filter(rating=rating)
    limit = positive_int(request.GET.get("limit"), 50, 200)
    serialized = [serialize_alert_feedback(item) for item in feedback[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["POST"])
def analytics_match_corrections(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    job = get_object_or_404(Job.objects.select_related("company"), pk=payload.get("job_id"))
    try:
        correction = record_match_score_correction(
            job,
            str(payload.get("correction") or "").strip(),
            reason=str(payload.get("reason") or "").strip(),
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    refreshed_match = refresh_job_match(job)
    return JsonResponse(
        {
            "correction": serialize_match_score_correction(correction),
            "match": serialize_job_match(refreshed_match),
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def analytics_learning_change_undo(request: HttpRequest, change_id: int) -> JsonResponse:
    change = undo_learning_change(get_object_or_404(LearningChange, pk=change_id))
    return JsonResponse(serialize_learning_change(change))


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
def applications_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        job = get_object_or_404(Job.objects.select_related("company"), pk=payload.get("job_id"))
        source_alert = None
        if payload.get("source_alert_id"):
            source_alert = get_object_or_404(JobAlert, pk=payload.get("source_alert_id"))
        try:
            application = create_or_update_application(job, application_updates_from_payload(payload), source_alert=source_alert)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_application(application), status=201)

    applications = Application.objects.select_related("job", "job__company", "source_alert").prefetch_related("artifacts").all()
    status = str(request.GET.get("status") or "").strip()
    if status:
        applications = applications.filter(status=status)
    serialized = [serialize_application(application) for application in applications[:200]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
def application_detail(request: HttpRequest, application_id: int) -> JsonResponse:
    application = get_object_or_404(
        Application.objects.select_related("job", "job__company", "source_alert").prefetch_related("artifacts"),
        pk=application_id,
    )

    if request.method == "GET":
        return JsonResponse(serialize_application(application))

    if request.method == "DELETE":
        application.delete()
        return JsonResponse({"deleted": True, "id": application_id})

    try:
        application = update_application(application, application_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_application(application))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def application_artifacts_list(request: HttpRequest, application_id: int) -> JsonResponse:
    application = get_object_or_404(Application.objects.select_related("job", "job__company"), pk=application_id)
    if request.method == "POST":
        try:
            artifact = create_application_artifact(application, application_artifact_updates_from_payload(request_payload(request)))
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_application_artifact(artifact), status=201)

    artifacts = application.artifacts.all()
    return JsonResponse({"count": artifacts.count(), "results": [serialize_application_artifact(artifact) for artifact in artifacts]})


@csrf_exempt
@require_http_methods(["POST"])
def application_generate_tailoring(request: HttpRequest, application_id: int) -> JsonResponse:
    application = get_object_or_404(Application.objects.select_related("job", "job__company"), pk=application_id)
    artifacts = generate_tailoring_artifacts(application)
    return JsonResponse({"count": len(artifacts), "results": [serialize_application_artifact(artifact) for artifact in artifacts]})


@csrf_exempt
@require_http_methods(["POST"])
def application_artifact_status(request: HttpRequest, artifact_id: int, status: str) -> JsonResponse:
    try:
        artifact = set_application_artifact_status(get_object_or_404(ApplicationArtifact, pk=artifact_id), status)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_application_artifact(artifact))


@csrf_exempt
@require_http_methods(["POST"])
def application_generate_interview_prep(request: HttpRequest, application_id: int) -> JsonResponse:
    application = get_object_or_404(Application.objects.select_related("job", "job__company"), pk=application_id)
    prep = generate_interview_prep(application)
    return JsonResponse(serialize_interview_prep(prep), status=201)


@csrf_exempt
@require_http_methods(["POST"])
def application_generate_offer_support(request: HttpRequest, application_id: int) -> JsonResponse:
    application = get_object_or_404(Application.objects.select_related("job", "job__company"), pk=application_id)
    support = generate_offer_support(application)
    return JsonResponse(serialize_offer_support(support), status=201)


@csrf_exempt
@require_http_methods(["POST"])
def alert_save_application(request: HttpRequest, alert_id: int) -> JsonResponse:
    alert = get_object_or_404(JobAlert.objects.select_related("job", "company"), pk=alert_id)
    try:
        application = save_alert_as_application(alert, application_updates_from_payload(request_payload(request)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(serialize_application(application), status=201)


@csrf_exempt
@require_http_methods(["POST"])
def alert_skip_application(request: HttpRequest, alert_id: int) -> JsonResponse:
    alert = get_object_or_404(JobAlert.objects.select_related("job", "company"), pk=alert_id)
    reason = str(request_payload(request).get("notes") or "").strip()
    application = skip_alert(alert, reason=reason)
    return JsonResponse(serialize_application(application), status=201)


@require_GET
def today_actions_list(request: HttpRequest) -> JsonResponse:
    sync_today_actions()
    limit = positive_int(request.GET.get("limit"), default=50, maximum=200)
    actions = TodayAction.objects.select_related(
        "job",
        "job__company",
        "application",
        "source_alert",
    ).all()
    status = str(request.GET.get("status") or "open").strip()
    if status:
        actions = actions.filter(status=status)
    serialized = [serialize_today_action(action) for action in actions[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["POST"])
def today_action_complete(request: HttpRequest, action_id: int) -> JsonResponse:
    action = mark_today_action_done(get_object_or_404(TodayAction, pk=action_id))
    return JsonResponse(serialize_today_action(action))


@csrf_exempt
@require_http_methods(["POST"])
def today_action_dismiss(request: HttpRequest, action_id: int) -> JsonResponse:
    action = dismiss_today_action(get_object_or_404(TodayAction, pk=action_id))
    return JsonResponse(serialize_today_action(action))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def companies_list(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        payload = request_payload(request)
        url = str(payload.get("careers_url", "") or "").strip()
        name = str(payload.get("name", "") or "").strip()
        if not url:
            return JsonResponse({"error": "careers_url is required"}, status=400)
        priority_tier = payload.get("priority_tier", payload.get("priority", ""))
        try:
            company = create_company_from_url(url, name, str(priority_tier).strip(), filters=payload)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_company(company), status=201)
    companies = [serialize_company(company) for company in Company.objects.all()]
    return JsonResponse({"count": len(companies), "results": companies})


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def company_detail(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)

    if request.method == "GET":
        return JsonResponse(serialize_company(company))

    if request.method == "DELETE":
        delete_company(company)
        return JsonResponse({"deleted": True, "id": company_id})

    payload = request_payload(request)
    try:
        updates = company_updates_from_payload(payload)
        company = update_company(company, updates)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except IntegrityError:
        return JsonResponse({"error": "careers_url must be unique"}, status=409)
    return JsonResponse(serialize_company(company))


@csrf_exempt
@require_http_methods(["POST"])
def company_pause(request: HttpRequest, company_id: int) -> JsonResponse:
    company = pause_company(get_object_or_404(Company, pk=company_id))
    return JsonResponse(serialize_company(company))


@csrf_exempt
@require_http_methods(["POST"])
def company_resume(request: HttpRequest, company_id: int) -> JsonResponse:
    company = resume_company(get_object_or_404(Company, pk=company_id))
    return JsonResponse(serialize_company(company))


@csrf_exempt
@require_http_methods(["POST"])
def company_rescan(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    try:
        scan_job, log = run_company_scan(company, trigger="manual")
    except ScanAlreadyRunning as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    company.refresh_from_db()
    return scrape_response(company, log, scan_job=scan_job)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def company_intelligence_detail(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    if request.method == "POST":
        report = generate_company_intelligence(company)
        return JsonResponse(serialize_company_intelligence(report), status=201)

    report = company.intelligence_reports.first()
    if not report:
        return JsonResponse({"error": "No company intelligence generated yet."}, status=404)
    return JsonResponse(serialize_company_intelligence(report))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def company_recruiter_contacts(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    if request.method == "POST":
        try:
            contact = create_recruiter_contact(company, request_payload(request))
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(serialize_recruiter_contact(contact), status=201)

    contacts = company.recruiter_contacts.all()[:100]
    return JsonResponse({"count": len(contacts), "results": [serialize_recruiter_contact(contact) for contact in contacts]})


@csrf_exempt
@require_http_methods(["POST"])
def company_scrape(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    try:
        scan_job, log = run_company_scan(company, trigger="manual")
    except ScanAlreadyRunning as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    company.refresh_from_db()
    return scrape_response(company, log, scan_job=scan_job)


@require_GET
def company_logs(request: HttpRequest, company_id: int) -> JsonResponse:
    company = get_object_or_404(Company, pk=company_id)
    limit = positive_int(request.GET.get("limit"), default=20, maximum=100)
    logs = [serialize_scrape_log(log) for log in company.scrape_logs.all()[:limit]]
    return JsonResponse({"count": len(logs), "results": logs})


@require_GET
def company_logs_all(request: HttpRequest) -> JsonResponse:
    limit = positive_int(request.GET.get("limit"), default=20, maximum=100)
    logs = ScrapeLog.objects.select_related("company").all()
    company_id = request.GET.get("company_id")
    if company_id:
        logs = logs.filter(company_id=company_id)
    logs = logs[:limit]
    serialized = [serialize_scrape_log(log) | {"company_name": log.company.name} for log in logs]
    return JsonResponse({"count": len(serialized), "results": serialized})


@require_GET
def scan_jobs_list(request: HttpRequest) -> JsonResponse:
    limit = positive_int(request.GET.get("limit"), default=20, maximum=100)
    scans = ScanJob.objects.select_related("company", "scrape_log").all()
    status = str(request.GET.get("status") or "").strip()
    if status:
        scans = scans.filter(status=status)
    company_id = request.GET.get("company_id")
    if company_id:
        scans = scans.filter(company_id=company_id)
    serialized = [serialize_scan_job(scan_job) for scan_job in scans[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["POST"])
def scan_run(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    company_id = payload.get("company_id")
    force = coerce_bool(payload.get("force", False))

    if company_id:
        company = get_object_or_404(Company, pk=company_id)
        try:
            scan_job, log = run_company_scan(company, trigger=str(payload.get("trigger") or "manual"), force=force)
        except ScanAlreadyRunning as exc:
            return JsonResponse({"error": str(exc)}, status=409)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        company.refresh_from_db()
        response = {
            "scanned": 1,
            "skipped": 1 if scan_job.status == "skipped" else 0,
            "failed": 1 if scan_job.status == "failed" else 0,
            "alerts_created": scan_job.alerts_created,
            "scan_jobs": [serialize_scan_job(scan_job)],
            "company": serialize_company(company),
            "log": serialize_scrape_log(log),
        }
        status_code = 200 if scan_job.status == "success" else 409 if scan_job.status == "skipped" else 500
        return JsonResponse(response, status=status_code)

    limit = positive_int(payload.get("limit"), default=25, maximum=100)
    dry_run = coerce_bool(payload.get("dry_run", False))
    summary = run_due_company_scans(limit=limit, force=force, dry_run=dry_run)
    return JsonResponse(
        {
            "scanned": summary["scanned"],
            "skipped": summary["skipped"],
            "failed": summary["failed"],
            "alerts_created": summary["alerts_created"],
            "due_count": summary["due_count"],
            "selected_count": summary["selected_count"],
            "scan_jobs": [serialize_scan_job(scan_job) for scan_job in summary["scan_jobs"]],
        }
    )


@require_GET
def alerts_list(request: HttpRequest) -> JsonResponse:
    limit = positive_int(request.GET.get("limit"), default=20, maximum=100)
    alerts = JobAlert.objects.select_related("company", "job", "scan_job").all()
    status = str(request.GET.get("status") or "").strip()
    if status:
        alerts = alerts.filter(status=status)
    company_id = request.GET.get("company_id")
    if company_id:
        alerts = alerts.filter(company_id=company_id)
    serialized = [serialize_job_alert(alert) for alert in alerts[:limit]]
    return JsonResponse({"count": len(serialized), "results": serialized})


@csrf_exempt
@require_http_methods(["POST"])
def alert_read(request: HttpRequest, alert_id: int) -> JsonResponse:
    alert = mark_alert_read(get_object_or_404(JobAlert, pk=alert_id))
    return JsonResponse(serialize_job_alert(alert))


@csrf_exempt
@require_http_methods(["POST"])
def alert_dismiss(request: HttpRequest, alert_id: int) -> JsonResponse:
    alert = dismiss_alert(get_object_or_404(JobAlert, pk=alert_id))
    return JsonResponse(serialize_job_alert(alert))


@require_GET
def diagnostics(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "generated_at": timezone.now().isoformat(),
            "database": database_status(),
            "worker": worker_status(),
            "scheduler": scheduler_status(),
            "langsmith": langsmith_status(),
            "notifications": notification_preferences_status(),
            "mteane": mteane_status(),
            "ai": config_status(AI_CONFIG_KEYS),
            "smtp": config_status(SMTP_CONFIG_KEYS),
            "redaction": redaction_audit(),
            "core_counts": core_counts(),
        }
    )


@require_GET
def export_data(request: HttpRequest) -> JsonResponse:
    companies = Company.objects.all()
    jobs = Job.objects.select_related("company").all()
    logs = ScrapeLog.objects.select_related("company").all()
    scan_jobs = ScanJob.objects.select_related("company").all()
    alerts = JobAlert.objects.select_related("company", "job").all()
    applications = Application.objects.select_related("job", "job__company").all()
    today_actions = TodayAction.objects.select_related("job", "job__company").all()
    profile = CandidateProfile.objects.prefetch_related("target_titles", "claims").order_by("id").first()
    agent_providers = ensure_provider_settings()
    agent_runs = agent_run_queryset()
    alert_feedback = AlertFeedback.objects.select_related("alert", "company", "job").all()
    notification_preferences = get_notification_preferences()
    job_matches = JobMatch.objects.select_related("job", "profile").all()
    job_match_by_job_id = {match.job_id: match for match in job_matches}
    manual_inbox_items = ManualUrlInboxItem.objects.select_related("company", "job").all()
    company_intelligence = CompanyIntelligence.objects.select_related("company").all()
    recruiter_contacts = RecruiterContact.objects.select_related("company").all()
    interview_preps = InterviewPrep.objects.select_related("application", "application__job").all()
    offer_support = OfferSupport.objects.select_related("application", "application__job").all()
    weekly_reviews = WeeklyReview.objects.all()
    match_score_corrections = MatchScoreCorrection.objects.select_related("job", "job__company", "learning_change").all()
    learning_changes = LearningChange.objects.all()
    return JsonResponse(
        {
            "app_version": getattr(settings, "APP_VERSION", EXPORT_APP_VERSION),
            "schema_version": schema_version(),
            "generated_at": timezone.now().isoformat(),
            "profile": serialize_profile(profile) if profile else None,
            "companies": [serialize_company(company) for company in companies],
            "jobs": [serialize_job_export(job, match=job_match_by_job_id.get(job.id)) for job in jobs],
            "scan_logs": [serialize_scrape_log_summary(log) for log in logs],
            "scan_jobs": [serialize_scan_job(scan_job) for scan_job in scan_jobs],
            "alerts": [serialize_job_alert_summary(alert) for alert in alerts],
            "applications": [serialize_application(application) for application in applications],
            "today_actions": [serialize_today_action_summary(action) for action in today_actions],
            "agent_providers": [serialize_agent_provider(provider) for provider in agent_providers],
            "agent_runs": [serialize_agent_run(run) for run in agent_runs],
            "alert_feedback": [serialize_alert_feedback(feedback) for feedback in alert_feedback],
            "notification_preferences": serialize_notification_preferences(notification_preferences),
            "job_matches": [serialize_job_match(match) for match in job_matches],
            "manual_url_inbox": [serialize_manual_url_item(item) for item in manual_inbox_items],
            "company_intelligence": [serialize_company_intelligence(report) for report in company_intelligence],
            "recruiter_contacts": [serialize_recruiter_contact(contact) for contact in recruiter_contacts],
            "interview_preps": [serialize_interview_prep(prep) for prep in interview_preps],
            "offer_support": [serialize_offer_support(support) for support in offer_support],
            "weekly_reviews": [serialize_weekly_review(review) for review in weekly_reviews],
            "match_score_corrections": [serialize_match_score_correction(correction) for correction in match_score_corrections],
            "learning_changes": [serialize_learning_change(change) for change in learning_changes],
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def import_companies(request: HttpRequest) -> JsonResponse:
    payload = parse_json(request)
    if isinstance(payload, dict):
        items = payload.get("companies") or payload.get("watchlist") or payload.get("company_watchlist")
    else:
        items = payload
    if not isinstance(items, list):
        return JsonResponse({"error": "Payload must be a list or an object with a companies list."}, status=400)

    created = []
    updated = []
    errors = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append({"index": index, "error": "Company entry must be an object."})
            continue

        url = str(item.get("careers_url", "") or "").strip()
        if not url:
            errors.append({"index": index, "error": "careers_url is required."})
            continue

        try:
            company = Company.objects.filter(careers_url=url).first()
            if company:
                updates = company_updates_from_payload(item)
                updates.pop("careers_url", None)
                company = update_company(company, updates)
                updated.append(serialize_company(company))
            else:
                priority_tier = item.get("priority_tier", item.get("priority", ""))
                company = create_company_from_url(
                    url,
                    str(item.get("name", "") or "").strip(),
                    str(priority_tier).strip(),
                    filters=item,
                )
                updates = company_updates_from_payload(item)
                updates.pop("careers_url", None)
                company = update_company(company, updates)
                created.append(serialize_company(company))
        except IntegrityError:
            errors.append({"index": index, "careers_url": url, "error": "careers_url must be unique."})
        except ValueError as exc:
            errors.append({"index": index, "careers_url": url, "error": str(exc)})

    return JsonResponse(
        {
            "created": created,
            "updated": updated,
            "errors": errors,
            "created_count": len(created),
            "updated_count": len(updated),
            "error_count": len(errors),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def import_workspace(request: HttpRequest) -> JsonResponse:
    try:
        result = import_workspace_export(parse_json(request))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result, status=200 if result["status"] == "ok" else 207)


@csrf_exempt
@require_http_methods(["POST"])
def delete_personal_data(request: HttpRequest) -> JsonResponse:
    payload = request_payload(request)
    try:
        result = delete_all_personal_data(str(payload.get("confirmation") or ""))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result)


@require_GET
def redaction_audit_detail(request: HttpRequest) -> JsonResponse:
    return JsonResponse(redaction_audit())


def request_payload(request: HttpRequest) -> dict:
    payload = parse_json(request)
    if not isinstance(payload, dict):
        payload = {}
    if request.POST:
        payload.update(request.POST.dict())
    return payload


def agent_run_queryset():
    return AgentRun.objects.prefetch_related(
        "steps",
        "artifacts",
        "decisions",
        "permissions",
        "runtime_invocations",
        "audit_logs",
    )


def parse_json(request: HttpRequest):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def company_updates_from_payload(payload: dict) -> dict:
    updates = {field: payload[field] for field in COMPANY_UPDATE_FIELDS if field in payload}
    updates.update(normalize_company_filter_updates(payload))
    if "priority" in payload and "priority_tier" not in updates:
        updates["priority_tier"] = payload["priority"]
    if "is_paused" in payload and "is_active" not in updates:
        updates["is_active"] = not coerce_bool(payload["is_paused"])
    if "state" in payload and "is_active" not in updates:
        updates["is_active"] = str(payload["state"]).strip().lower() != "paused"
    return updates


def application_updates_from_payload(payload: dict) -> dict:
    fields = ("status", "notes", "next_action", "follow_up_at")
    return {field: payload[field] for field in fields if field in payload}


def application_artifact_updates_from_payload(payload: dict) -> dict:
    fields = ("artifact_type", "title", "content", "status", "metadata", "generated_by")
    return {field: payload[field] for field in fields if field in payload}


def profile_updates_from_payload(payload: dict) -> dict:
    fields = (
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
    return {field: payload[field] for field in fields if field in payload}


def search_strategy_updates_from_payload(payload: dict) -> dict:
    fields = (
        "role_families",
        "target_title_keywords",
        "negative_keywords",
        "seniority_levels",
        "location_keywords",
        "work_mode_preferences",
        "notes",
    )
    return {field: payload[field] for field in fields if field in payload}


def agent_provider_updates_from_payload(payload: dict) -> dict:
    fields = (
        "enabled",
        "model_name",
        "default_tool_policy",
        "consent_required",
        "daily_run_limit",
        "monthly_budget_cents",
        "estimated_cost_per_run_cents",
        "notes",
    )
    return {field: payload[field] for field in fields if field in payload}


def notification_preferences_updates_from_payload(payload: dict) -> dict:
    fields = (
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "timezone",
        "digest_enabled",
        "digest_frequency",
        "digest_time",
        "digest_channel",
    )
    return {field: payload[field] for field in fields if field in payload}


def positive_int(value, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return min(parsed, maximum)


def database_status() -> dict:
    try:
        connection.ensure_connection()
        return {"status": "ok", "vendor": connection.vendor}
    except Exception as exc:
        return {"status": "error", "error_type": exc.__class__.__name__}


def worker_status() -> dict:
    runtime = agent_runtime_status()
    now = timezone.now()
    stale_cutoff = now - timedelta(minutes=30)
    stale_runs = AgentRun.objects.filter(status="running", started_at__lt=stale_cutoff).count()
    latest_run = AgentRun.objects.order_by("-updated_at").first()
    status = "error" if stale_runs else "ok"
    if runtime["execution_mode"] != "queued":
        status = "warning"
    return {
        "name": "Agent worker",
        "status": status,
        "configured": runtime["execution_mode"] == "queued",
        "execution_mode": runtime["execution_mode"],
        "command": "python manage.py process_agent_queue",
        "queued_runs": runtime["queued_runs"],
        "running_runs": runtime["running_runs"],
        "stale_running_runs": stale_runs,
        "last_activity_at": latest_run.updated_at.isoformat() if latest_run else None,
        "message": (
            "Queued worker mode is configured."
            if runtime["execution_mode"] == "queued"
            else "Agent runs execute inline unless AGENT_EXECUTION_MODE=queued is set."
        ),
    }


def scheduler_status() -> dict:
    now = timezone.now()
    due_count = sum(1 for company in Company.objects.filter(is_active=True) if company_scan_is_due(company, now))
    active_scans = ScanJob.objects.filter(status__in=["queued", "running"]).count()
    stale_scans = ScanJob.objects.filter(status="running", started_at__lt=now - timedelta(minutes=30)).count()
    latest_scan = ScanJob.objects.order_by("-updated_at").first()
    scanner_configured = bool(getattr(settings, "SCANNER_ENABLED", False))
    if not scanner_configured:
        scanner_configured = bool(os.environ.get("SCAN_INTERVAL_SECONDS") or os.environ.get("SCAN_BATCH_LIMIT"))
    return {
        "name": "Scheduled scanner",
        "status": "error" if stale_scans else "ok",
        "configured": scanner_configured,
        "command": "python manage.py scan_due_companies",
        "due_companies": due_count,
        "active_scans": active_scans,
        "stale_running_scans": stale_scans,
        "last_scan_activity_at": latest_scan.updated_at.isoformat() if latest_scan else None,
        "message": "Management command scheduler is available; Docker/VPS deployments run it as a separate scanner service.",
    }


def config_status(keys: tuple[str, ...]) -> dict:
    configured = any(os.environ.get(key) for key in keys)
    return {"status": "configured" if configured else "not_configured", "configured": configured}


def core_counts() -> dict:
    return {
        "companies": Company.objects.count(),
        "active_companies": Company.objects.filter(is_active=True).count(),
        "jobs": Job.objects.count(),
        "scrape_logs": ScrapeLog.objects.count(),
        "scan_jobs": ScanJob.objects.count(),
        "unread_alerts": JobAlert.objects.filter(status="unread").count(),
        "applications": Application.objects.count(),
        "application_artifacts": ApplicationArtifact.objects.count(),
        "open_today_actions": TodayAction.objects.filter(status="open").count(),
        "profiles": CandidateProfile.objects.count(),
        "target_titles": TargetTitle.objects.count(),
        "unconfirmed_claims": ProfileClaim.objects.filter(status="unconfirmed").count(),
        "agent_runs": AgentRun.objects.count(),
        "failed_agent_runs": AgentRun.objects.filter(status="failed").count(),
        "alert_feedback": AlertFeedback.objects.count(),
        "notification_preferences": 1 if get_notification_preferences() else 0,
        "job_matches": JobMatch.objects.count(),
        "manual_url_inbox": ManualUrlInboxItem.objects.count(),
        "pending_manual_url_inbox": ManualUrlInboxItem.objects.filter(status="pending").count(),
        "company_intelligence": CompanyIntelligence.objects.count(),
        "recruiter_contacts": RecruiterContact.objects.count(),
        "interview_preps": InterviewPrep.objects.count(),
        "offer_support": OfferSupport.objects.count(),
        "weekly_reviews": WeeklyReview.objects.count(),
    }


def schema_version() -> str:
    try:
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()
    except Exception:
        return "unknown"
    latest_by_app = {}
    for app, name in applied:
        if app in {"agents", "analytics", "applications", "companies", "discovery", "intelligence", "interviews", "jobs", "matching", "notifications", "profiles"}:
            latest_by_app[app] = max(name, latest_by_app.get(app, ""))
    if not latest_by_app:
        return "unmigrated"
    return ";".join(f"{app}.{name}" for app, name in sorted(latest_by_app.items()))


def scrape_response(company: Company, log, scan_job: ScanJob | None = None) -> JsonResponse:
    status_code = 200 if log.status == "success" else 500
    if log.status == "failed" and not company.is_active:
        status_code = 409

    return JsonResponse(
        {
            "status": log.status,
            "message": log.message,
            "jobs_found": log.jobs_found,
            "jobs_created": log.jobs_created,
            "jobs_updated": log.jobs_updated,
            "company": serialize_company(company),
            "log": serialize_scrape_log(log),
            "scan_job": serialize_scan_job(scan_job) if scan_job else None,
            "alerts_created": scan_job.alerts_created if scan_job else 0,
        },
        status=status_code,
    )


def serialize_company(company: Company) -> dict:
    latest_intelligence = company.intelligence_reports.first()
    return {
        "id": company.id,
        "name": company.name,
        "careers_url": company.careers_url,
        "priority": company.priority_tier,
        "priority_tier": company.priority_tier,
        "scraper_type": company.scraper_type,
        "is_active": company.is_active,
        "is_paused": not company.is_active,
        "state": "active" if company.is_active else "paused",
        "source_health": company.source_health,
        "title_keywords": company.title_keywords,
        "negative_title_keywords": company.negative_title_keywords,
        "location_keywords": company.location_keywords,
        "work_mode_filter": company.work_mode_filter,
        "scan_frequency_hours": company.scan_frequency_hours,
        "alert_new_roles": company.alert_new_roles,
        "last_scraped_at": company.last_scraped_at.isoformat() if company.last_scraped_at else None,
        "last_scrape_status": company.last_scrape_status,
        "last_scrape_message": company.last_scrape_message,
        "last_successful_scan_at": company.last_successful_scan_at.isoformat() if company.last_successful_scan_at else None,
        "last_failed_scan_at": company.last_failed_scan_at.isoformat() if company.last_failed_scan_at else None,
        "consecutive_failure_count": company.consecutive_failure_count,
        "last_new_role_at": company.last_new_role_at.isoformat() if company.last_new_role_at else None,
        "latest_intelligence": serialize_company_intelligence(latest_intelligence) if latest_intelligence else None,
        "recruiter_contacts_count": company.recruiter_contacts.count(),
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
    }


def serialize_company_intelligence(report: CompanyIntelligence) -> dict:
    return {
        "id": report.id,
        "company_id": report.company_id,
        "summary": report.summary,
        "research_notes": report.research_notes,
        "hiring_signals": report.hiring_signals,
        "role_patterns": report.role_patterns,
        "role_legitimacy": report.role_legitimacy,
        "caveats": report.caveats,
        "hiring_team_hints": report.hiring_team_hints,
        "interview_process_notes": report.interview_process_notes,
        "risk_flags": report.risk_flags,
        "user_notes": report.user_notes,
        "source_snapshot": report.source_snapshot,
        "verification_status": report.verification_status,
        "generated_by": report.generated_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def serialize_recruiter_contact(contact: RecruiterContact) -> dict:
    return {
        "id": contact.id,
        "company_id": contact.company_id,
        "name": contact.name,
        "title": contact.title,
        "source_url": contact.source_url,
        "source_label": contact.source_label,
        "public_source_only": contact.public_source_only,
        "status": contact.status,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


def serialize_scrape_log(log) -> dict:
    return {
        "id": log.id,
        "company_id": log.company_id,
        "status": log.status,
        "source_platform": log.source_platform,
        "jobs_found": log.jobs_found,
        "jobs_created": log.jobs_created,
        "jobs_updated": log.jobs_updated,
        "message": log.message,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }


def serialize_scrape_log_summary(log) -> dict:
    return {
        "id": log.id,
        "company_id": log.company_id,
        "company": log.company.name,
        "status": log.status,
        "source_platform": log.source_platform,
        "jobs_found": log.jobs_found,
        "jobs_created": log.jobs_created,
        "jobs_updated": log.jobs_updated,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }


def serialize_scan_job(scan_job: ScanJob) -> dict:
    return {
        "id": scan_job.id,
        "company_id": scan_job.company_id,
        "company_name": scan_job.company.name,
        "scrape_log_id": scan_job.scrape_log_id,
        "status": scan_job.status,
        "trigger": scan_job.trigger,
        "source_platform": scan_job.source_platform,
        "message": scan_job.message,
        "jobs_found": scan_job.jobs_found,
        "jobs_created": scan_job.jobs_created,
        "jobs_updated": scan_job.jobs_updated,
        "alerts_created": scan_job.alerts_created,
        "requested_at": scan_job.requested_at.isoformat() if scan_job.requested_at else None,
        "started_at": scan_job.started_at.isoformat() if scan_job.started_at else None,
        "finished_at": scan_job.finished_at.isoformat() if scan_job.finished_at else None,
        "created_at": scan_job.created_at.isoformat() if scan_job.created_at else None,
        "updated_at": scan_job.updated_at.isoformat() if scan_job.updated_at else None,
    }


def serialize_scan_job_summary(scan_job: ScanJob) -> dict:
    return {
        "id": scan_job.id,
        "company_id": scan_job.company_id,
        "company": scan_job.company.name,
        "status": scan_job.status,
        "trigger": scan_job.trigger,
        "source_platform": scan_job.source_platform,
        "jobs_found": scan_job.jobs_found,
        "jobs_created": scan_job.jobs_created,
        "jobs_updated": scan_job.jobs_updated,
        "alerts_created": scan_job.alerts_created,
        "requested_at": scan_job.requested_at.isoformat() if scan_job.requested_at else None,
        "finished_at": scan_job.finished_at.isoformat() if scan_job.finished_at else None,
    }


def serialize_job_alert(alert: JobAlert) -> dict:
    return {
        "id": alert.id,
        "company_id": alert.company_id,
        "company_name": alert.company.name,
        "job_id": alert.job_id,
        "job_title": alert.job.title,
        "job_apply_url": alert.job.apply_url,
        "scan_job_id": alert.scan_job_id,
        "alert_type": alert.alert_type,
        "status": alert.status,
        "title": alert.title,
        "message": alert.message,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
        "dismissed_at": alert.dismissed_at.isoformat() if alert.dismissed_at else None,
    }


def serialize_job_alert_summary(alert: JobAlert) -> dict:
    return {
        "id": alert.id,
        "company_id": alert.company_id,
        "company": alert.company.name,
        "job_id": alert.job_id,
        "alert_type": alert.alert_type,
        "status": alert.status,
        "title": alert.title,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def serialize_application(application: Application) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "job_title": application.job.title,
        "company_id": application.job.company_id,
        "company_name": application.job.company.name,
        "apply_url": application.job.apply_url,
        "location": application.job.location,
        "remote_policy": application.job.remote_policy,
        "source_alert_id": application.source_alert_id,
        "status": application.status,
        "notes": application.notes,
        "next_action": application.next_action,
        "follow_up_at": application.follow_up_at.isoformat() if application.follow_up_at else None,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "artifacts": [serialize_application_artifact(artifact) for artifact in application.artifacts.all()],
        "interview_prep": serialize_interview_prep(application.interview_prep) if hasattr(application, "interview_prep") else None,
        "offer_support": serialize_offer_support(application.offer_support) if hasattr(application, "offer_support") else None,
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
    }


def serialize_application_artifact(artifact: ApplicationArtifact) -> dict:
    return {
        "id": artifact.id,
        "application_id": artifact.application_id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "content": artifact.content,
        "status": artifact.status,
        "metadata": artifact.metadata,
        "generated_by": artifact.generated_by,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
    }


def serialize_application_summary(application: Application) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "job_title": application.job.title,
        "company": application.job.company.name,
        "status": application.status,
        "next_action": application.next_action,
        "follow_up_at": application.follow_up_at.isoformat() if application.follow_up_at else None,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "artifacts": [serialize_application_artifact(artifact) for artifact in application.artifacts.all()],
        "interview_prep": serialize_interview_prep(application.interview_prep) if hasattr(application, "interview_prep") else None,
        "offer_support": serialize_offer_support(application.offer_support) if hasattr(application, "offer_support") else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
    }


def serialize_interview_prep(prep: InterviewPrep) -> dict:
    return {
        "id": prep.id,
        "application_id": prep.application_id,
        "stage": prep.stage,
        "checklist": prep.checklist,
        "focus_areas": prep.focus_areas,
        "question_bank": prep.question_bank,
        "story_bank": prep.story_bank,
        "gaps": prep.gaps,
        "notes": prep.notes,
        "generated_by": prep.generated_by,
        "created_at": prep.created_at.isoformat() if prep.created_at else None,
        "updated_at": prep.updated_at.isoformat() if prep.updated_at else None,
    }


def serialize_offer_support(support: OfferSupport) -> dict:
    return {
        "id": support.id,
        "application_id": support.application_id,
        "offer_stage": support.offer_stage,
        "base_salary_min": support.base_salary_min,
        "base_salary_max": support.base_salary_max,
        "equity_notes": support.equity_notes,
        "benefits_notes": support.benefits_notes,
        "manual_research": support.manual_research,
        "decision_criteria": support.decision_criteria,
        "negotiation_points": support.negotiation_points,
        "compensation_notes": support.compensation_notes,
        "risk_flags": support.risk_flags,
        "generated_by": support.generated_by,
        "created_at": support.created_at.isoformat() if support.created_at else None,
        "updated_at": support.updated_at.isoformat() if support.updated_at else None,
    }


def serialize_today_action(action: TodayAction) -> dict:
    job = action.job or (action.application.job if action.application_id else None)
    return {
        "id": action.id,
        "action_type": action.action_type,
        "status": action.status,
        "title": action.title,
        "message": action.message,
        "due_at": action.due_at.isoformat() if action.due_at else None,
        "job_id": job.id if job else None,
        "job_title": job.title if job else "",
        "company_id": job.company_id if job else None,
        "company_name": job.company.name if job else "",
        "apply_url": job.apply_url if job else "",
        "application_id": action.application_id,
        "source_alert_id": action.source_alert_id,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "completed_at": action.completed_at.isoformat() if action.completed_at else None,
    }


def serialize_today_action_summary(action: TodayAction) -> dict:
    return {
        "id": action.id,
        "action_type": action.action_type,
        "status": action.status,
        "title": action.title,
        "due_at": action.due_at.isoformat() if action.due_at else None,
        "application_id": action.application_id,
        "source_alert_id": action.source_alert_id,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


def serialize_profile(profile: CandidateProfile) -> dict:
    target_titles = profile.target_titles.all()
    claims = profile.claims.all()
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
        "last_generated_at": profile.last_generated_at.isoformat() if profile.last_generated_at else None,
        "target_titles": [serialize_target_title(target_title) for target_title in target_titles],
        "claims": [serialize_profile_claim(claim) for claim in claims],
        "search_strategy": serialize_search_strategy(profile.search_strategy) if hasattr(profile, "search_strategy") else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
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


def serialize_manual_url_item(item: ManualUrlInboxItem) -> dict:
    return {
        "id": item.id,
        "url": item.url,
        "item_type": item.item_type,
        "status": item.status,
        "title": item.title,
        "notes": item.notes,
        "inferred_company": item.inferred_company,
        "company_id": item.company_id,
        "company_name": item.company.name if item.company else "",
        "job_id": item.job_id,
        "job_title": item.job.title if item.job else "",
        "imported_at": item.imported_at.isoformat() if item.imported_at else None,
        "dismissed_at": item.dismissed_at.isoformat() if item.dismissed_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
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
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
    }


def serialize_agent_provider(provider: AgentProviderSetting) -> dict:
    return {
        "id": provider.id,
        "provider": provider.provider,
        "label": provider.label,
        "model_name": provider.model_name,
        "enabled": provider.enabled,
        "worker_only": provider.worker_only,
        "api_key_env_var": provider.api_key_env_var,
        "api_key_configured": bool(provider.api_key_env_var and os.environ.get(provider.api_key_env_var)),
        "default_tool_policy": provider.default_tool_policy,
        "consent_required": provider.consent_required,
        "daily_run_limit": provider.daily_run_limit,
        "monthly_budget_cents": provider.monthly_budget_cents,
        "estimated_cost_per_run_cents": provider.estimated_cost_per_run_cents,
        "notes": provider.notes,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
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
        "input_snapshot": safe_agent_snapshot(run.input_snapshot),
        "output_snapshot": run.output_snapshot,
        "result_summary": run.result_summary,
        "error": run.error,
        "user_safe_error": run.user_safe_error,
        "requested_at": run.requested_at.isoformat() if run.requested_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "steps": [serialize_agent_step(step) for step in run.steps.all()],
        "artifacts": [serialize_agent_artifact(artifact) for artifact in run.artifacts.all()],
        "decisions": [serialize_agent_decision(decision) for decision in run.decisions.all()],
        "permissions": [serialize_agent_permission(permission) for permission in run.permissions.all()],
        "runtime_invocations": [
            serialize_runtime_invocation(invocation) for invocation in run.runtime_invocations.all()
        ],
        "audit_logs": [serialize_agent_audit_log(log) for log in run.audit_logs.all()],
    }


def serialize_agent_run_summary(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "agent_type": run.agent_type,
        "status": run.status,
        "provider": run.provider,
        "model_name": run.model_name,
        "tool_policy": run.tool_policy,
        "prompt_version": run.prompt_version,
        "result_summary": run.result_summary,
        "user_safe_error": run.user_safe_error,
        "requested_at": run.requested_at.isoformat() if run.requested_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "artifact_count": run.artifacts.count(),
        "runtime_invocation_count": run.runtime_invocations.count(),
    }


def serialize_agent_step(step) -> dict:
    return {
        "id": step.id,
        "order": step.order,
        "name": step.name,
        "status": step.status,
        "message": step.message,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "finished_at": step.finished_at.isoformat() if step.finished_at else None,
        "created_at": step.created_at.isoformat() if step.created_at else None,
    }


def serialize_agent_artifact(artifact) -> dict:
    return {
        "id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "content": artifact.content,
        "metadata": artifact.metadata,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
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


def serialize_agent_permission(permission) -> dict:
    return {
        "id": permission.id,
        "policy_level": permission.policy_level,
        "status": permission.status,
        "reason": permission.reason,
        "created_at": permission.created_at.isoformat() if permission.created_at else None,
    }


def serialize_runtime_invocation(invocation) -> dict:
    return {
        "id": invocation.id,
        "provider": invocation.provider,
        "adapter": invocation.adapter,
        "model_name": invocation.model_name,
        "status": invocation.status,
        "input_snapshot": safe_agent_snapshot(invocation.input_snapshot),
        "output_snapshot": invocation.output_snapshot,
        "error": invocation.error,
        "token_count": invocation.token_count,
        "cost_estimate": float(invocation.cost_estimate),
        "started_at": invocation.started_at.isoformat() if invocation.started_at else None,
        "finished_at": invocation.finished_at.isoformat() if invocation.finished_at else None,
        "created_at": invocation.created_at.isoformat() if invocation.created_at else None,
    }


def serialize_agent_audit_log(log) -> dict:
    return {
        "id": log.id,
        "event_type": log.event_type,
        "message": log.message,
        "metadata": log.metadata,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def safe_agent_snapshot(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        return {}

    sanitized = dict(snapshot)
    profile = sanitized.get("profile")
    if isinstance(profile, dict):
        sanitized["profile"] = safe_agent_profile_snapshot(profile)

    context = sanitized.get("context")
    if isinstance(context, dict):
        context = dict(context)
        profile = context.get("profile")
        if isinstance(profile, dict):
            context["profile"] = safe_agent_profile_snapshot(profile)
        sanitized["context"] = context

    return sanitized


def safe_agent_profile_snapshot(profile: dict) -> dict:
    sanitized = dict(profile)
    for key, label in (("cv_markdown", "cv markdown"), ("profile_markdown", "profile markdown")):
        value = sanitized.get(key)
        if value:
            sanitized[key] = f"[redacted {label}, {len(str(value))} chars]"
    return sanitized


def serialize_job_base(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company.name,
        "company_id": job.company_id,
        "location": job.location,
        "description": job.description,
        "apply_url": job.apply_url,
        "source_url": job.source_url,
        "source_platform": job.source_platform,
        "external_id": job.external_id,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "tags": job.tags,
        "remote_policy": job.remote_policy,
        "first_seen_at": job.first_seen_at.isoformat(),
        "last_seen_at": job.last_seen_at.isoformat(),
    }


def serialize_job(job: Job, match: JobMatch | None = None) -> dict:
    match = match or refresh_job_match(job)
    return {**serialize_job_base(job), "match": serialize_job_match(match)}


def serialize_job_export(job: Job, match: JobMatch | None = None) -> dict:
    return {**serialize_job_base(job), "match": serialize_job_match(match) if match else None}
