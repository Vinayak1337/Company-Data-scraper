from applications.models import Application
from interviews.models import InterviewPrep, OfferSupport
from matching.services import refresh_job_match, serialize_job_match
from profiles.services import get_profile


def generate_interview_prep(application: Application) -> InterviewPrep:
    profile = get_profile()
    match = serialize_job_match(refresh_job_match(application.job, profile=profile))
    matched_skills = matched_skill_values(match)
    gaps = match.get("missing_skills", [])[:8]
    proof_points = [item.get("text", "") for item in profile.proof_points[:8] if isinstance(item, dict)]
    focus_areas = matched_skills[:8] or profile.skills[:8] or [application.job.title]
    question_bank = [
        {"question": f"Explain your experience with {skill}.", "focus": skill}
        for skill in focus_areas[:8]
    ]
    question_bank.extend(
        {"question": f"How would you handle a gap around {gap}?", "focus": gap}
        for gap in gaps[:5]
    )
    story_bank = [{"prompt": "Use this proof point if relevant.", "story": point} for point in proof_points[:6]]
    checklist = [
        {"item": "Confirm interview format and stage with recruiter.", "done": False},
        {"item": "Map each required skill to one proof point.", "done": False},
        {"item": "Prepare questions for hiring manager and team.", "done": False},
        {"item": "Write down gaps and mitigation language.", "done": False},
    ]
    notes = f"Prepare for {application.job.title} at {application.job.company.name}. Match score: {match.get('overall_score', 0)}/100."

    prep, _ = InterviewPrep.objects.update_or_create(
        application=application,
        defaults={
            "stage": infer_interview_stage(application),
            "checklist": checklist,
            "focus_areas": focus_areas,
            "question_bank": question_bank,
            "story_bank": story_bank,
            "gaps": gaps,
            "notes": notes,
            "generated_by": "deterministic",
        },
    )
    return prep


def generate_offer_support(application: Application) -> OfferSupport:
    profile = get_profile()
    criteria = [
        {"criterion": "Role fit", "note": application.job.title},
        {"criterion": "Company priority", "note": application.job.company.priority_tier},
        {"criterion": "Work mode", "note": application.job.remote_policy},
    ]
    if profile.dealbreakers:
        criteria.append({"criterion": "Dealbreakers", "note": profile.dealbreakers[:500]})
    if profile.compensation_expectation:
        criteria.append({"criterion": "Compensation", "note": profile.compensation_expectation})

    negotiation_points = [
        {"point": "Scope and level", "note": "Confirm title, responsibilities, and growth path."},
        {"point": "Compensation mix", "note": "Compare salary, equity, bonus, and benefits together."},
        {"point": "Start date and flexibility", "note": "Clarify constraints before accepting."},
    ]
    risk_flags = []
    if application.job.company.source_health in {"degraded", "failing", "blocked"}:
        risk_flags.append({"risk": "source_health", "note": f"Company source health is {application.job.company.source_health}."})
    if application.status == "rejected":
        risk_flags.append({"risk": "pipeline_status", "note": "Application is currently rejected."})

    support, _ = OfferSupport.objects.update_or_create(
        application=application,
        defaults={
            "offer_stage": "manual_review",
            "equity_notes": "Add equity, vesting, and refresh details manually if an offer arrives.",
            "benefits_notes": "Add health, leave, remote-work, relocation, and learning budget details manually.",
            "manual_research": [
                {
                    "source": "user_input_required",
                    "note": "Compensation support is manual-first; add source-labeled research before comparing offers.",
                }
            ],
            "decision_criteria": criteria,
            "negotiation_points": negotiation_points,
            "compensation_notes": profile.compensation_expectation,
            "risk_flags": risk_flags,
            "generated_by": "deterministic",
        },
    )
    return support


def infer_interview_stage(application: Application) -> str:
    if application.status == "offer":
        return "final"
    if application.status == "interviewing":
        return "technical"
    if application.status in {"applied", "applying"}:
        return "screen"
    return "unknown"


def matched_skill_values(match_payload: dict) -> list[str]:
    values = []
    for evidence in match_payload.get("evidence", []):
        if evidence.get("kind") == "skills":
            values.extend(evidence.get("values", []))
    return values[:12]
