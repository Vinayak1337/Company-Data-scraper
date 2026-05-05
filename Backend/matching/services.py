from __future__ import annotations

import re
from dataclasses import dataclass

from django.utils import timezone

from jobs.models import Job
from matching.models import JobMatch
from profiles.models import CandidateProfile


TECH_TERMS = {
    "python",
    "django",
    "fastapi",
    "flask",
    "postgres",
    "postgresql",
    "mysql",
    "redis",
    "react",
    "next.js",
    "nextjs",
    "typescript",
    "javascript",
    "node",
    "node.js",
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "terraform",
    "graphql",
    "rest",
    "java",
    "spring",
    "go",
    "golang",
    "rust",
    "ruby",
    "rails",
    "data",
    "ml",
    "machine learning",
    "ai",
}

SENIORITY_TERMS = {
    "intern",
    "junior",
    "associate",
    "mid",
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
}


@dataclass(frozen=True)
class ScorePart:
    score: int
    evidence: list[dict]
    reasons_to_apply: list[str]
    reasons_to_skip: list[str]


def refresh_job_match(job: Job, profile: CandidateProfile | None = None) -> JobMatch:
    profile = profile if profile is not None else current_profile()
    report = build_match_report(job, profile)
    match, _ = JobMatch.objects.update_or_create(
        job=job,
        defaults={
            "profile": profile,
            "source": "deterministic",
            "profile_updated_at": profile.updated_at if profile else None,
            **report,
        },
    )
    return match


def refresh_job_matches(jobs) -> dict[int, JobMatch]:
    profile = current_profile()
    matches = {}
    for job in jobs:
        matches[job.id] = refresh_job_match(job, profile=profile)
    return matches


def build_match_report(job: Job, profile: CandidateProfile | None) -> dict:
    title_part = score_title(job, profile)
    skill_part, matched_skills, missing_skills = score_skills(job, profile)
    location_part = score_location(job, profile)
    seniority_part = score_seniority(job, profile)
    confidence_score = profile_confidence(profile)
    overall_score = clamp(
        round(
            title_part.score * 0.35
            + skill_part.score * 0.3
            + location_part.score * 0.2
            + seniority_part.score * 0.15
        )
    )

    evidence = title_part.evidence + skill_part.evidence + location_part.evidence + seniority_part.evidence
    reasons_to_apply = dedupe(title_part.reasons_to_apply + skill_part.reasons_to_apply + location_part.reasons_to_apply + seniority_part.reasons_to_apply)
    reasons_to_skip = dedupe(title_part.reasons_to_skip + skill_part.reasons_to_skip + location_part.reasons_to_skip + seniority_part.reasons_to_skip)
    if not profile:
        reasons_to_skip.append("No profile is available, so score confidence is limited.")

    report = {
        "overall_score": overall_score,
        "title_score": title_part.score,
        "skill_score": skill_part.score,
        "seniority_score": seniority_part.score,
        "location_score": location_part.score,
        "confidence_score": confidence_score,
        "knowledge_coverage_score": skill_part.score,
        "apply_priority": apply_priority(overall_score, confidence_score),
        "reasons_to_apply": reasons_to_apply[:6],
        "reasons_to_skip": reasons_to_skip[:6],
        "missing_skills": missing_skills[:10],
        "evidence": evidence[:12],
        "generated_at": timezone.now(),
    }
    return apply_active_score_correction(job, report)


def score_title(job: Job, profile: CandidateProfile | None) -> ScorePart:
    accepted_titles = accepted_target_titles(profile)
    title = job.title.lower()
    evidence = []
    reasons_to_apply = []
    reasons_to_skip = []

    exact_matches = [item for item in accepted_titles if item.lower() in title]
    if exact_matches:
        evidence.append(evidence_item("title", "Accepted target title matches job title.", exact_matches))
        reasons_to_apply.append("Job title matches an accepted target title.")
        return ScorePart(100, evidence, reasons_to_apply, reasons_to_skip)

    title_tokens = set(tokens(" ".join(accepted_titles)))
    job_tokens = set(tokens(job.title))
    overlap = sorted(title_tokens & job_tokens)
    if overlap:
        evidence.append(evidence_item("title", "Job title shares terms with accepted target titles.", overlap))
        reasons_to_apply.append("Job title overlaps with target role language.")
        return ScorePart(clamp(45 + len(overlap) * 12), evidence, reasons_to_apply, reasons_to_skip)

    if not accepted_titles:
        evidence.append(evidence_item("title", "No accepted target titles are available.", []))
        reasons_to_skip.append("Accept target titles in Profile to improve title fit.")
        return ScorePart(45, evidence, reasons_to_apply, reasons_to_skip)

    reasons_to_skip.append("Job title does not match accepted target titles.")
    return ScorePart(25, evidence, reasons_to_apply, reasons_to_skip)


