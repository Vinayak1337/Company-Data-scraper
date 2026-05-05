import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone

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
from agents.observability import execute_with_optional_langsmith
from agents.runtime import (
    DisabledRuntimeAdapter,
    LocalApplicationPrepAdapter,
    LocalFollowUpAdapter,
    LocalMatchReviewAdapter,
    LocalProfileBuilderAdapter,
    LocalSearchStrategyAdapter,
)
from applications.models import Application
from jobs.models import Job
from matching.services import refresh_job_matches, serialize_job_match
from profiles.models import CandidateProfile
from profiles.services import get_search_strategy


PROVIDER_DEFAULTS = [
    {
        "provider": "direct_api",
        "label": "Direct API",
        "model_name": "",
        "enabled": True,
        "worker_only": False,
        "api_key_env_var": "OPENAI_API_KEY",
        "default_tool_policy": "read_only",
        "consent_required": False,
        "daily_run_limit": 100,
        "monthly_budget_cents": 0,
        "estimated_cost_per_run_cents": 0,
        "notes": "Structured direct API runtime. This wave uses local deterministic execution only.",
    },
    {
        "provider": "openrouter",
        "label": "OpenRouter",
        "model_name": "",
        "enabled": False,
        "worker_only": False,
        "api_key_env_var": "OPENROUTER_API_KEY",
        "default_tool_policy": "read_only",
        "consent_required": True,
        "daily_run_limit": 25,
        "monthly_budget_cents": 1000,
        "estimated_cost_per_run_cents": 10,
        "notes": "Hosted model routing placeholder; not executed in this wave.",
    },
    {
        "provider": "deepseek",
        "label": "DeepSeek",
        "model_name": "",
        "enabled": False,
        "worker_only": False,
        "api_key_env_var": "DEEPSEEK_API_KEY",
        "default_tool_policy": "read_only",
        "consent_required": True,
        "daily_run_limit": 25,
        "monthly_budget_cents": 1000,
        "estimated_cost_per_run_cents": 10,
        "notes": "Direct/routed DeepSeek placeholder; not executed in this wave.",
    },
    {
        "provider": "gemini_cli",
        "label": "Gemini CLI",
        "model_name": "",
        "enabled": False,
        "worker_only": True,
        "api_key_env_var": "",
        "default_tool_policy": "safe_shell",
        "consent_required": True,
        "daily_run_limit": 10,
        "monthly_budget_cents": 0,
        "estimated_cost_per_run_cents": 0,
        "notes": "Worker-only CLI adapter placeholder; never executed in web requests.",
    },
    {
        "provider": "claude_code_cli",
        "label": "Claude Code CLI",
        "model_name": "",
        "enabled": False,
        "worker_only": True,
        "api_key_env_var": "",
        "default_tool_policy": "safe_shell",
        "consent_required": True,
        "daily_run_limit": 10,
        "monthly_budget_cents": 0,
        "estimated_cost_per_run_cents": 0,
        "notes": "Worker-only CLI adapter placeholder; never executed in web requests.",
    },
    {
        "provider": "opencode",
        "label": "OpenCode",
        "model_name": "",
        "enabled": False,
        "worker_only": True,
        "api_key_env_var": "",
        "default_tool_policy": "safe_shell",
        "consent_required": True,
        "daily_run_limit": 10,
        "monthly_budget_cents": 0,
        "estimated_cost_per_run_cents": 0,
        "notes": "Worker-only provider-router placeholder; never executed in web requests.",
    },
]

AGENT_PROMPT_VERSIONS = {
    "profile_builder": "local-profile-builder-v1",
    "match_review": "local-match-review-v1",
    "search_strategy": "local-search-strategy-v1",
    "application_prep": "local-application-prep-v1",
    "follow_up": "local-follow-up-v1",
}

BLOCKED_POLICY_LEVELS = {"external_action"}


