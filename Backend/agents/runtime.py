import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    output: dict
    artifacts: list[dict]
    error: str = ""
    token_count: int = 0
    cost_estimate: float = 0


class RuntimeAdapter:
    adapter_name = "base"

    def prepare(self, context: dict, policy: str) -> dict:
        return {"context": context, "policy": policy}

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        raise NotImplementedError

    def collect_artifacts(self, runtime_result: RuntimeResult) -> list[dict]:
        return runtime_result.artifacts

    def summarize_failure(self, error: Exception) -> str:
        return str(error) or error.__class__.__name__


class LocalCliReviewAdapter(RuntimeAdapter):
    adapter_name = "local_cli_review"
    DEFAULT_COMMANDS = {
        "gemini_cli": ["gemini", "-p", "{prompt}"],
        "claude_code_cli": ["claude", "-p", "{prompt}"],
        "codex_cli": ["codex", "exec", "{prompt}"],
        "opencode": ["opencode", "run", "{prompt}"],
    }

    def __init__(self, provider: str, label: str):
        self.provider = provider
        self.label = label

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        prompt = cli_review_prompt(invocation_payload)
        args = self.command_args(prompt)
        timeout = int(env_setting("JOB_SCOUT_CLI_TIMEOUT_SECONDS", "120") or "120")
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return RuntimeResult(
                status="failed",
                output={"provider": self.provider},
                artifacts=[],
                error=f"{self.label} command was not found in PATH.",
            )
        except subprocess.TimeoutExpired:
            return RuntimeResult(
                status="failed",
                output={"provider": self.provider},
                artifacts=[],
                error=f"{self.label} timed out after {timeout} seconds.",
            )

        output = completed.stdout.strip()
        error_output = completed.stderr.strip()
        if completed.returncode != 0:
            return RuntimeResult(
                status="failed",
                output={"provider": self.provider, "stderr": error_output[:4000]},
                artifacts=[],
                error=error_output[:1000] or f"{self.label} exited with status {completed.returncode}.",
            )

        content = output or "(CLI returned no text.)"
        return RuntimeResult(
            status="success",
            output={
                "provider": self.provider,
                "cli_review": content[:20000],
                "proposals": [
                    {
                        "decision_type": "cli_brain_review",
                        "question": f"Review {self.label}'s local brain output?",
                        "changes": {"provider": self.provider, "review": content[:4000]},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": f"{self.label} Brain Review",
                    "content": content,
                    "metadata": {"provider": self.provider},
                }
            ],
        )

    def command_args(self, prompt: str) -> list[str]:
        env_key = f"JOB_SCOUT_{self.provider.upper()}_COMMAND"
        configured = env_setting(env_key, "").strip()
        if configured:
            parts = shlex.split(configured)
            return [prompt if part == "{prompt}" else part for part in parts] if "{prompt}" in parts else [*parts, prompt]
        return [prompt if part == "{prompt}" else part for part in self.DEFAULT_COMMANDS.get(self.provider, [self.provider, "{prompt}"])]


class LocalProfileBuilderAdapter(RuntimeAdapter):
    adapter_name = "local_profile_builder"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        context = invocation_payload["context"]
        profile = context.get("profile") or {}
        target_titles = profile.get("target_titles") or []
        claims = profile.get("claims") or []
        skills = profile.get("skills") or []
        unconfirmed_claims = [claim for claim in claims if claim.get("status") == "unconfirmed"]
        accepted_titles = [title for title in target_titles if title.get("status") == "accepted"]

        readiness_score = profile_readiness_score(profile, target_titles, claims)
        recommendations = profile_recommendations(profile, target_titles, claims)
        markdown = profile_builder_markdown(profile, readiness_score, recommendations, unconfirmed_claims, accepted_titles)

        return RuntimeResult(
            status="success",
            output={
                "readiness_score": readiness_score,
                "skills_count": len(skills),
                "target_titles_count": len(target_titles),
                "accepted_titles_count": len(accepted_titles),
                "unconfirmed_claims_count": len(unconfirmed_claims),
                "recommendations": recommendations,
                "proposals": [
                    {
                        "decision_type": "profile_recommendations",
                        "question": "Accept this profile readiness review as the next profile work queue?",
                        "changes": {"recommendations": recommendations},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Profile Builder Review",
                    "content": markdown,
                    "metadata": {"readiness_score": readiness_score},
                },
                {
                    "artifact_type": "json",
                    "title": "Profile Builder Metrics",
                    "content": "",
                    "metadata": {
                        "readiness_score": readiness_score,
                        "recommendations": recommendations,
                    },
                },
            ],
        )


class LocalMatchReviewAdapter(RuntimeAdapter):
    adapter_name = "local_match_review"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        jobs = invocation_payload["context"].get("jobs") or []
        apply_now = [job for job in jobs if job.get("match", {}).get("apply_priority") == "apply_now"]
        risks = [
            job
            for job in jobs
            if job.get("match", {}).get("reasons_to_skip") or job.get("match", {}).get("confidence_score", 0) < 50
        ]
        markdown = match_review_markdown(apply_now, risks, jobs)
        return RuntimeResult(
            status="success",
            output={
                "jobs_reviewed": len(jobs),
                "apply_now_count": len(apply_now),
                "risk_count": len(risks),
                "proposals": [
                    {
                        "decision_type": "match_review",
                        "question": "Review these apply-now roles and caveats?",
                        "changes": {
                            "apply_now_job_ids": [job.get("id") for job in apply_now[:10]],
                            "risk_job_ids": [job.get("id") for job in risks[:10]],
                        },
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Match Review",
                    "content": markdown,
                    "metadata": {"jobs_reviewed": len(jobs)},
                }
            ],
        )


class LocalSearchStrategyAdapter(RuntimeAdapter):
    adapter_name = "local_search_strategy"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        strategy = invocation_payload["context"].get("search_strategy") or {}
        profile = invocation_payload["context"].get("profile") or {}
        keyword_count = len(strategy.get("target_title_keywords") or [])
        role_family_count = len(strategy.get("role_families") or [])
        gaps = []
        if not keyword_count:
            gaps.append("Generate or edit target title keywords before relying on company filters.")
        if not strategy.get("negative_keywords"):
            gaps.append("Add negative keywords for roles you consistently skip.")
        if not strategy.get("location_keywords") and profile.get("location"):
            gaps.append("Convert preferred locations into strategy keywords.")
        if not gaps:
            gaps.append("Search strategy is usable; tune it with match feedback over time.")
        return RuntimeResult(
            status="success",
            output={
                "keyword_count": keyword_count,
                "role_family_count": role_family_count,
                "gaps": gaps,
                "proposals": [
                    {
                        "decision_type": "search_strategy_review",
                        "question": "Review these search strategy gaps before changing filters?",
                        "changes": {"gaps": gaps},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Search Strategy Review",
                    "content": search_strategy_markdown(strategy, gaps),
                    "metadata": {"keyword_count": keyword_count, "role_family_count": role_family_count},
                }
            ],
        )


class LocalSourceDiscoveryAdapter(RuntimeAdapter):
    adapter_name = "local_source_discovery"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        companies = invocation_payload["context"].get("companies") or []
        needs_source = [item for item in companies if item.get("source_health") in {"needs_source", "needs_review"}]
        ready = [item for item in companies if item.get("primary_source_url")]
        return RuntimeResult(
            status="success",
            output={
                "companies_reviewed": len(companies),
                "needs_source_count": len(needs_source),
                "ready_source_count": len(ready),
                "proposals": [
                    {
                        "decision_type": "source_discovery",
                        "question": "Review these companies that need a verified jobs source?",
                        "changes": {"company_ids": [item.get("id") for item in needs_source[:20]]},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Source Discovery Review",
                    "content": source_discovery_markdown(needs_source, ready, companies),
                    "metadata": {"needs_source_company_ids": [item.get("id") for item in needs_source]},
                }
            ],
        )


class LocalNotificationReviewAdapter(RuntimeAdapter):
    adapter_name = "local_notification_review"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        jobs = invocation_payload["context"].get("jobs") or []
        notify = [job for job in jobs if job.get("match", {}).get("should_notify")]
        held = [job for job in jobs if not job.get("match", {}).get("should_notify")]
        return RuntimeResult(
            status="success",
            output={
                "jobs_reviewed": len(jobs),
                "notify_count": len(notify),
                "held_count": len(held),
                "proposals": [
                    {
                        "decision_type": "notification_review",
                        "question": "Review these jobs selected for notification?",
                        "changes": {"job_ids": [item.get("id") for item in notify[:20]]},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Notification Review",
                    "content": notification_review_markdown(notify, held, jobs),
                    "metadata": {"notify_job_ids": [item.get("id") for item in notify]},
                }
            ],
        )


class DisabledRuntimeAdapter(RuntimeAdapter):
    adapter_name = "disabled_runtime"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        provider = invocation_payload.get("context", {}).get("provider", "runtime")
        return RuntimeResult(
            status="skipped",
            output={"disabled": True, "provider": provider},
            artifacts=[],
            error=f"{provider} runtime is disabled or unavailable in this local process.",
        )


def cli_review_prompt(invocation_payload: dict) -> str:
    context = invocation_payload.get("context") or {}
    agent_type = context.get("agent_type", "agent_review")
    compact_context = json.dumps(context, ensure_ascii=True, indent=2, default=str)[:60000]
    return "\n".join(
        [
            "You are the local Job Scout brain running from a developer terminal.",
            "Review the structured context and return a concise, actionable markdown report.",
            "Do not take external actions, send emails, modify files, or browse unless the caller explicitly asks in a later tool.",
            f"Agent type: {agent_type}",
            "",
            "Return sections:",
            "1. Decision summary",
            "2. Strong signals",
            "3. Risks or missing data",
            "4. Recommended next action",
            "",
            "Context JSON:",
            compact_context,
        ]
    )


def env_setting(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    if value not in {None, ""}:
        return str(value)
    env_path = Path(getattr(settings, "BASE_DIR", ".")) / ".env"
    if not env_path.exists():
        return str(default or "")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        item_key, item_value = stripped.split("=", 1)
        if item_key.strip() == key:
            return item_value.strip().strip("'\"")
    return str(default or "")


def profile_readiness_score(profile: dict, target_titles: list[dict], claims: list[dict]) -> int:
    score = 0
    if profile.get("summary"):
        score += 15
    if profile.get("cv_markdown"):
        score += 20
    if profile.get("profile_markdown"):
        score += 15
    if profile.get("skills"):
        score += min(20, len(profile["skills"]) * 2)
    if target_titles:
        score += 15
    if any(claim.get("status") == "confirmed" for claim in claims):
        score += 15
    return min(score, 100)


def profile_recommendations(profile: dict, target_titles: list[dict], claims: list[dict]) -> list[str]:
    recommendations = []
    if not profile.get("cv_markdown"):
        recommendations.append("Paste or write a canonical cv.md before running match review.")
    if not profile.get("profile_markdown"):
        recommendations.append("Create profile.md with strengths, proof points, and role framing.")
    if not target_titles:
        recommendations.append("Generate target titles and accept the ones that reflect the search strategy.")
    if not any(claim.get("status") == "confirmed" for claim in claims):
        recommendations.append("Confirm at least a few proof-point claims before relying on AI match explanations.")
    if not profile.get("skills"):
        recommendations.append("Add skills manually or import a resume so alerts can use profile terms.")
    if not recommendations:
        recommendations.append("Profile is ready for match-review work once job scoring is added.")
    return recommendations


def profile_builder_markdown(
    profile: dict,
    readiness_score: int,
    recommendations: list[str],
    unconfirmed_claims: list[dict],
    accepted_titles: list[dict],
) -> str:
    lines = [
        "# Profile Builder Review",
        "",
        f"Readiness score: {readiness_score}/100",
        "",
        "## Accepted Titles",
    ]
    if accepted_titles:
        lines.extend(f"- {title.get('title')}" for title in accepted_titles)
    else:
        lines.append("- None accepted yet")
    lines.extend(["", "## Recommendations"])
    lines.extend(f"- {item}" for item in recommendations)
    lines.extend(["", "## Unconfirmed Claims"])
    if unconfirmed_claims:
        lines.extend(f"- {claim.get('text')}" for claim in unconfirmed_claims[:10])
    else:
        lines.append("- None")
    return "\n".join(lines)


def match_review_markdown(apply_now: list[dict], risks: list[dict], jobs: list[dict]) -> str:
    lines = ["# Match Review", "", f"Jobs reviewed: {len(jobs)}", "", "## Apply Now"]
    if apply_now:
        for job in apply_now[:10]:
            lines.append(f"- {job.get('title')} at {job.get('company')} ({job.get('match', {}).get('overall_score', 0)}/100)")
    else:
        lines.append("- No apply-now roles found.")
    lines.extend(["", "## Check Before Applying"])
    if risks:
        for job in risks[:10]:
            reasons = "; ".join((job.get("match") or {}).get("reasons_to_skip") or ["Low confidence"])
            lines.append(f"- {job.get('title')} at {job.get('company')}: {reasons}")
    else:
        lines.append("- No risk flags found.")
    return "\n".join(lines)


def search_strategy_markdown(strategy: dict, gaps: list[str]) -> str:
    lines = ["# Search Strategy Review", "", "## Role Families"]
    lines.extend(f"- {family}" for family in strategy.get("role_families") or ["None"])
    lines.extend(["", "## Keywords"])
    lines.extend(f"- {keyword}" for keyword in strategy.get("target_title_keywords") or ["None"])
    lines.extend(["", "## Recommendations"])
    lines.extend(f"- {gap}" for gap in gaps)
    return "\n".join(lines)


def source_discovery_markdown(needs_source: list[dict], ready: list[dict], companies: list[dict]) -> str:
    lines = ["# Source Discovery Review", "", f"Companies reviewed: {len(companies)}", "", "## Needs Source Review"]
    if needs_source:
        lines.extend(f"- {item.get('name')} ({item.get('domain') or item.get('homepage_url') or 'no domain'})" for item in needs_source[:20])
    else:
        lines.append("- All active companies have usable sources.")
    lines.extend(["", "## Ready Sources"])
    if ready:
        lines.extend(f"- {item.get('name')}: {item.get('primary_source_url')}" for item in ready[:20])
    else:
        lines.append("- No ready sources yet.")
    return "\n".join(lines)


def notification_review_markdown(notify: list[dict], held: list[dict], jobs: list[dict]) -> str:
    lines = ["# Notification Review", "", f"Jobs reviewed: {len(jobs)}", "", "## Notify"]
    if notify:
        for item in notify[:20]:
            match = item.get("match") or {}
            lines.append(f"- {item.get('title')} at {item.get('company')} ({match.get('overall_score', 0)}%, confidence {match.get('confidence_score', 0)}%)")
    else:
        lines.append("- No jobs currently clear notification thresholds.")
    lines.extend(["", "## Held"])
    if held:
        for item in held[:20]:
            match = item.get("match") or {}
            lines.append(f"- {item.get('title')} at {item.get('company')}: score {match.get('overall_score', 0)}, threshold {match.get('notification_threshold', 0)}")
    else:
        lines.append("- No held jobs in this review.")
    return "\n".join(lines)