def score_skills(job: Job, profile: CandidateProfile | None) -> tuple[ScorePart, list[str], list[str]]:
    profile_skills = [skill.lower() for skill in (profile.skills if profile else []) if str(skill).strip()]
    text = job_text(job)
    matched_skills = sorted({skill for skill in profile_skills if skill and skill in text})
    known_job_terms = sorted({term for term in TECH_TERMS if term in text})
    missing_skills = [term for term in known_job_terms if term not in profile_skills]
    evidence = []
    reasons_to_apply = []
    reasons_to_skip = []

    if matched_skills:
        evidence.append(evidence_item("skills", "Profile skills found in job text.", matched_skills[:12]))
        reasons_to_apply.append(f"{len(matched_skills)} profile skills appear in the job.")

    if missing_skills:
        evidence.append(evidence_item("gaps", "Known job terms not present in profile skills.", missing_skills[:10]))

    if profile_skills:
        score = clamp(round(len(matched_skills) / max(len(profile_skills), 1) * 100))
        if score < 35:
            reasons_to_skip.append("Few profile skills appear in the job text.")
        return ScorePart(score, evidence, reasons_to_apply, reasons_to_skip), matched_skills, missing_skills

    if known_job_terms:
        reasons_to_skip.append("Profile skills are missing, so skill coverage cannot be trusted.")
        return ScorePart(35, evidence, reasons_to_apply, reasons_to_skip), matched_skills, missing_skills

    return ScorePart(45, evidence, reasons_to_apply, reasons_to_skip), matched_skills, missing_skills


def score_location(job: Job, profile: CandidateProfile | None) -> ScorePart:
    evidence = []
    reasons_to_apply = []
    reasons_to_skip = []
    preferred_modes = set((profile.preferred_work_modes if profile else []) or [])
    remote_preference = (profile.remote_preference if profile else "any") or "any"
    target_locations = [location.lower() for location in ((profile.target_locations if profile else []) or [])]
    location_text = f"{job.location} {job.remote_policy}".lower()

    if remote_preference in {"any", "", job.remote_policy} or job.remote_policy in preferred_modes:
        evidence.append(evidence_item("work_mode", "Work mode fits profile preference.", [job.remote_policy]))
        reasons_to_apply.append("Work mode fits profile preference.")
        mode_score = 100
    elif job.remote_policy == "unknown":
        mode_score = 60
        reasons_to_skip.append("Work mode is unknown.")
    else:
        mode_score = 35
        reasons_to_skip.append("Work mode may not match preference.")

    if target_locations:
        matches = sorted({location for location in target_locations if location and location in location_text})
        if matches:
            evidence.append(evidence_item("location", "Job location matches target locations.", matches))
            location_score = 100
        elif "remote" in location_text and remote_preference in {"any", "remote"}:
            location_score = 85
        else:
            location_score = 45
            reasons_to_skip.append("Location does not match target locations.")
    else:
        location_score = 70

    return ScorePart(round((mode_score + location_score) / 2), evidence, reasons_to_apply, reasons_to_skip)


