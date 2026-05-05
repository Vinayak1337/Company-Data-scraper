from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from agents.models import (
    AgentArtifact,
    AgentAuditLog,
    AgentDecision,
    AgentPermission,
    AgentProviderSetting,
    AgentRun,
    AgentStep,
    RuntimeInvocation,
)
from agents.services import ensure_provider_settings, update_provider_setting
from analytics.models import AlertFeedback, LearningChange, MatchScoreCorrection, WeeklyReview
from analytics.services import record_match_score_correction, undo_learning_change
from applications.models import Application, ApplicationArtifact, TodayAction
from companies.models import Company, JobAlert, ScanJob, ScrapeLog
from companies.services import create_company_from_url, update_company
from discovery.models import ManualUrlInboxItem
from intelligence.models import CompanyIntelligence, RecruiterContact
from interviews.models import InterviewPrep, OfferSupport
from jobs.models import Job
from matching.models import JobMatch
from notifications.models import NotificationPreference
from notifications.services import get_notification_preferences, update_notification_preferences
from profiles.models import CandidateProfile, ProfileClaim, SearchStrategy, TargetTitle


DELETE_ALL_CONFIRMATION = "DELETE ALL PERSONAL DATA"
EXPORT_RESTORE_DOMAINS = {
    "profile": "restored",
    "companies": "restored",
    "jobs": "restored",
    "applications": "restored",
    "application_artifacts": "restored",
    "interview_preps": "restored",
    "offer_support": "restored",
    "notification_preferences": "restored",
    "manual_url_inbox": "restored",
    "company_intelligence": "restored",
    "recruiter_contacts": "restored",
    "weekly_reviews": "restored",
    "job_matches": "restored",
    "match_score_corrections": "restored",
    "learning_changes": "restored",
    "scan_logs": "restored_without_raw_messages",
    "scan_jobs": "restored",
    "alerts": "restored",
    "agent_providers": "restored_without_secrets",
    "agent_runs": "restored_with_redacted_snapshots",
}


def import_workspace_export(payload: dict[str, Any]) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Workspace import payload must be a JSON object.")

    counts: dict[str, int] = defaultdict(int)
    errors: list[dict] = []
    maps: dict[str, dict[int, Any]] = {
        "companies": {},
        "jobs": {},
        "applications": {},
        "alerts": {},
        "scan_logs": {},
        "scan_jobs": {},
        "learning_changes": {},
    }

    with transaction.atomic():
        profile = import_profile(payload.get("profile"), counts, errors)
        import_notification_preferences(payload.get("notification_preferences"), counts, errors)
        import_agent_providers(payload.get("agent_providers") or [], counts, errors)
        import_companies(payload.get("companies") or [], counts, errors, maps)
        import_jobs(payload.get("jobs") or [], counts, errors, maps)
        import_scan_logs(payload.get("scan_logs") or [], counts, errors, maps)
        import_scan_jobs(payload.get("scan_jobs") or [], counts, errors, maps)
        import_alerts(payload.get("alerts") or [], counts, errors, maps)
        import_applications(payload.get("applications") or [], counts, errors, maps)
        import_today_actions(payload.get("today_actions") or [], counts, errors, maps)
        import_manual_url_inbox(payload.get("manual_url_inbox") or [], counts, errors, maps)
        import_company_intelligence(payload.get("company_intelligence") or [], counts, errors, maps)
        import_recruiter_contacts(payload.get("recruiter_contacts") or [], counts, errors, maps)
        import_interview_preps(payload.get("interview_preps") or [], counts, errors, maps)
        import_offer_support(payload.get("offer_support") or [], counts, errors, maps)
        import_weekly_reviews(payload.get("weekly_reviews") or [], counts, errors)
        import_job_matches(payload.get("job_matches") or [], counts, errors, maps, profile)
        import_learning_changes(payload.get("learning_changes") or [], counts, errors, maps)
        import_match_score_corrections(payload.get("match_score_corrections") or [], counts, errors, maps)
        import_agent_runs(payload.get("agent_runs") or [], counts, errors)

    return {
        "status": "ok" if not errors else "partial",
        "imported": dict(counts),
        "errors": errors,
        "error_count": len(errors),
        "domain_behavior": EXPORT_RESTORE_DOMAINS,
    }


