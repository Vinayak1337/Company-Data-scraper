from django.utils import timezone
from django.utils.dateparse import parse_datetime

from applications.models import Application, ApplicationArtifact, TodayAction
from companies.models import JobAlert
from companies.services import dismiss_alert, mark_alert_read
from jobs.models import Job
from matching.services import refresh_job_match, serialize_job_match
from profiles.services import get_profile


ACTIVE_APPLICATION_STATUSES = {"saved", "applying", "applied", "interviewing"}
APPLICATION_STATUSES = {choice[0] for choice in Application.STATUS_CHOICES}
ARTIFACT_STATUSES = {choice[0] for choice in ApplicationArtifact.STATUS_CHOICES}
ARTIFACT_TYPES = {choice[0] for choice in ApplicationArtifact.ARTIFACT_TYPE_CHOICES}


def create_or_update_application(job: Job, updates: dict | None = None, source_alert: JobAlert | None = None) -> Application:
    updates = updates or {}
    application, _ = Application.objects.get_or_create(job=job)

    update_fields = []
    if source_alert and application.source_alert_id != source_alert.id:
        application.source_alert = source_alert
        update_fields.append("source_alert")

    if "status" in updates:
        status = normalize_application_status(updates.get("status"))
        if application.status != status:
            application.status = status
            update_fields.append("status")
        if status == "applied" and not application.applied_at:
            application.applied_at = timezone.now()
            update_fields.append("applied_at")

    for field in ("notes", "next_action"):
        if field in updates:
            value = str(updates.get(field) or "").strip()
            if getattr(application, field) != value:
                setattr(application, field, value)
                update_fields.append(field)

    if "follow_up_at" in updates:
        follow_up_at = parse_optional_datetime(updates.get("follow_up_at"))
        if application.follow_up_at != follow_up_at:
            application.follow_up_at = follow_up_at
            update_fields.append("follow_up_at")

    if update_fields:
        application.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])

    sync_today_actions_for_application(application)
    return application


def save_alert_as_application(alert: JobAlert, updates: dict | None = None) -> Application:
    payload = {"status": "saved", "next_action": "Review and decide whether to apply"}
    payload.update(updates or {})
    application = create_or_update_application(alert.job, payload, source_alert=alert)
    if alert.status == "unread":
        mark_alert_read(alert)
    complete_alert_review_action(alert)
    return application


def skip_alert(alert: JobAlert, reason: str = "") -> Application:
    application = create_or_update_application(
        alert.job,
        {
            "status": "skipped",
            "notes": reason or "Skipped from Today.",
            "next_action": "",
            "follow_up_at": None,
        },
        source_alert=alert,
    )
    dismiss_alert(alert)
    complete_alert_review_action(alert)
    dismiss_application_actions(application)
    return application


def update_application(application: Application, updates: dict) -> Application:
    return create_or_update_application(application.job, updates, source_alert=application.source_alert)


def create_application_artifact(application: Application, updates: dict) -> ApplicationArtifact:
    artifact_type = normalize_artifact_type(updates.get("artifact_type"))
    title = str(updates.get("title") or artifact_type.replace("_", " ").title()).strip()[:255]
    content = str(updates.get("content") or "").strip()
    if not content:
        raise ValueError("content is required")
    return ApplicationArtifact.objects.create(
        application=application,
        artifact_type=artifact_type,
        title=title,
        content=content[:50_000],
        status=normalize_artifact_status(updates.get("status") or "draft"),
        metadata=updates.get("metadata") if isinstance(updates.get("metadata"), dict) else {},
        generated_by=str(updates.get("generated_by") or "manual").strip()[:80],
    )


def set_application_artifact_status(artifact: ApplicationArtifact, status: str) -> ApplicationArtifact:
    artifact.status = normalize_artifact_status(status)
    artifact.save(update_fields=["status", "updated_at"])
    return artifact


def generate_tailoring_artifacts(application: Application) -> list[ApplicationArtifact]:
    profile = get_profile()
    match = refresh_job_match(application.job, profile=profile)
    match_payload = serialize_job_match(match)
    context = {
        "profile_name": profile.full_name or "Candidate",
        "job_title": application.job.title,
        "company": application.job.company.name,
        "location": application.job.location,
        "apply_priority": match.apply_priority,
        "overall_score": match.overall_score,
        "confidence_score": match.confidence_score,
        "matched_skills": matched_skill_values(match_payload),
        "missing_skills": match_payload["missing_skills"][:8],
        "reasons_to_apply": match_payload["reasons_to_apply"][:6],
        "reasons_to_check": match_payload["reasons_to_skip"][:6],
        "profile_skills": profile.skills[:20],
        "proof_points": [item.get("text", "") for item in profile.proof_points[:8] if isinstance(item, dict)],
    }
    specs = [
        ("tailoring_plan", "Tailoring Plan", build_tailoring_plan(context)),
        ("cv_notes", "CV Notes", build_cv_notes(context)),
        ("cover_note", "Cover Note Draft", build_cover_note(context)),
        ("recruiter_message", "Recruiter Message Draft", build_recruiter_message(context)),
        ("answer_bank", "Answer Bank Seeds", build_answer_bank(context)),
        ("interview_seed", "Interview Prep Seeds", build_interview_seed(context)),
    ]
    artifacts = []
    for artifact_type, title, content in specs:
        artifact, _ = ApplicationArtifact.objects.update_or_create(
            application=application,
            artifact_type=artifact_type,
            status="draft",
            defaults={
                "title": title,
                "content": content,
                "metadata": {"source": "deterministic_match", "match_id": match.id},
                "generated_by": "deterministic",
            },
        )
        artifacts.append(artifact)
    return artifacts