def score_seniority(job: Job, profile: CandidateProfile | None) -> ScorePart:
    evidence = []
    reasons_to_apply = []
    reasons_to_skip = []
    job_terms = set(tokens(job.title)) & SENIORITY_TERMS
    profile_text = f"{profile.headline if profile else ''} {profile.summary if profile else ''}".lower()
    profile_terms = set(tokens(profile_text)) & SENIORITY_TERMS

    if job_terms and profile_terms:
        overlap = sorted(job_terms & profile_terms)
        if overlap:
            evidence.append(evidence_item("seniority", "Seniority terms overlap with profile.", overlap))
            reasons_to_apply.append("Seniority appears aligned.")
            return ScorePart(100, evidence, reasons_to_apply, reasons_to_skip)
        evidence.append(evidence_item("seniority", "Job and profile seniority terms differ.", sorted(job_terms | profile_terms)))
        reasons_to_skip.append("Seniority may need manual review.")
        return ScorePart(55, evidence, reasons_to_apply, reasons_to_skip)

    if job_terms:
        evidence.append(evidence_item("seniority", "Job seniority term detected.", sorted(job_terms)))
        return ScorePart(70, evidence, reasons_to_apply, reasons_to_skip)

    return ScorePart(75, evidence, reasons_to_apply, reasons_to_skip)


def serialize_job_match(match: JobMatch) -> dict:
    return {
        "id": match.id,
        "job_id": match.job_id,
        "profile_id": match.profile_id,
        "source": match.source,
        "overall_score": match.overall_score,
        "title_score": match.title_score,
        "skill_score": match.skill_score,
        "seniority_score": match.seniority_score,
        "location_score": match.location_score,
        "confidence_score": match.confidence_score,
        "knowledge_coverage_score": match.knowledge_coverage_score,
        "apply_priority": match.apply_priority,
        "reasons_to_apply": match.reasons_to_apply,
        "reasons_to_skip": match.reasons_to_skip,
        "missing_skills": match.missing_skills,
        "evidence": match.evidence,
        "generated_at": match.generated_at.isoformat() if match.generated_at else None,
        "updated_at": match.updated_at.isoformat() if match.updated_at else None,
    }


def current_profile() -> CandidateProfile | None:
    return CandidateProfile.objects.prefetch_related("target_titles", "claims").order_by("id").first()


def accepted_target_titles(profile: CandidateProfile | None) -> list[str]:
    if not profile:
        return []
    return [title.title for title in profile.target_titles.filter(status="accepted")]


def profile_confidence(profile: CandidateProfile | None) -> int:
    if not profile:
        return 20
    score = 25
    if profile.skills:
        score += min(25, len(profile.skills) * 3)
    if accepted_target_titles(profile):
        score += 20
    if profile.summary:
        score += 10
    if profile.cv_markdown or profile.profile_markdown:
        score += 15
    if profile.claims.filter(status="confirmed").exists():
        score += 5
    return clamp(score)


def apply_priority(score: int, confidence: int) -> str:
    if score >= 80 and confidence >= 55:
        return "apply_now"
    if score >= 60:
        return "consider"
    if score >= 45:
        return "stretch"
    return "ignore"


def apply_active_score_correction(job: Job, report: dict) -> dict:
    try:
        from analytics.models import MatchScoreCorrection
    except Exception:
        return report

    correction = (
        MatchScoreCorrection.objects.filter(job=job, learning_change__status="active")
        .select_related("learning_change")
        .order_by("-created_at")
        .first()
    )
    if not correction or correction.correction == "accurate":
        return report

    adjusted = dict(report)
    delta = -15 if correction.correction == "too_high" else 15
    adjusted["overall_score"] = clamp(adjusted["overall_score"] + delta)
    adjusted["apply_priority"] = apply_priority(adjusted["overall_score"], adjusted["confidence_score"])
    evidence = list(adjusted.get("evidence") or [])
    evidence.append(
        evidence_item(
            "user_correction",
            f"User marked prior score as {correction.correction.replace('_', ' ')}.",
            [str(delta)],
        )
    )
    adjusted["evidence"] = evidence[:12]
    return adjusted


def job_text(job: Job) -> str:
    return " ".join(
        [
            job.title,
            job.description,
            job.location,
            job.remote_policy,
            " ".join(job.tags or []),
        ]
    ).lower()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9.+#-]{1,}", text.lower())


def evidence_item(kind: str, message: str, values: list[str]) -> dict:
    return {"kind": kind, "message": message, "values": values}


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def clamp(value: int) -> int:
    return max(0, min(100, int(value)))