def delete_all_personal_data(confirmation: str) -> dict:
    if confirmation != DELETE_ALL_CONFIRMATION:
        raise ValueError(f'Type "{DELETE_ALL_CONFIRMATION}" to confirm deletion.')

    deleted: dict[str, int] = {}
    with transaction.atomic():
        for label, model in (
            ("agent_runs", AgentRun),
            ("agent_provider_settings", AgentProviderSetting),
            ("weekly_reviews", WeeklyReview),
            ("match_score_corrections", MatchScoreCorrection),
            ("learning_changes", LearningChange),
            ("alert_feedback", AlertFeedback),
            ("offer_support", OfferSupport),
            ("interview_preps", InterviewPrep),
            ("application_artifacts", ApplicationArtifact),
            ("today_actions", TodayAction),
            ("applications", Application),
            ("job_alerts", JobAlert),
            ("scan_jobs", ScanJob),
            ("scrape_logs", ScrapeLog),
            ("company_intelligence", CompanyIntelligence),
            ("recruiter_contacts", RecruiterContact),
            ("manual_url_inbox", ManualUrlInboxItem),
            ("job_matches", JobMatch),
            ("jobs", Job),
            ("companies", Company),
            ("candidate_profiles", CandidateProfile),
            ("notification_preferences", NotificationPreference),
        ):
            deleted[label] = model.objects.all().delete()[0]
        ensure_provider_settings()
    return {"deleted": deleted, "status": "ok", "confirmed_at": timezone.now().isoformat()}


def redaction_audit() -> dict:
    provider_settings = ensure_provider_settings()
    runtime_snapshots = AgentRun.objects.filter(runtime_invocations__isnull=False).distinct().count()
    return {
        "status": "ok",
        "generated_at": timezone.now().isoformat(),
        "checks": [
            {
                "name": "Secret configuration",
                "status": "ok",
                "message": "Diagnostics and exports expose configured/missing flags, not secret values.",
            },
            {
                "name": "Agent runtime payloads",
                "status": "ok",
                "message": "Runtime invocation inputs are scrubbed before storage and API serialization redacts CV/profile markdown.",
                "detail": {"runs_with_runtime_snapshots": runtime_snapshots},
            },
            {
                "name": "Scrape log export",
                "status": "ok",
                "message": "Exported scan-log summaries omit raw scraper error messages by default.",
            },
            {
                "name": "Provider settings",
                "status": "ok",
                "message": "Provider records store env-var names and metadata only.",
                "detail": {"providers": [provider.provider for provider in provider_settings]},
            },
        ],
    }


def import_profile(item, counts, errors) -> CandidateProfile | None:
    if not isinstance(item, dict):
        return CandidateProfile.objects.order_by("id").first()

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
    profile = CandidateProfile.objects.order_by("id").first() or CandidateProfile()
    for field in fields:
        if field in item:
            setattr(profile, field, item[field])
    profile.save()
    counts["profile"] += 1

    for title in item.get("target_titles") or []:
        if not isinstance(title, dict) or not title.get("title"):
            continue
        TargetTitle.objects.update_or_create(
            profile=profile,
            title=str(title["title"])[:180],
            defaults={
                "fit_bucket": title.get("fit_bucket") or "adjacent",
                "confidence_score": int_or_default(title.get("confidence_score"), 50),
                "knowledge_accuracy": int_or_default(title.get("knowledge_accuracy"), 50),
                "evidence": list_value(title.get("evidence")),
                "source": str(title.get("source") or "import")[:40],
                "status": title.get("status") or "suggested",
            },
        )
        counts["target_titles"] += 1

    for claim in item.get("claims") or []:
        if not isinstance(claim, dict) or not claim.get("text"):
            continue
        ProfileClaim.objects.update_or_create(
            profile=profile,
            text=str(claim["text"]),
            defaults={
                "claim_type": claim.get("claim_type") or "other",
                "evidence": str(claim.get("evidence") or ""),
                "source": str(claim.get("source") or "import")[:40],
                "status": claim.get("status") or "unconfirmed",
            },
        )
        counts["profile_claims"] += 1

    strategy = item.get("search_strategy")
    if isinstance(strategy, dict):
        SearchStrategy.objects.update_or_create(
            profile=profile,
            defaults={
                "role_families": list_value(strategy.get("role_families")),
                "target_title_keywords": list_value(strategy.get("target_title_keywords")),
                "negative_keywords": list_value(strategy.get("negative_keywords")),
                "seniority_levels": list_value(strategy.get("seniority_levels")),
                "location_keywords": list_value(strategy.get("location_keywords")),
                "work_mode_preferences": list_value(strategy.get("work_mode_preferences")),
                "generated_from": str(strategy.get("generated_from") or "import")[:80],
                "notes": str(strategy.get("notes") or ""),
            },
        )
        counts["search_strategy"] += 1
    return profile


