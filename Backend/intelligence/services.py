from collections import Counter

from applications.models import Application
from companies.models import Company
from companies.services import validate_public_careers_url
from intelligence.models import CompanyIntelligence, RecruiterContact


def generate_company_intelligence(company: Company) -> CompanyIntelligence:
    jobs = list(company.jobs.order_by("-first_seen_at")[:100])
    applications = list(Application.objects.filter(job__company=company).order_by("-updated_at")[:25])
    title_terms = Counter()
    remote_modes = Counter()
    for job in jobs:
        remote_modes[job.remote_policy or "unknown"] += 1
        for token in job.title.replace("/", " ").replace("-", " ").split():
            token = token.strip(".,:;()[]").casefold()
            if len(token) > 3:
                title_terms[token] += 1

    role_patterns = [
        {"term": term, "count": count}
        for term, count in title_terms.most_common(8)
    ]
    hiring_signals = build_hiring_signals(company, jobs, applications, remote_modes)
    risk_flags = build_company_risk_flags(company, jobs, applications)
    caveats = build_company_caveats(company, jobs)
    hiring_team_hints = build_hiring_team_hints(company, jobs)
    summary = build_company_summary(company, jobs, applications, role_patterns, risk_flags)

    return CompanyIntelligence.objects.create(
        company=company,
        summary=summary,
        research_notes=build_research_notes(company, jobs, applications),
        hiring_signals=hiring_signals,
        role_patterns=role_patterns,
        role_legitimacy=role_legitimacy(company, jobs, risk_flags),
        caveats=caveats,
        hiring_team_hints=hiring_team_hints,
        interview_process_notes=build_interview_process_notes(applications),
        risk_flags=risk_flags,
        verification_status="deterministic",
        source_snapshot={
            "jobs_seen": len(jobs),
            "applications": len(applications),
            "remote_modes": dict(remote_modes),
            "source_health": company.source_health,
            "last_scraped_at": company.last_scraped_at.isoformat() if company.last_scraped_at else None,
            "source_policy": "public careers pages and user-entered notes only",
        },
    )


def create_recruiter_contact(company: Company, payload: dict) -> RecruiterContact:
    source_url = str(payload.get("source_url") or "").strip()
    if source_url:
        source_url = validate_public_careers_url(source_url)
    return RecruiterContact.objects.create(
        company=company,
        name=str(payload.get("name") or "").strip()[:180],
        title=str(payload.get("title") or "").strip()[:180],
        source_url=source_url,
        source_label=str(payload.get("source_label") or payload.get("source") or "").strip()[:180],
        public_source_only=True,
        status=normalize_contact_status(payload.get("status") or "lead"),
        notes=str(payload.get("notes") or "").strip()[:5000],
    )


def build_hiring_signals(company: Company, jobs: list, applications: list, remote_modes: Counter) -> list[dict]:
    signals = []
    if jobs:
        signals.append({"signal": "active_roles", "message": f"{len(jobs)} roles seen for this company."})
    if company.last_new_role_at:
        signals.append({"signal": "recent_new_role", "message": "A new role was detected from this source."})
    if remote_modes:
        mode, count = remote_modes.most_common(1)[0]
        signals.append({"signal": "work_mode", "message": f"Most observed roles are {mode} ({count})."})
    if applications:
        signals.append({"signal": "tracked_pipeline", "message": f"{len(applications)} application records exist for this company."})
    return signals or [{"signal": "needs_scan", "message": "Run a scan to collect company intelligence."}]


def build_company_risk_flags(company: Company, jobs: list, applications: list) -> list[dict]:
    flags = []
    if company.source_health in {"degraded", "failing", "blocked"}:
        flags.append({"risk": "source_health", "message": f"Source health is {company.source_health}."})
    if company.consecutive_failure_count:
        flags.append({"risk": "scan_failures", "message": f"{company.consecutive_failure_count} consecutive scan failures."})
    if not jobs:
        flags.append({"risk": "no_roles", "message": "No roles are currently stored for this company."})
    if any(application.status == "rejected" for application in applications):
        flags.append({"risk": "pipeline_signal", "message": "At least one prior application was rejected."})
    return flags


def build_company_caveats(company: Company, jobs: list) -> list[dict]:
    caveats = []
    if company.source_health != "active":
        caveats.append({"kind": "source_health", "message": f"Source health is {company.source_health}; research may be incomplete."})
    if len(jobs) < 3:
        caveats.append({"kind": "small_sample", "message": "Only a small number of stored roles were available for pattern analysis."})
    caveats.append({"kind": "public_sources_only", "message": "No private profiles or authenticated sites were used."})
    return caveats


def build_hiring_team_hints(company: Company, jobs: list) -> list[dict]:
    hints = []
    if jobs:
        departments = Counter()
        for job in jobs:
            title = job.title.casefold()
            if "platform" in title or "backend" in title:
                departments["Engineering"] += 1
            elif "data" in title or "ml" in title or "ai" in title:
                departments["Data/AI"] += 1
            elif "frontend" in title or "react" in title:
                departments["Frontend"] += 1
        for team, count in departments.most_common(5):
            hints.append({"team": team, "evidence": f"{count} stored role(s) mention this area."})
    if not hints:
        hints.append({"team": "Unknown", "evidence": f"Review {company.name}'s public careers page before outreach."})
    return hints


def build_research_notes(company: Company, jobs: list, applications: list) -> str:
    return (
        f"Generated from {len(jobs)} stored public role(s), {len(applications)} application record(s), "
        f"and source health '{company.source_health}'. Edit these notes with manual research before relying on them."
    )


def build_interview_process_notes(applications: list) -> str:
    if any(application.status == "interviewing" for application in applications):
        return "At least one application is in interview stage. Add recruiter-provided process details manually."
    return "No confirmed interview process details yet. Add only user-confirmed or public-source notes."


def role_legitimacy(company: Company, jobs: list, risk_flags: list[dict]) -> str:
    if company.source_health in {"blocked", "failing"}:
        return "needs_review"
    if any(flag.get("risk") == "no_roles" for flag in risk_flags):
        return "unknown"
    if jobs:
        return "likely_legitimate"
    return "unknown"


def build_company_summary(company: Company, jobs: list, applications: list, role_patterns: list[dict], risk_flags: list[dict]) -> str:
    if not jobs:
        return f"{company.name} has no stored jobs yet. Keep it tracked and run a scan before prioritizing outreach."
    terms = ", ".join(item["term"] for item in role_patterns[:4]) or "roles"
    risk_note = " Risk flags are present." if risk_flags else " No deterministic risk flags found."
    return f"{company.name} has {len(jobs)} stored roles with recurring terms around {terms}.{risk_note} Pipeline records: {len(applications)}."


def normalize_contact_status(value: str) -> str:
    status = str(value or "lead").strip().lower()
    allowed = {choice[0] for choice in RecruiterContact.STATUS_CHOICES}
    if status not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
    return status