def ensure_provider_settings() -> list[AgentProviderSetting]:
    settings = []
    for defaults in PROVIDER_DEFAULTS:
        provider_setting, created = AgentProviderSetting.objects.get_or_create(
            provider=defaults["provider"],
            defaults=defaults,
        )
        if not created:
            update_fields = []
            for field in ("consent_required", "daily_run_limit", "monthly_budget_cents", "estimated_cost_per_run_cents"):
                current = getattr(provider_setting, field)
                default = defaults[field]
                if field == "consent_required" and defaults["provider"] != "direct_api" and current is False:
                    setattr(provider_setting, field, default)
                    update_fields.append(field)
                elif field != "consent_required" and current == 0 and default:
                    setattr(provider_setting, field, default)
                    update_fields.append(field)
            if update_fields:
                provider_setting.save(update_fields=[*update_fields, "updated_at"])
        settings.append(provider_setting)
    return settings


def update_provider_setting(provider_setting: AgentProviderSetting, updates: dict) -> AgentProviderSetting:
    update_fields = []
    for field in (
        "enabled",
        "model_name",
        "default_tool_policy",
        "consent_required",
        "daily_run_limit",
        "monthly_budget_cents",
        "estimated_cost_per_run_cents",
        "notes",
    ):
        if field not in updates:
            continue
        value = updates[field]
        if field in {"enabled", "consent_required"}:
            value = coerce_bool(value)
        elif field in {"daily_run_limit", "monthly_budget_cents", "estimated_cost_per_run_cents"}:
            value = nonnegative_int(value, field)
        else:
            value = str(value or "").strip()
        if field == "default_tool_policy" and value not in {choice[0] for choice in AgentProviderSetting.TOOL_POLICY_CHOICES}:
            raise ValueError("Invalid default_tool_policy")
        if getattr(provider_setting, field) != value:
            setattr(provider_setting, field, value)
            update_fields.append(field)
    if update_fields:
        provider_setting.save(update_fields=[*update_fields, "updated_at"])
    return provider_setting


@transaction.atomic
def start_agent_run(
    agent_type: str,
    provider: str = "direct_api",
    model_name: str = "",
    tool_policy: str = "",
    user_consent: bool = False,
) -> AgentRun:
    ensure_provider_settings()
    validate_agent_type(agent_type)
    provider_setting = AgentProviderSetting.objects.get(provider=provider)
    selected_policy = tool_policy or provider_setting.default_tool_policy
    validate_tool_policy(selected_policy)
    assert_provider_runtime_allowed(provider_setting, user_consent)

    run = AgentRun.objects.create(
        agent_type=agent_type,
        provider=provider,
        model_name=model_name or provider_setting.model_name,
        tool_policy=selected_policy,
        prompt_version=AGENT_PROMPT_VERSIONS.get(agent_type, "unknown"),
        input_snapshot=build_input_snapshot(agent_type, provider_setting),
    )
    add_audit(run, "run_created", "Agent run created.", {"agent_type": agent_type, "provider": provider})
    record_permissions(run, selected_policy)
    if agent_execution_mode() == "inline":
        execute_agent_run(run)
    else:
        add_step(run, "Queued for worker", "queued", "Run will execute through the agent queue worker.")
        add_audit(run, "run_queued", "Agent run queued for worker execution.", {"execution_mode": agent_execution_mode()})
    return run


def process_queued_agent_runs(limit: int | None = None) -> dict:
    limit = limit or getattr(settings, "AGENT_QUEUE_BATCH_SIZE", 5)
    runs = list(AgentRun.objects.filter(status="queued").order_by("requested_at", "id")[:limit])
    completed = 0
    failed = 0
    for run in runs:
        execute_agent_run(run)
        run.refresh_from_db()
        if run.status == "success":
            completed += 1
        elif run.status == "failed":
            failed += 1
    return {"selected": len(runs), "completed": completed, "failed": failed}