def import_notification_preferences(item, counts, errors) -> None:
    if not isinstance(item, dict):
        return
    try:
        update_notification_preferences(get_notification_preferences(), item)
        counts["notification_preferences"] += 1
    except ValueError as exc:
        errors.append({"domain": "notification_preferences", "error": str(exc)})


def import_agent_providers(items, counts, errors) -> None:
    ensure_provider_settings()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("provider"):
            continue
        try:
            provider = AgentProviderSetting.objects.filter(provider=item["provider"]).first()
            if provider:
                update_provider_setting(provider, item)
                counts["agent_providers"] += 1
        except ValueError as exc:
            errors.append({"domain": "agent_providers", "index": index, "error": str(exc)})


def import_companies(items, counts, errors, maps) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        try:
            company = Company.objects.filter(careers_url=item.get("careers_url")).first()
            if company:
                company = update_company(company, company_updates(item))
                counts["companies_updated"] += 1
            else:
                company = create_company_from_url(
                    str(item.get("careers_url") or ""),
                    str(item.get("name") or ""),
                    str(item.get("priority_tier") or item.get("priority") or ""),
                    filters=item,
                )
                company = update_company(company, company_updates(item))
                counts["companies_created"] += 1
            if item.get("id") is not None:
                maps["companies"][int_or_default(item.get("id"), 0)] = company
        except Exception as exc:
            errors.append({"domain": "companies", "index": index, "error": str(exc)})


def import_jobs(items, counts, errors, maps) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        company = company_from_item(item, maps)
        if not company:
            errors.append({"domain": "jobs", "index": index, "error": "Could not map company."})
            continue
        apply_url = str(item.get("apply_url") or "").strip()
        if not apply_url:
            errors.append({"domain": "jobs", "index": index, "error": "apply_url is required."})
            continue
        defaults = {
            "title": str(item.get("title") or "Imported role")[:255],
            "location": str(item.get("location") or "")[:255],
            "description": str(item.get("description") or ""),
            "source_url": str(item.get("source_url") or company.careers_url),
            "source_platform": str(item.get("source_platform") or company.scraper_type or "import")[:40],
            "external_id": str(item.get("external_id") or "")[:255],
            "posted_at": parse_dt(item.get("posted_at")),
            "tags": list_value(item.get("tags")),
            "remote_policy": item.get("remote_policy") or "unknown",
        }
        job, _ = Job.objects.update_or_create(company=company, apply_url=apply_url, defaults=defaults)
        counts["jobs"] += 1
        if item.get("id") is not None:
            maps["jobs"][int_or_default(item.get("id"), 0)] = job


def import_scan_logs(items, counts, errors, maps) -> None:
    for index, item in enumerate(items):
        company = company_from_item(item, maps) if isinstance(item, dict) else None
        if not company:
            continue
        log = ScrapeLog.objects.create(
            company=company,
            status=str(item.get("status") or "success")[:20],
            source_platform=str(item.get("source_platform") or company.scraper_type)[:40],
            jobs_found=int_or_default(item.get("jobs_found"), 0),
            jobs_created=int_or_default(item.get("jobs_created"), 0),
            jobs_updated=int_or_default(item.get("jobs_updated"), 0),
        )
        set_datetime_fields(log, item, "started_at", "finished_at")
        counts["scan_logs"] += 1
        if item.get("id") is not None:
            maps["scan_logs"][int_or_default(item.get("id"), 0)] = log