def sync_today_actions() -> None:
    for alert in JobAlert.objects.select_related("company", "job").filter(status="unread"):
        TodayAction.objects.get_or_create(
            source_alert=alert,
            action_type="review_new_role",
            defaults={
                "job": alert.job,
                "title": f"Review new role: {alert.job.title}",
                "message": f"{alert.company.name} posted a matching role.",
                "due_at": alert.created_at,
            },
        )

    for application in Application.objects.select_related("job", "job__company").filter(
        status__in=ACTIVE_APPLICATION_STATUSES,
        follow_up_at__lte=timezone.now(),
    ):
        sync_today_actions_for_application(application)


def sync_today_actions_for_application(application: Application) -> None:
    if application.status not in ACTIVE_APPLICATION_STATUSES or not application.follow_up_at:
        dismiss_application_actions(application)
        return

    if application.follow_up_at > timezone.now():
        return

    TodayAction.objects.get_or_create(
        application=application,
        action_type="follow_up",
        defaults={
            "job": application.job,
            "title": f"Follow up: {application.job.title}",
            "message": application.next_action or f"Follow up with {application.job.company.name}.",
            "due_at": application.follow_up_at,
        },
    )


def complete_alert_review_action(alert: JobAlert) -> None:
    TodayAction.objects.filter(source_alert=alert, action_type="review_new_role", status="open").update(
        status="done",
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )


def dismiss_application_actions(application: Application) -> None:
    TodayAction.objects.filter(application=application, status="open").update(
        status="dismissed",
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )


def mark_today_action_done(action: TodayAction) -> TodayAction:
    action.mark_done()
    return action


def dismiss_today_action(action: TodayAction) -> TodayAction:
    action.dismiss()
    return action


def normalize_artifact_type(value) -> str:
    artifact_type = str(value or "").strip().lower()
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"artifact_type must be one of: {', '.join(sorted(ARTIFACT_TYPES))}")
    return artifact_type


def normalize_artifact_status(value) -> str:
    status = str(value or "draft").strip().lower()
    if status not in ARTIFACT_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(ARTIFACT_STATUSES))}")
    return status


def normalize_application_status(value) -> str:
    status = str(value or "saved").strip().lower()
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(APPLICATION_STATUSES))}")
    return status


def parse_optional_datetime(value):
    if value in {None, ""}:
        return None
    if hasattr(value, "isoformat"):
        return value
    parsed = parse_datetime(str(value))
    if parsed is None:
        raise ValueError("follow_up_at must be an ISO datetime")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def matched_skill_values(match_payload: dict) -> list[str]:
    values = []
    for evidence in match_payload.get("evidence", []):
        if evidence.get("kind") == "skills":
            values.extend(evidence.get("values", []))
    return values[:12]


def build_tailoring_plan(context: dict) -> str:
    lines = [
        f"# Tailoring Plan: {context['job_title']} at {context['company']}",
        "",
        f"- Match score: {context['overall_score']}/100",
        f"- Confidence: {context['confidence_score']}/100",
        f"- Apply priority: {context['apply_priority']}",
        "",
        "## Emphasize",
    ]
    lines.extend(f"- {item}" for item in context["reasons_to_apply"] or ["Relevant profile evidence is limited."])
    lines.extend(["", "## Check Before Applying"])
    lines.extend(f"- {item}" for item in context["reasons_to_check"] or ["No deterministic blockers found."])
    if context["missing_skills"]:
        lines.extend(["", "## Gaps To Handle"])
        lines.extend(f"- {skill}" for skill in context["missing_skills"])
    return "\n".join(lines)


def build_cv_notes(context: dict) -> str:
    lines = ["# CV Notes", "", "## Skills To Surface"]
    lines.extend(f"- {skill}" for skill in context["matched_skills"] or context["profile_skills"][:8] or ["Add role-relevant skills after review."])
    if context["proof_points"]:
        lines.extend(["", "## Proof Points"])
        lines.extend(f"- {point}" for point in context["proof_points"][:6])
    return "\n".join(lines)


def build_cover_note(context: dict) -> str:
    skills = ", ".join(context["matched_skills"][:4] or context["profile_skills"][:4])
    return "\n".join(
        [
            f"Hi {context['company']} team,",
            "",
            f"I am interested in the {context['job_title']} role. My background aligns with {skills or 'the role requirements'}, and I would like to discuss where I can contribute.",
            "",
            "Best,",
            context["profile_name"],
        ]
    )


def build_recruiter_message(context: dict) -> str:
    return (
        f"Hi, I found the {context['job_title']} role at {context['company']} and it looks relevant to my background. "
        f"My strongest overlap is {', '.join(context['matched_skills'][:3]) or 'the product and engineering scope'}. "
        "Would you be open to pointing me to the best application path?"
    )


def build_answer_bank(context: dict) -> str:
    lines = ["# Answer Bank Seeds", "", "## Why this role?"]
    lines.append(f"- The role matches {', '.join(context['matched_skills'][:5]) or 'my target role direction'}.")
    lines.extend(["", "## Relevant examples"])
    lines.extend(f"- {point}" for point in context["proof_points"][:5] or ["Add a concrete project or metric before applying."])
    return "\n".join(lines)


def build_interview_seed(context: dict) -> str:
    lines = ["# Interview Prep Seeds", "", "## Prepare examples for"]
    lines.extend(f"- {skill}" for skill in context["matched_skills"][:6] or context["profile_skills"][:6] or ["Core role requirements"])
    if context["missing_skills"]:
        lines.extend(["", "## Review gaps"])
        lines.extend(f"- {skill}" for skill in context["missing_skills"][:6])
    return "\n".join(lines)