def execute_agent_run(run: AgentRun) -> AgentRun:
    if run.status in {"cancelled", "success"}:
        return run

    run.status = "running"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])
    add_audit(run, "run_started", "Agent run started.")

    try:
        adapter = adapter_for_run(run)
        context = run.input_snapshot | {"provider": run.provider}
        payload = adapter.prepare(context, run.tool_policy)
        invocation = RuntimeInvocation.objects.create(
            run=run,
            provider=run.provider,
            adapter=adapter.adapter_name,
            model_name=run.model_name,
            status="running",
            input_snapshot=scrub_snapshot(payload),
            started_at=timezone.now(),
        )
        result, langsmith_metadata = execute_with_optional_langsmith(run, payload, lambda: adapter.execute(payload))
        if langsmith_metadata:
            add_audit(
                run,
                f"langsmith_{langsmith_metadata['status']}",
                "LangSmith tracing metadata recorded for this agent run.",
                langsmith_metadata,
            )
        finish_running_steps(run, "success" if result.status == "success" else "failed", result.error)
        invocation.status = "success" if result.status == "success" else "skipped"
        invocation.output_snapshot = result.output
        invocation.error = result.error
        invocation.token_count = result.token_count
        invocation.cost_estimate = result.cost_estimate
        invocation.finished_at = timezone.now()
        invocation.save(
            update_fields=[
                "status",
                "output_snapshot",
                "error",
                "token_count",
                "cost_estimate",
                "finished_at",
            ]
        )

        for artifact in adapter.collect_artifacts(result):
            AgentArtifact.objects.create(
                run=run,
                artifact_type=artifact.get("artifact_type", "text"),
                title=artifact.get("title", "Artifact"),
                content=artifact.get("content", ""),
                metadata=artifact.get("metadata", {}),
            )

        decision_count = create_review_decisions(run, result.output) if result.status == "success" else 0
        run.output_snapshot = result.output
        run.result_summary = run_summary(run, result.output)
        run.status = "waiting_approval" if decision_count else "success" if result.status == "success" else "failed"
        if result.error:
            run.user_safe_error = result.error
        run.finished_at = timezone.now()
        run.save(update_fields=["output_snapshot", "result_summary", "status", "user_safe_error", "finished_at", "updated_at"])
        add_step(run, "Collect artifacts", "success", "Artifacts collected and stored.")
        if decision_count:
            add_step(run, "Create approval queue", "success", f"{decision_count} review decision(s) are waiting.")
            add_audit(run, "decisions_created", "Review decisions created for user approval.", {"count": decision_count})
        add_audit(run, "run_finished", f"Agent run finished with status {run.status}.")
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.user_safe_error = "Agent run failed before producing a reviewable result."
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "user_safe_error", "finished_at", "updated_at"])
        add_audit(run, "run_failed", run.user_safe_error, {"error_type": exc.__class__.__name__})
    return run


def cancel_agent_run(run: AgentRun) -> AgentRun:
    if run.status in {"success", "failed", "cancelled"}:
        return run
    run.status = "cancelled"
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "finished_at", "updated_at"])
    add_audit(run, "run_cancelled", "Agent run cancelled by user.")
    return run


def retry_agent_run(run: AgentRun) -> AgentRun:
    return start_agent_run(
        run.agent_type,
        provider=run.provider,
        model_name=run.model_name,
        tool_policy=run.tool_policy,
        user_consent=True,
    )


def set_agent_decision_status(decision: AgentDecision, status: str) -> AgentDecision:
    status = str(status or "").strip().lower()
    if status not in {"approved", "rejected"}:
        raise ValueError("decision status must be approved or rejected")
    if decision.status == status:
        return decision
    if decision.status != "pending":
        raise ValueError("Only pending decisions can be changed.")
    decision.status = status
    decision.decided_at = timezone.now()
    decision.save(update_fields=["status", "decided_at"])
    add_audit(
        decision.run,
        f"decision_{status}",
        f"User marked {decision.decision_type} as {status}. No data was changed automatically.",
        {"decision_id": decision.id},
    )
    if not decision.run.decisions.filter(status="pending").exists() and decision.run.status == "waiting_approval":
        decision.run.status = "success"
        decision.run.save(update_fields=["status", "updated_at"])
    return decision


