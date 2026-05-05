from __future__ import annotations

import re
from dataclasses import dataclass

from django.utils import timezone

from jobs.models import Job
from matching.models import JobMatch, MatchFeedback
from profiles.models import CandidateProfile, UserSearchPreference


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
            "source": "weighted",
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
    preference = get_search_preferences(profile)
    weights = preference_weights(preference)
    title_part = score_title(job, profile)
    skill_part, matched_skills, missing_skills = score_skills(job, profile)
    location_part = score_location(job, profile)
    seniority_part = score_seniority(job, profile)
    dealbreaker_part = score_dealbreakers(job, profile, preference)
    confidence_score = profile_confidence(profile, job)
    overall_score = clamp(
        round(
            title_part.score * weights["title"]
            + skill_part.score * weights["skill"]
            + location_part.score * weights["location"]
            + seniority_part.score * weights["seniority"]
            + dealbreaker_part.score * weights["dealbreaker"]
        )
    )

    evidence = title_part.evidence + skill_part.evidence + location_part.evidence + seniority_part.evidence + dealbreaker_part.evidence
    reasons_to_apply = dedupe(
        title_part.reasons_to_apply
        + skill_part.reasons_to_apply
        + location_part.reasons_to_apply
        + seniority_part.reasons_to_apply
        + dealbreaker_part.reasons_to_apply
    )
    reasons_to_skip = dedupe(
        title_part.reasons_to_skip
        + skill_part.reasons_to_skip
        + location_part.reasons_to_skip
        + seniority_part.reasons_to_skip
        + dealbreaker_part.reasons_to_skip
    )
    if not profile:
        reasons_to_skip.append("No profile is available, so score confidence is limited.")
    threshold = notification_threshold(preference, job, overall_score, confidence_score)
    should_notify = bool(
        preference
        and overall_score >= max(preference.minimum_match_score, threshold)
        and confidence_score >= preference.minimum_confidence_score
        and job.status not in {"dismissed", "closed", "stale"}
    )

    report = {
        "overall_score": overall_score,
        "title_score": title_part.score,
        "skill_score": skill_part.score,
        "seniority_score": seniority_part.score,
        "location_score": location_part.score,
        "confidence_score": confidence_score,
        "knowledge_coverage_score": skill_part.score,
        "notification_threshold": threshold,
        "should_notify": should_notify,
        "feature_snapshot": {
            "weights": weights,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "profile_preference_id": preference.id if preference else None,
            "profile_strictness": preference.match_strictness if preference else "unknown",
            "source_confidence": getattr(job.company, "source_discovery_confidence", 0),
        },
        "agent_summary": agentic_match_summary(overall_score, confidence_score, should_notify, reasons_to_apply, reasons_to_skip),
        "agent_review_status": "local_reviewed",
        "model_version": "weighted-v1",
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


def score_dealbreakers(job: Job, profile: CandidateProfile | None, preference: UserSearchPreference | None) -> ScorePart:
    text = job_text(job)
    dealbreakers = tokens(profile.dealbreakers if profile else "")
    excluded = [str(item).lower().strip() for item in (preference.excluded_keywords if preference else []) if str(item).strip()]
    hits = sorted({term for term in excluded if term and term in text})
    if not hits and dealbreakers:
        hits = sorted({term for term in dealbreakers if len(term) > 3 and term in text})[:8]
    if hits:
        return ScorePart(
            10,
            [evidence_item("dealbreaker", "Job text contains excluded or dealbreaker terms.", hits)],
            [],
            ["Job appears to hit excluded keywords or dealbreakers."],
        )
    return ScorePart(100, [], ["No dealbreaker terms were detected."], [])


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
        "notification_threshold": match.notification_threshold,
        "should_notify": match.should_notify,
        "feature_snapshot": match.feature_snapshot,
        "agent_summary": match.agent_summary,
        "agent_review_status": match.agent_review_status,
        "model_version": match.model_version,
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


def get_search_preferences(profile: CandidateProfile | None) -> UserSearchPreference | None:
    if not profile:
        return None
    preference, _ = UserSearchPreference.objects.get_or_create(profile=profile)
    return preference


def profile_confidence(profile: CandidateProfile | None, job: Job | None = None) -> int:
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
    source_confidence = getattr(job.company, "source_discovery_confidence", 0) if job else 0
    if source_confidence >= 85:
        score += 5
    elif source_confidence and source_confidence < 60:
        score -= 10
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
    feedback = job.match_feedback.order_by("-created_at").first()
    if not feedback:
        return report
    adjusted = dict(report)
    delta = feedback_delta(feedback.feedback_type)
    if not delta:
        return report
    adjusted["overall_score"] = clamp(adjusted["overall_score"] + delta)
    adjusted["apply_priority"] = apply_priority(adjusted["overall_score"], adjusted["confidence_score"])
    adjusted["should_notify"] = adjusted["overall_score"] >= adjusted["notification_threshold"]
    evidence = list(adjusted.get("evidence") or [])
    evidence.append(
        evidence_item(
            "feedback_adjustment",
            f"Recent feedback adjusted score for {feedback.feedback_type.replace('_', ' ')}.",
            [str(delta)],
        )
    )
    adjusted["evidence"] = evidence[:12]
    return adjusted


def record_match_feedback(job: Job, feedback_type: str, notes: str = "", profile: CandidateProfile | None = None) -> MatchFeedback:
    profile = profile if profile is not None else current_profile()
    match = refresh_job_match(job, profile=profile)
    if feedback_type not in {choice[0] for choice in MatchFeedback.FEEDBACK_CHOICES}:
        raise ValueError("Unsupported feedback_type")
    feedback = MatchFeedback.objects.create(
        job=job,
        match=match,
        profile=profile,
        feedback_type=feedback_type,
        notes=notes[:2000],
    )
    apply_feedback_to_preferences(feedback)
    refresh_job_match(job, profile=profile)
    return feedback


def apply_feedback_to_preferences(feedback: MatchFeedback) -> None:
    preference = get_search_preferences(feedback.profile)
    if not preference:
        return
    weights = dict(preference.feedback_weights or {})
    weights[feedback.feedback_type] = int(weights.get(feedback.feedback_type, 0)) + 1
    if feedback.feedback_type == "too_many_notifications":
        preference.minimum_match_score = clamp(preference.minimum_match_score + 5)
    elif feedback.feedback_type == "want_more_matches":
        preference.minimum_match_score = max(40, preference.minimum_match_score - 5)
    elif feedback.feedback_type in {"wrong_role", "bad_match"}:
        preference.match_strictness = "strict"
    preference.feedback_weights = weights
    preference.save(update_fields=["minimum_match_score", "match_strictness", "feedback_weights", "updated_at"])


def preference_weights(preference: UserSearchPreference | None) -> dict[str, float]:
    strictness = preference.match_strictness if preference else "balanced"
    if strictness == "strict":
        return {"title": 0.32, "skill": 0.28, "location": 0.18, "seniority": 0.12, "dealbreaker": 0.10}
    if strictness == "loose":
        return {"title": 0.25, "skill": 0.25, "location": 0.20, "seniority": 0.15, "dealbreaker": 0.15}
    return {"title": 0.30, "skill": 0.28, "location": 0.18, "seniority": 0.14, "dealbreaker": 0.10}


def notification_threshold(preference: UserSearchPreference | None, job: Job, score: int, confidence: int) -> int:
    base = preference.minimum_match_score if preference else 80
    if confidence < 45:
        return min(95, base + 10)
    if getattr(job.company, "source_discovery_confidence", 0) < 60:
        return min(95, base + 5)
    if score >= 90 and confidence >= 75:
        return max(50, base - 5)
    return base


def agentic_match_summary(score: int, confidence: int, should_notify: bool, reasons_to_apply: list[str], reasons_to_skip: list[str]) -> str:
    decision = "notify" if should_notify else "hold"
    leading_reason = (reasons_to_apply or reasons_to_skip or ["Evidence is limited."])[0]
    return f"Local match agent recommends {decision}: score {score}, confidence {confidence}. {leading_reason}"


def feedback_delta(feedback_type: str) -> int:
    if feedback_type in {"good_match", "want_more_matches"}:
        return 8
    if feedback_type in {"bad_match", "wrong_role", "wrong_location", "too_senior", "too_junior", "not_interested_company"}:
        return -15
    if feedback_type == "too_many_notifications":
        return -10
    return 0


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