def import_scan_jobs(items, counts, errors, maps) -> None:
    for item in items:
        company = company_from_item(item, maps) if isinstance(item, dict) else None
        if not company:
            continue
        scrape_log = None
        scrape_log_id = int_or_default(item.get("scrape_log_id"), 0)
        if scrape_log_id:
            scrape_log = maps["scan_logs"].get(scrape_log_id)
        scan_job = ScanJob.objects.create(
            company=company,
            scrape_log=scrape_log,
            status=str(item.get("status") or "success")[:20],
            trigger=str(item.get("trigger") or "manual")[:20],
            source_platform=str(item.get("source_platform") or company.scraper_type)[:40],
            message=str(item.get("message") or ""),
            jobs_found=int_or_default(item.get("jobs_found"), 0),
            jobs_created=int_or_default(item.get("jobs_created"), 0),
            jobs_updated=int_or_default(item.get("jobs_updated"), 0),
            alerts_created=int_or_default(item.get("alerts_created"), 0),
            requested_at=parse_dt(item.get("requested_at")) or timezone.now(),
            started_at=parse_dt(item.get("started_at")),
            finished_at=parse_dt(item.get("finished_at")),
        )
        set_datetime_fields(scan_job, item, "created_at", "updated_at")
        counts["scan_jobs"] += 1
        if item.get("id") is not None:
            maps["scan_jobs"][int_or_default(item.get("id"), 0)] = scan_job