def adapter_for_run(run: AgentRun):
    provider_setting = AgentProviderSetting.objects.get(provider=run.provider)
    if run.tool_policy in BLOCKED_POLICY_LEVELS:
        add_step(run, "Policy check", "failed", "External actions are blocked in v2.")
        raise ValueError("External actions are blocked in v2.")
    if not provider_setting.enabled:
        add_step(run, "Provider disabled", "failed", "This runtime provider is disabled in settings.")
        return DisabledRuntimeAdapter()
    if provider_setting.worker_only:
        add_step(run, "Worker-only guard", "failed", "CLI runtimes are disabled until worker execution is implemented.")
        return DisabledRuntimeAdapter()
    if run.provider == "direct_api":
        adapters = {
            "profile_builder": ("Local profile analysis", "Running deterministic Profile Builder review.", LocalProfileBuilderAdapter),
            "match_review": ("Local match review", "Reviewing strongest and weakest job matches.", LocalMatchReviewAdapter),
            "search_strategy": ("Local search strategy review", "Reviewing search strategy coverage.", LocalSearchStrategyAdapter),
            "application_prep": ("Local application prep", "Reviewing saved applications and prep gaps.", LocalApplicationPrepAdapter),
            "follow_up": ("Local follow-up review", "Reviewing due follow-ups and next actions.", LocalFollowUpAdapter),
        }
        if run.agent_type in adapters:
            name, message, adapter_cls = adapters[run.agent_type]
            add_step(run, name, "running", message)
            return adapter_cls()
    add_step(run, "Runtime disabled", "failed", "This agent/runtime is not implemented in this build wave.")
    return DisabledRuntimeAdapter()


def agent_runtime_status() -> dict:
    ensure_provider_settings()
    return {
        "execution_mode": agent_execution_mode(),
        "queue_batch_size": getattr(settings, "AGENT_QUEUE_BATCH_SIZE", 5),
        "queued_runs": AgentRun.objects.filter(status="queued").count(),
        "running_runs": AgentRun.objects.filter(status="running").count(),
        "providers": [provider_budget_status(provider) for provider in AgentProviderSetting.objects.all()],
    }


def provider_budget_status(provider_setting: AgentProviderSetting) -> dict:
    today_start = timezone.now() - timedelta(hours=24)
    month_start = timezone.now() - timedelta(days=30)
    daily_runs = AgentRun.objects.filter(provider=provider_setting.provider, requested_at__gte=today_start).count()
    spent = (
        RuntimeInvocation.objects.filter(provider=provider_setting.provider, created_at__gte=month_start)
        .aggregate(total=Sum("cost_estimate"))
        .get("total")
        or Decimal("0")
    )
    monthly_budget = Decimal(provider_setting.monthly_budget_cents) / Decimal("100")
    return {
        "provider": provider_setting.provider,
        "label": provider_setting.label,
        "enabled": provider_setting.enabled,
        "worker_only": provider_setting.worker_only,
        "consent_required": provider_setting.consent_required,
        "daily_run_limit": provider_setting.daily_run_limit,
        "daily_runs_used": daily_runs,
        "daily_runs_remaining": max(provider_setting.daily_run_limit - daily_runs, 0),
        "monthly_budget_cents": provider_setting.monthly_budget_cents,
        "monthly_spend_estimate": float(spent),
        "monthly_budget_estimate": float(monthly_budget),
        "estimated_cost_per_run_cents": provider_setting.estimated_cost_per_run_cents,
    }


def assert_provider_runtime_allowed(provider_setting: AgentProviderSetting, user_consent: bool) -> None:
    if provider_setting.consent_required and not user_consent:
        raise ValueError("User consent is required before starting this runtime.")

    status = provider_budget_status(provider_setting)
    if provider_setting.daily_run_limit and status["daily_runs_remaining"] <= 0:
        raise ValueError(f"Daily run limit reached for {provider_setting.label}.")

    if provider_setting.monthly_budget_cents:
        monthly_budget = Decimal(provider_setting.monthly_budget_cents) / Decimal("100")
        projected = Decimal(str(status["monthly_spend_estimate"])) + (Decimal(provider_setting.estimated_cost_per_run_cents) / Decimal("100"))
        if projected > monthly_budget:
            raise ValueError(f"Monthly budget reached for {provider_setting.label}.")


def agent_execution_mode() -> str:
    mode = str(getattr(settings, "AGENT_EXECUTION_MODE", "inline") or "inline").strip().lower()
    return "queued" if mode in {"queued", "worker", "async"} else "inline"


