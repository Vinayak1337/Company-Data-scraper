from dataclasses import dataclass


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
            gaps.append("Search strategy is usable; review analytics feedback weekly.")
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


class LocalApplicationPrepAdapter(RuntimeAdapter):
    adapter_name = "local_application_prep"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        applications = invocation_payload["context"].get("applications") or []
        active = [item for item in applications if item.get("status") in {"saved", "applying", "applied", "interviewing"}]
        needs_artifacts = [item for item in active if not item.get("artifact_types")]
        return RuntimeResult(
            status="success",
            output={
                "applications_reviewed": len(applications),
                "needs_artifacts_count": len(needs_artifacts),
                "proposals": [
                    {
                        "decision_type": "application_prep",
                        "question": "Review these applications that need prep artifacts?",
                        "changes": {"application_ids": [item.get("id") for item in needs_artifacts[:20]]},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Application Prep Review",
                    "content": application_prep_markdown(active, needs_artifacts),
                    "metadata": {"needs_artifacts": [item.get("id") for item in needs_artifacts]},
                }
            ],
        )


class LocalFollowUpAdapter(RuntimeAdapter):
    adapter_name = "local_follow_up"

    def execute(self, invocation_payload: dict) -> RuntimeResult:
        applications = invocation_payload["context"].get("applications") or []
        due = [
            item
            for item in applications
            if item.get("status") in {"saved", "applying", "applied", "interviewing"} and (item.get("follow_up_at") or item.get("next_action"))
        ]
        return RuntimeResult(
            status="success",
            output={
                "applications_reviewed": len(applications),
                "due_count": len(due),
                "proposals": [
                    {
                        "decision_type": "follow_up",
                        "question": "Review these follow-up actions before changing Today?",
                        "changes": {"application_ids": [item.get("id") for item in due[:20]]},
                        "applies_automatically": False,
                    }
                ],
            },
            artifacts=[
                {
                    "artifact_type": "markdown",
                    "title": "Follow-Up Review",
                    "content": follow_up_markdown(due),
                    "metadata": {"application_ids": [item.get("id") for item in due]},
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
            error=f"{provider} runtime is disabled or worker-only in this build wave.",
        )


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
        recommendations.append("Confirm at least a few proof-point claims before using them in applications.")
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


def application_prep_markdown(active: list[dict], needs_artifacts: list[dict]) -> str:
    lines = ["# Application Prep Review", "", f"Active applications: {len(active)}", "", "## Needs Artifacts"]
    if needs_artifacts:
        lines.extend(f"- {item.get('job_title')} at {item.get('company')}" for item in needs_artifacts[:12])
    else:
        lines.append("- All active applications have at least one prep artifact.")
    lines.extend(["", "## Existing Approved Artifacts"])
    approved = [item for item in active if item.get("approved_artifacts")]
    if approved:
        for item in approved[:12]:
            lines.append(f"- {item.get('job_title')} at {item.get('company')}: {', '.join(item.get('approved_artifacts'))}")
    else:
        lines.append("- No approved artifacts yet.")
    return "\n".join(lines)


def follow_up_markdown(due: list[dict]) -> str:
    lines = ["# Follow-Up Review", ""]
    if due:
        for item in due[:20]:
            action = item.get("next_action") or "Review next step"
            date = item.get("follow_up_at") or "No date"
            lines.append(f"- {item.get('job_title')} at {item.get('company')}: {action} ({date})")
    else:
        lines.append("- No due follow-up actions found.")
    return "\n".join(lines)