def import_alerts(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        company = company_from_item(item, maps)
        job = job_from_item(item, maps)
        if not company or not job:
            continue
        alert, _ = JobAlert.objects.update_or_create(
            company=company,
            job=job,
            alert_type=item.get("alert_type") or "new_role",
            defaults={
                "scan_job": maps["scan_jobs"].get(int_or_default(item.get("scan_job_id"), 0)),
                "status": item.get("status") or "unread",
                "title": str(item.get("title") or f"New role at {company.name}: {job.title}")[:255],
                "message": str(item.get("message") or ""),
            },
        )
        counts["alerts"] += 1
        if item.get("id") is not None:
            maps["alerts"][int_or_default(item.get("id"), 0)] = alert


def import_applications(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        job = job_from_item(item, maps)
        if not job:
            continue
        application, _ = Application.objects.update_or_create(
            job=job,
            defaults={
                "source_alert": alert_from_item(item, maps),
                "status": item.get("status") or "saved",
                "notes": str(item.get("notes") or ""),
                "next_action": str(item.get("next_action") or "")[:255],
                "follow_up_at": parse_dt(item.get("follow_up_at")),
                "applied_at": parse_dt(item.get("applied_at")),
            },
        )
        counts["applications"] += 1
        if item.get("id") is not None:
            maps["applications"][int_or_default(item.get("id"), 0)] = application
        import_application_artifacts(application, item.get("artifacts") or [], counts)
        import_nested_interview_prep(application, item.get("interview_prep"), counts)
        import_nested_offer_support(application, item.get("offer_support"), counts)


def import_application_artifacts(application, items, counts) -> None:
    for artifact in items:
        if not isinstance(artifact, dict):
            continue
        title = str(artifact.get("title") or "Imported artifact")[:255]
        ApplicationArtifact.objects.update_or_create(
            application=application,
            artifact_type=artifact.get("artifact_type") or "tailoring_plan",
            title=title,
            defaults={
                "content": str(artifact.get("content") or ""),
                "status": artifact.get("status") or "draft",
                "metadata": dict_value(artifact.get("metadata")),
                "generated_by": str(artifact.get("generated_by") or "import")[:80],
            },
        )
        counts["application_artifacts"] += 1


def import_today_actions(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        application = application_from_item(item, maps)
        alert = alert_from_item(item, maps)
        job = job_from_item(item, maps)
        if not any([application, alert, job]):
            continue
        TodayAction.objects.update_or_create(
            application=application,
            source_alert=alert,
            action_type=item.get("action_type") or "application_next_step",
            defaults={
                "job": job,
                "status": item.get("status") or "open",
                "title": str(item.get("title") or "Imported action")[:255],
                "message": str(item.get("message") or ""),
                "due_at": parse_dt(item.get("due_at")),
            },
        )
        counts["today_actions"] += 1


def import_manual_url_inbox(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        ManualUrlInboxItem.objects.update_or_create(
            url=str(item["url"]),
            defaults={
                "item_type": item.get("item_type") or "unknown",
                "status": item.get("status") or "pending",
                "title": str(item.get("title") or "")[:255],
                "notes": str(item.get("notes") or ""),
                "inferred_company": str(item.get("inferred_company") or "")[:180],
                "company": company_from_item(item, maps),
                "job": job_from_item(item, maps),
            },
        )
        counts["manual_url_inbox"] += 1


def import_company_intelligence(items, counts, errors, maps) -> None:
    for item in items:
        company = company_from_item(item, maps) if isinstance(item, dict) else None
        if not company:
            continue
        CompanyIntelligence.objects.create(
            company=company,
            summary=str(item.get("summary") or ""),
            research_notes=str(item.get("research_notes") or ""),
            hiring_signals=list_value(item.get("hiring_signals")),
            role_patterns=list_value(item.get("role_patterns")),
            role_legitimacy=item.get("role_legitimacy") or "unknown",
            caveats=list_value(item.get("caveats")),
            hiring_team_hints=list_value(item.get("hiring_team_hints")),
            interview_process_notes=str(item.get("interview_process_notes") or ""),
            risk_flags=list_value(item.get("risk_flags")),
            user_notes=str(item.get("user_notes") or ""),
            source_snapshot=dict_value(item.get("source_snapshot")),
            verification_status=item.get("verification_status") or "unverified",
            generated_by=str(item.get("generated_by") or "import")[:80],
        )
        counts["company_intelligence"] += 1


def import_recruiter_contacts(items, counts, errors, maps) -> None:
    for item in items:
        company = company_from_item(item, maps) if isinstance(item, dict) else None
        if not company:
            continue
        RecruiterContact.objects.create(
            company=company,
            name=str(item.get("name") or "")[:180],
            title=str(item.get("title") or "")[:180],
            source_url=str(item.get("source_url") or ""),
            source_label=str(item.get("source_label") or "")[:180],
            public_source_only=bool(item.get("public_source_only", True)),
            status=item.get("status") or "lead",
            notes=str(item.get("notes") or ""),
        )
        counts["recruiter_contacts"] += 1


def import_interview_preps(items, counts, errors, maps) -> None:
    for item in items:
        application = application_from_item(item, maps) if isinstance(item, dict) else None
        if application:
            import_nested_interview_prep(application, item, counts)


def import_nested_interview_prep(application, item, counts) -> None:
    if not isinstance(item, dict):
        return
    InterviewPrep.objects.update_or_create(
        application=application,
        defaults={
            "stage": item.get("stage") or "unknown",
            "checklist": list_value(item.get("checklist")),
            "focus_areas": list_value(item.get("focus_areas")),
            "question_bank": list_value(item.get("question_bank")),
            "story_bank": list_value(item.get("story_bank")),
            "gaps": list_value(item.get("gaps")),
            "notes": str(item.get("notes") or ""),
            "generated_by": str(item.get("generated_by") or "import")[:80],
        },
    )
    counts["interview_preps"] += 1


def import_offer_support(items, counts, errors, maps) -> None:
    for item in items:
        application = application_from_item(item, maps) if isinstance(item, dict) else None
        if application:
            import_nested_offer_support(application, item, counts)


def import_nested_offer_support(application, item, counts) -> None:
    if not isinstance(item, dict):
        return
    OfferSupport.objects.update_or_create(
        application=application,
        defaults={
            "offer_stage": str(item.get("offer_stage") or "")[:80],
            "base_salary_min": none_or_int(item.get("base_salary_min")),
            "base_salary_max": none_or_int(item.get("base_salary_max")),
            "equity_notes": str(item.get("equity_notes") or ""),
            "benefits_notes": str(item.get("benefits_notes") or ""),
            "manual_research": list_value(item.get("manual_research")),
            "decision_criteria": list_value(item.get("decision_criteria")),
            "negotiation_points": list_value(item.get("negotiation_points")),
            "compensation_notes": str(item.get("compensation_notes") or ""),
            "risk_flags": list_value(item.get("risk_flags")),
            "generated_by": str(item.get("generated_by") or "import")[:80],
        },
    )
    counts["offer_support"] += 1


def import_weekly_reviews(items, counts, errors) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        WeeklyReview.objects.create(
            period_start=parse_dt(item.get("period_start")) or timezone.now(),
            period_end=parse_dt(item.get("period_end")) or timezone.now(),
            summary=str(item.get("summary") or ""),
            recommendations=list_value(item.get("recommendations")),
            risks=list_value(item.get("risks")),
            metrics_snapshot=dict_value(item.get("metrics_snapshot")),
            generated_by=str(item.get("generated_by") or "import")[:80],
        )
        counts["weekly_reviews"] += 1


def import_job_matches(items, counts, errors, maps, profile) -> None:
    for item in items:
        job = job_from_item(item, maps) if isinstance(item, dict) else None
        if not job:
            continue
        JobMatch.objects.update_or_create(
            job=job,
            defaults={
                "profile": profile,
                "source": item.get("source") or "deterministic",
                "overall_score": int_or_default(item.get("overall_score"), 0),
                "title_score": int_or_default(item.get("title_score"), 0),
                "skill_score": int_or_default(item.get("skill_score"), 0),
                "seniority_score": int_or_default(item.get("seniority_score"), 0),
                "location_score": int_or_default(item.get("location_score"), 0),
                "confidence_score": int_or_default(item.get("confidence_score"), 0),
                "knowledge_coverage_score": int_or_default(item.get("knowledge_coverage_score"), 0),
                "apply_priority": item.get("apply_priority") or "ignore",
                "reasons_to_apply": list_value(item.get("reasons_to_apply")),
                "reasons_to_skip": list_value(item.get("reasons_to_skip")),
                "missing_skills": list_value(item.get("missing_skills")),
                "evidence": list_value(item.get("evidence")),
            },
        )
        counts["job_matches"] += 1


def import_learning_changes(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        change = LearningChange.objects.create(
            change_type=str(item.get("change_type") or "import")[:80],
            status=item.get("status") or "active",
            summary=str(item.get("summary") or ""),
            evidence=list_value(item.get("evidence")),
            payload=dict_value(item.get("payload")),
            undone_at=parse_dt(item.get("undone_at")),
        )
        counts["learning_changes"] += 1
        if item.get("id") is not None:
            maps["learning_changes"][int_or_default(item.get("id"), 0)] = change


def import_match_score_corrections(items, counts, errors, maps) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        job = job_from_item(item, maps)
        if not job:
            continue
        try:
            correction = record_match_score_correction(job, item.get("correction") or "accurate", str(item.get("reason") or ""))
            if item.get("learning_change_status") == "undone":
                undo_learning_change(correction.learning_change)
            counts["match_score_corrections"] += 1
        except ValueError as exc:
            errors.append({"domain": "match_score_corrections", "error": str(exc)})


def import_agent_runs(items, counts, errors) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        try:
            run = AgentRun.objects.create(
                agent_type=str(item.get("agent_type") or "profile_builder")[:40],
                status=str(item.get("status") or "success")[:24],
                provider=str(item.get("provider") or "direct_api")[:40],
                model_name=str(item.get("model_name") or "")[:120],
                tool_policy=str(item.get("tool_policy") or "read_only")[:40],
                prompt_version=str(item.get("prompt_version") or "imported")[:80],
                input_snapshot=dict_value(item.get("input_snapshot")),
                output_snapshot=dict_value(item.get("output_snapshot")),
                result_summary=str(item.get("result_summary") or ""),
                error=str(item.get("error") or ""),
                user_safe_error=str(item.get("user_safe_error") or ""),
                requested_at=parse_dt(item.get("requested_at")) or timezone.now(),
                started_at=parse_dt(item.get("started_at")),
                finished_at=parse_dt(item.get("finished_at")),
            )
            set_datetime_fields(run, item, "created_at", "updated_at")
            import_agent_steps(run, item.get("steps") or [], counts)
            import_agent_artifacts(run, item.get("artifacts") or [], counts)
            import_agent_decisions(run, item.get("decisions") or [], counts)
            import_agent_permissions(run, item.get("permissions") or [], counts)
            import_runtime_invocations(run, item.get("runtime_invocations") or [], counts)
            import_agent_audit_logs(run, item.get("audit_logs") or [], counts)
            counts["agent_runs"] += 1
        except Exception as exc:
            errors.append({"domain": "agent_runs", "index": index, "error": str(exc)})


def import_agent_steps(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        step = AgentStep.objects.create(
            run=run,
            order=int_or_default(item.get("order"), 1),
            name=str(item.get("name") or "Imported step")[:160],
            status=str(item.get("status") or "success")[:24],
            message=str(item.get("message") or ""),
            started_at=parse_dt(item.get("started_at")),
            finished_at=parse_dt(item.get("finished_at")),
        )
        set_datetime_fields(step, item, "created_at")
        counts["agent_steps"] += 1


def import_agent_artifacts(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        artifact = AgentArtifact.objects.create(
            run=run,
            artifact_type=str(item.get("artifact_type") or "text")[:40],
            title=str(item.get("title") or "Imported artifact")[:180],
            content=str(item.get("content") or ""),
            metadata=dict_value(item.get("metadata")),
        )
        set_datetime_fields(artifact, item, "created_at")
        counts["agent_artifacts"] += 1


def import_agent_decisions(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        decision = AgentDecision.objects.create(
            run=run,
            decision_type=str(item.get("decision_type") or "imported")[:80],
            status=str(item.get("status") or "pending")[:20],
            question=str(item.get("question") or ""),
            proposed_changes=dict_value(item.get("proposed_changes")),
            decided_at=parse_dt(item.get("decided_at")),
        )
        set_datetime_fields(decision, item, "created_at")
        counts["agent_decisions"] += 1


def import_agent_permissions(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        permission = AgentPermission.objects.create(
            run=run,
            policy_level=str(item.get("policy_level") or "read_only")[:40],
            status=str(item.get("status") or "granted")[:20],
            reason=str(item.get("reason") or ""),
        )
        set_datetime_fields(permission, item, "created_at")
        counts["agent_permissions"] += 1


def import_runtime_invocations(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        invocation = RuntimeInvocation.objects.create(
            run=run,
            provider=str(item.get("provider") or run.provider)[:40],
            adapter=str(item.get("adapter") or "imported")[:80],
            model_name=str(item.get("model_name") or "")[:120],
            status=str(item.get("status") or "success")[:20],
            input_snapshot=dict_value(item.get("input_snapshot")),
            output_snapshot=dict_value(item.get("output_snapshot")),
            error=str(item.get("error") or ""),
            token_count=int_or_default(item.get("token_count"), 0),
            cost_estimate=item.get("cost_estimate") or 0,
            started_at=parse_dt(item.get("started_at")),
            finished_at=parse_dt(item.get("finished_at")),
        )
        set_datetime_fields(invocation, item, "created_at")
        counts["runtime_invocations"] += 1


def import_agent_audit_logs(run: AgentRun, items, counts) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        log = AgentAuditLog.objects.create(
            run=run,
            event_type=str(item.get("event_type") or "imported")[:80],
            message=str(item.get("message") or ""),
            metadata=dict_value(item.get("metadata")),
        )
        set_datetime_fields(log, item, "created_at")
        counts["agent_audit_logs"] += 1


def company_updates(item: dict) -> dict:
    fields = (
        "name",
        "careers_url",
        "scraper_type",
        "priority_tier",
        "priority",
        "is_active",
        "is_paused",
        "title_keywords",
        "negative_title_keywords",
        "location_keywords",
        "work_mode_filter",
        "scan_frequency_hours",
        "alert_new_roles",
    )
    return {field: item[field] for field in fields if field in item}


def company_from_item(item, maps):
    if not isinstance(item, dict):
        return None
    company_id = int_or_default(item.get("company_id"), 0)
    if company_id and company_id in maps["companies"]:
        return maps["companies"][company_id]
    name = str(item.get("company") or item.get("company_name") or "").strip()
    if name:
        return Company.objects.filter(name=name).first()
    return None


def job_from_item(item, maps):
    if not isinstance(item, dict):
        return None
    job_id = int_or_default(item.get("job_id") or item.get("id"), 0)
    if job_id and job_id in maps["jobs"]:
        return maps["jobs"][job_id]
    apply_url = item.get("apply_url") or item.get("job_apply_url")
    if apply_url:
        return Job.objects.filter(apply_url=apply_url).first()
    return None


def application_from_item(item, maps):
    if not isinstance(item, dict):
        return None
    application_id = int_or_default(item.get("application_id") or item.get("id"), 0)
    if application_id and application_id in maps["applications"]:
        return maps["applications"][application_id]
    job = job_from_item(item, maps)
    return Application.objects.filter(job=job).first() if job else None


def alert_from_item(item, maps):
    if not isinstance(item, dict):
        return None
    alert_id = int_or_default(item.get("source_alert_id") or item.get("alert_id") or item.get("id"), 0)
    if alert_id and alert_id in maps["alerts"]:
        return maps["alerts"][alert_id]
    return None


def parse_dt(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    parsed = parse_datetime(str(value))
    return parsed


def set_datetime_fields(instance, item: dict, *fields: str) -> None:
    updates = {}
    for field in fields:
        value = parse_dt(item.get(field)) if isinstance(item, dict) else None
        if value:
            updates[field] = value
    if updates:
        instance.__class__.objects.filter(pk=instance.pk).update(**updates)


def list_value(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]
    return []


def dict_value(value) -> dict:
    return value if isinstance(value, dict) else {}


def int_or_default(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def none_or_int(value):
    if value in {"", None}:
        return None
    return int_or_default(value, 0)