def build_input_snapshot(agent_type: str, provider_setting: AgentProviderSetting) -> dict:
    snapshot = {
        "agent_type": agent_type,
        "provider": provider_setting.provider,
        "provider_enabled": provider_setting.enabled,
        "worker_only": provider_setting.worker_only,
        "api_key_configured": bool(provider_setting.api_key_env_var and os.environ.get(provider_setting.api_key_env_var)),
    }
    if agent_type == "profile_builder":
        profile = CandidateProfile.objects.prefetch_related("target_titles", "claims").order_by("id").first()
        snapshot["profile"] = serialize_profile_snapshot(profile)
    elif agent_type == "match_review":
        profile = CandidateProfile.objects.prefetch_related("target_titles", "claims").order_by("id").first()
        jobs = list(Job.objects.select_related("company").order_by("-first_seen_at")[:50])
        matches = refresh_job_matches(jobs)
        snapshot["jobs"] = [serialize_job_snapshot(job, matches.get(job.id)) for job in jobs]
    elif agent_type == "search_strategy":
        profile = CandidateProfile.objects.prefetch_related("target_titles", "claims").order_by("id").first()
        snapshot["profile"] = serialize_profile_snapshot(profile)
        if profile:
            strategy = get_search_strategy(profile)
            snapshot["search_strategy"] = {
                "role_families": strategy.role_families,
                "target_title_keywords": strategy.target_title_keywords,
                "negative_keywords": strategy.negative_keywords,
                "seniority_levels": strategy.seniority_levels,
                "location_keywords": strategy.location_keywords,
                "work_mode_preferences": strategy.work_mode_preferences,
                "notes": strategy.notes,
            }
    elif agent_type in {"application_prep", "follow_up"}:
        applications = Application.objects.select_related("job", "job__company").prefetch_related("artifacts").order_by("follow_up_at", "-updated_at")[:50]
        snapshot["applications"] = [serialize_application_snapshot(application) for application in applications]
    return snapshot


def serialize_profile_snapshot(profile: CandidateProfile | None) -> dict:
    if not profile:
        return {
            "exists": False,
            "skills": [],
            "target_titles": [],
            "claims": [],
            "cv_markdown": "",
            "profile_markdown": "",
            "summary": "",
        }
    return {
        "exists": True,
        "full_name": profile.full_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "skills": profile.skills,
        "cv_markdown": profile.cv_markdown,
        "profile_markdown": profile.profile_markdown,
        "target_titles": [
            {
                "title": title.title,
                "status": title.status,
                "fit_bucket": title.fit_bucket,
                "confidence_score": title.confidence_score,
                "knowledge_accuracy": title.knowledge_accuracy,
            }
            for title in profile.target_titles.all()
        ],
        "claims": [
            {
                "id": claim.id,
                "claim_type": claim.claim_type,
                "text": claim.text,
                "status": claim.status,
            }
            for claim in profile.claims.all()
        ],
    }


def serialize_job_snapshot(job: Job, match) -> dict:
    match_payload = serialize_job_match(match) if match else {}
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company.name,
        "location": job.location,
        "remote_policy": job.remote_policy,
        "apply_url": job.apply_url,
        "match": {
            "overall_score": match_payload.get("overall_score", 0),
            "confidence_score": match_payload.get("confidence_score", 0),
            "apply_priority": match_payload.get("apply_priority", "unknown"),
            "reasons_to_apply": match_payload.get("reasons_to_apply", []),
            "reasons_to_skip": match_payload.get("reasons_to_skip", []),
            "missing_skills": match_payload.get("missing_skills", []),
        },
    }


def serialize_application_snapshot(application: Application) -> dict:
    return {
        "id": application.id,
        "status": application.status,
        "job_title": application.job.title,
        "company": application.job.company.name,
        "location": application.job.location,
        "next_action": application.next_action,
        "follow_up_at": application.follow_up_at.isoformat() if application.follow_up_at else None,
        "notes": application.notes,
        "artifact_types": [artifact.artifact_type for artifact in application.artifacts.all()],
        "approved_artifacts": [artifact.title for artifact in application.artifacts.all() if artifact.status == "approved"],
    }


def record_permissions(run: AgentRun, tool_policy: str) -> None:
    policies = ["read_only", "workspace_write", "safe_shell", "network_tools", "external_action"]
    for policy in policies:
        if policy == tool_policy or policy == "read_only":
            status = "blocked" if policy in BLOCKED_POLICY_LEVELS else "granted"
            reason = "External actions are blocked in v2." if status == "blocked" else "Allowed by selected policy."
        else:
            status = "blocked"
            reason = "Not included in selected tool policy."
        AgentPermission.objects.create(run=run, policy_level=policy, status=status, reason=reason)


def add_step(run: AgentRun, name: str, status: str, message: str = "") -> AgentStep:
    order = run.steps.count() + 1
    now = timezone.now()
    return AgentStep.objects.create(
        run=run,
        order=order,
        name=name,
        status=status,
        message=message,
        started_at=now,
        finished_at=now if status in {"success", "failed", "cancelled"} else None,
    )


def finish_running_steps(run: AgentRun, status: str, message: str = "") -> None:
    now = timezone.now()
    for step in run.steps.filter(status="running"):
        step.status = status
        if message:
            step.message = message
        step.finished_at = now
        step.save(update_fields=["status", "message", "finished_at"])


def add_audit(run: AgentRun, event_type: str, message: str = "", metadata: dict | None = None) -> AgentAuditLog:
    return AgentAuditLog.objects.create(run=run, event_type=event_type, message=message, metadata=metadata or {})


def create_review_decisions(run: AgentRun, output: dict) -> int:
    proposals = output.get("proposals") if isinstance(output, dict) else []
    if not isinstance(proposals, list):
        proposals = []

    created = 0
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        decision_type = str(proposal.get("decision_type") or run.agent_type).strip()[:80]
        question = str(proposal.get("question") or default_decision_question(run.agent_type)).strip()
        if not question:
            question = default_decision_question(run.agent_type)
        AgentDecision.objects.create(
            run=run,
            decision_type=decision_type,
            question=question,
            proposed_changes=proposal,
        )
        created += 1
    return created


def default_decision_question(agent_type: str) -> str:
    defaults = {
        "profile_builder": "Review these profile recommendations?",
        "match_review": "Review these match recommendations?",
        "search_strategy": "Review these search strategy changes?",
        "application_prep": "Review these application prep suggestions?",
        "follow_up": "Review these follow-up suggestions?",
    }
    return defaults.get(agent_type, "Review this agent proposal?")


def run_summary(run: AgentRun, output: dict) -> str:
    if run.agent_type == "profile_builder":
        return f"Profile Builder completed with readiness score {output.get('readiness_score', 0)}/100."
    if run.agent_type == "match_review":
        return f"Match Review found {output.get('apply_now_count', 0)} apply-now roles and {output.get('risk_count', 0)} roles to check."
    if run.agent_type == "search_strategy":
        return f"Search Strategy reviewed {output.get('keyword_count', 0)} keywords across {output.get('role_family_count', 0)} role families."
    if run.agent_type == "application_prep":
        return f"Application Prep found {output.get('needs_artifacts_count', 0)} applications needing artifacts."
    if run.agent_type == "follow_up":
        return f"Follow-Up reviewed {output.get('due_count', 0)} due or ready next actions."
    return "Agent run completed."


def validate_agent_type(agent_type: str) -> None:
    allowed = {choice[0] for choice in AgentRun.AGENT_TYPE_CHOICES}
    if agent_type not in allowed:
        raise ValueError(f"agent_type must be one of: {', '.join(sorted(allowed))}")


def validate_tool_policy(tool_policy: str) -> None:
    allowed = {choice[0] for choice in AgentRun.TOOL_POLICY_CHOICES}
    if tool_policy not in allowed:
        raise ValueError(f"tool_policy must be one of: {', '.join(sorted(allowed))}")


def nonnegative_int(value, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")
    if parsed < 0:
        raise ValueError(f"{field} must be zero or greater")
    return parsed


def scrub_snapshot(snapshot: dict) -> dict:
    sanitized = dict(snapshot)
    context = sanitized.get("context")
    if isinstance(context, dict):
        context = dict(context)
        profile = context.get("profile")
        if isinstance(profile, dict):
            profile = dict(profile)
            if profile.get("cv_markdown"):
                profile["cv_markdown"] = f"[redacted cv markdown, {len(profile['cv_markdown'])} chars]"
            if profile.get("profile_markdown"):
                profile["profile_markdown"] = f"[redacted profile markdown, {len(profile['profile_markdown'])} chars]"
            context["profile"] = profile
        sanitized["context"] = context
    return sanitized


def coerce_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
