import re

from django.db import IntegrityError, transaction
from django.utils import timezone

from companies.models import Company
from companies.services import coerce_keyword_list
from profiles.models import CandidateProfile, ProfileClaim, SearchStrategy, TargetTitle


TECH_TERMS = {
    "python",
    "django",
    "fastapi",
    "flask",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "node",
    "node.js",
    "java",
    "spring",
    "go",
    "golang",
    "rust",
    "sql",
    "postgres",
    "postgresql",
    "mysql",
    "redis",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "terraform",
    "graphql",
    "machine learning",
    "ml",
    "ai",
    "data",
    "spark",
    "airflow",
}

TITLE_RULES = [
    ("Backend Engineer", {"python", "django", "fastapi", "node", "java", "spring", "go", "sql"}),
    ("Python Developer", {"python", "django", "fastapi", "flask"}),
    ("Full Stack Engineer", {"react", "typescript", "javascript", "node", "python", "django"}),
    ("Frontend Engineer", {"react", "typescript", "javascript", "next.js"}),
    ("React Developer", {"react", "typescript", "javascript"}),
    ("Platform Engineer", {"docker", "kubernetes", "terraform", "aws", "gcp", "azure"}),
    ("DevOps Engineer", {"docker", "kubernetes", "terraform", "aws", "gcp", "azure"}),
    ("Data Engineer", {"data", "sql", "postgres", "postgresql", "spark", "airflow", "python"}),
    ("Machine Learning Engineer", {"machine learning", "ml", "ai", "python", "data"}),
]

ROLE_FAMILY_RULES = {
    "backend": ("backend", "python", "django", "fastapi", "java", "spring", "go", "api"),
    "frontend": ("frontend", "react", "next.js", "typescript", "javascript", "ui"),
    "full_stack": ("full stack", "full-stack", "react", "node", "django", "typescript"),
    "platform": ("platform", "devops", "docker", "kubernetes", "terraform", "aws", "gcp", "azure"),
    "data": ("data", "sql", "spark", "airflow", "pipeline", "analytics"),
    "ml": ("machine learning", "ml", "ai", "model", "python"),
}

DEFAULT_NEGATIVE_KEYWORDS = ("intern", "unpaid", "volunteer", "founder", "co-founder")

PROFILE_UPDATE_FIELDS = (
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


def get_profile() -> CandidateProfile:
    profile = CandidateProfile.objects.filter(pk=1).first() or CandidateProfile.objects.order_by("id").first()
    if profile:
        return profile
    try:
        return CandidateProfile.objects.create(pk=1)
    except IntegrityError:
        return CandidateProfile.objects.get(pk=1)


def update_profile(profile: CandidateProfile, updates: dict) -> CandidateProfile:
    update_fields = []
    for field in PROFILE_UPDATE_FIELDS:
        if field not in updates:
            continue
        value = normalize_profile_value(field, updates[field])
        if getattr(profile, field) != value:
            setattr(profile, field, value)
            update_fields.append(field)

    if update_fields:
        profile.save(update_fields=[*update_fields, "updated_at"])
    return refresh_profile_completeness(profile)


@transaction.atomic
def import_resume(profile: CandidateProfile, raw_text: str) -> CandidateProfile:
    raw_text = str(raw_text or "").strip()
    if not raw_text:
        raise ValueError("resume_text is required")
    if len(raw_text) > 120_000:
        raise ValueError("resume_text is too large")

    cv_markdown = resume_to_markdown(raw_text)
    skills = sorted(set(profile.skills) | set(extract_skills(raw_text)), key=str.lower)
    summary = profile.summary or first_nonempty_line(raw_text)
    profile_markdown = build_profile_markdown(profile, summary, skills, raw_text)
    proof_points = merge_profile_items(profile.proof_points, build_proof_points(raw_text), "text")
    skill_inventory = build_skill_inventory(skills, raw_text)
    career_timeline = merge_profile_items(profile.career_timeline, build_career_timeline(raw_text), "label")

    profile.cv_markdown = cv_markdown
    profile.profile_markdown = profile_markdown
    profile.proof_points = proof_points
    profile.skill_inventory = skill_inventory
    profile.career_timeline = career_timeline
    profile.skills = skills
    profile.summary = summary[:5000]
    profile.profile_yml = build_profile_yml(profile)
    profile.profile_completeness_score = compute_profile_completeness(profile)
    profile.last_generated_at = timezone.now()
    profile.save(
        update_fields=[
            "cv_markdown",
            "profile_markdown",
            "profile_yml",
            "proof_points",
            "skill_inventory",
            "career_timeline",
            "skills",
            "summary",
            "profile_completeness_score",
            "last_generated_at",
            "updated_at",
        ]
    )

    generate_claims(profile, raw_text, skills)
    generate_target_titles(profile, raw_text, skills)
    return refresh_profile_completeness(profile)


def generate_target_titles(profile: CandidateProfile, raw_text: str = "", skills: list[str] | None = None) -> list[TargetTitle]:
    skills = skills or profile.skills
    skill_set = {skill.casefold() for skill in skills}
    text = f"{raw_text}\n{profile.cv_markdown}\n{profile.profile_markdown}\n{' '.join(profile.skills)}".casefold()
    created_titles = []

    for title, required in TITLE_RULES:
        evidence = sorted(term for term in required if term in skill_set or term_in_text(term, text))
        if not evidence:
            continue
        knowledge_accuracy = round((len(evidence) / len(required)) * 100)
        confidence = min(95, 35 + len(evidence) * 10)
        fit_bucket = "core" if knowledge_accuracy >= 60 else "adjacent" if knowledge_accuracy >= 35 else "stretch"
        target_title, created = TargetTitle.objects.get_or_create(
            profile=profile,
            title=title,
            defaults={
                "fit_bucket": fit_bucket,
                "confidence_score": confidence,
                "knowledge_accuracy": knowledge_accuracy,
                "evidence": evidence,
            },
        )
        if not created and target_title.status == "suggested":
            target_title.fit_bucket = fit_bucket
            target_title.confidence_score = confidence
            target_title.knowledge_accuracy = knowledge_accuracy
            target_title.evidence = evidence
            target_title.save(update_fields=["fit_bucket", "confidence_score", "knowledge_accuracy", "evidence", "updated_at"])
        created_titles.append(target_title)

    if not created_titles and profile.headline:
        target_title, _ = TargetTitle.objects.get_or_create(
            profile=profile,
            title=profile.headline[:180],
            defaults={
                "fit_bucket": "stretch",
                "confidence_score": 40,
                "knowledge_accuracy": 30,
                "evidence": ["headline"],
            },
        )
        created_titles.append(target_title)
    return created_titles


def generate_claims(profile: CandidateProfile, raw_text: str, skills: list[str]) -> list[ProfileClaim]:
    claims = []
    for skill in skills[:30]:
        claim, _ = ProfileClaim.objects.get_or_create(
            profile=profile,
            text=f"Has experience with {skill}.",
            defaults={"claim_type": "skill", "evidence": skill, "status": "unconfirmed"},
        )
        claims.append(claim)

    for line in notable_resume_lines(raw_text):
        claim_type = classify_claim(line)
        claim, _ = ProfileClaim.objects.get_or_create(
            profile=profile,
            text=line[:1000],
            defaults={"claim_type": claim_type, "evidence": line[:1000], "status": "unconfirmed"},
        )
        claims.append(claim)
    return claims


def set_target_title_status(target_title: TargetTitle, status: str) -> TargetTitle:
    if status not in {choice[0] for choice in TargetTitle.STATUS_CHOICES}:
        raise ValueError("Invalid target title status")
    target_title.status = status
    target_title.save(update_fields=["status", "updated_at"])
    return target_title


def set_claim_status(claim: ProfileClaim, status: str) -> ProfileClaim:
    if status not in {choice[0] for choice in ProfileClaim.STATUS_CHOICES}:
        raise ValueError("Invalid claim status")
    claim.status = status
    claim.save(update_fields=["status", "updated_at"])
    return claim


def apply_accepted_titles_to_company_filters(profile: CandidateProfile) -> dict:
    accepted_titles = list(profile.target_titles.filter(status="accepted").values_list("title", flat=True))
    if not accepted_titles:
        raise ValueError("Accept at least one target title before applying filters")

    updated = []
    for company in Company.objects.filter(is_active=True).order_by("name"):
        current = coerce_keyword_list(company.title_keywords, "title_keywords")
        merged = []
        seen = set()
        for keyword in [*current, *accepted_titles]:
            key = keyword.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(keyword)
        if merged != current:
            company.title_keywords = merged
            company.save(update_fields=["title_keywords", "updated_at"])
            updated.append(company)

    return {"updated_count": len(updated), "titles": accepted_titles, "companies": updated}


def get_search_strategy(profile: CandidateProfile) -> SearchStrategy:
    strategy, _ = SearchStrategy.objects.get_or_create(profile=profile)
    return strategy


def update_search_strategy(strategy: SearchStrategy, updates: dict) -> SearchStrategy:
    fields = (
        "role_families",
        "target_title_keywords",
        "negative_keywords",
        "seniority_levels",
        "location_keywords",
        "work_mode_preferences",
        "notes",
    )
    update_fields = []
    for field in fields:
        if field not in updates:
            continue
        value = str(updates[field] or "").strip() if field == "notes" else coerce_keyword_list(updates[field], field)
        if getattr(strategy, field) != value:
            setattr(strategy, field, value)
            update_fields.append(field)
    if update_fields:
        strategy.save(update_fields=[*update_fields, "updated_at"])
    return strategy


def generate_search_strategy(profile: CandidateProfile) -> SearchStrategy:
    strategy = get_search_strategy(profile)
    title_queryset = profile.target_titles.exclude(status="rejected").order_by("status", "-confidence_score")
    titles = [title.title for title in title_queryset[:12]]
    if not titles and profile.headline:
        titles = [profile.headline]

    skills = profile.skills[:24]
    role_families = infer_role_families([*titles, *skills, profile.summary, profile.role_framing])
    seniority_levels = infer_seniority_levels([*titles, profile.headline, profile.summary])
    target_keywords = dedupe_keywords([*titles, *skills[:12]])
    negative_keywords = list(DEFAULT_NEGATIVE_KEYWORDS)
    location_keywords = dedupe_keywords([*profile.target_locations, profile.location])
    work_modes = dedupe_keywords([*profile.preferred_work_modes, profile.remote_preference])
    work_modes = [mode for mode in work_modes if mode and mode != "any"]

    strategy.role_families = role_families
    strategy.target_title_keywords = target_keywords
    strategy.negative_keywords = negative_keywords
    strategy.seniority_levels = seniority_levels
    strategy.location_keywords = location_keywords
    strategy.work_mode_preferences = work_modes
    strategy.generated_from = "deterministic_profile"
    strategy.notes = build_search_strategy_notes(strategy, profile)
    strategy.last_generated_at = timezone.now()
    strategy.save(
        update_fields=[
            "role_families",
            "target_title_keywords",
            "negative_keywords",
            "seniority_levels",
            "location_keywords",
            "work_mode_preferences",
            "generated_from",
            "notes",
            "last_generated_at",
            "updated_at",
        ]
    )
    return strategy


def apply_search_strategy_to_company_filters(profile: CandidateProfile) -> dict:
    strategy = get_search_strategy(profile)
    if not strategy.target_title_keywords:
        strategy = generate_search_strategy(profile)

    updated = []
    for company in Company.objects.filter(is_active=True).order_by("name"):
        changed = []
        merged_titles = merge_keywords(company.title_keywords, strategy.target_title_keywords)
        if merged_titles != company.title_keywords:
            company.title_keywords = merged_titles
            changed.append("title_keywords")

        merged_negative = merge_keywords(company.negative_title_keywords, strategy.negative_keywords)
        if merged_negative != company.negative_title_keywords:
            company.negative_title_keywords = merged_negative
            changed.append("negative_title_keywords")

        merged_locations = merge_keywords(company.location_keywords, strategy.location_keywords)
        if merged_locations != company.location_keywords:
            company.location_keywords = merged_locations
            changed.append("location_keywords")

        if company.work_mode_filter == "any" and strategy.work_mode_preferences:
            preferred = strategy.work_mode_preferences[0]
            if preferred in {"remote", "hybrid", "onsite"}:
                company.work_mode_filter = preferred
                changed.append("work_mode_filter")

        if changed:
            company.save(update_fields=[*changed, "updated_at"])
            updated.append(company)

    strategy.applied_at = timezone.now()
    strategy.save(update_fields=["applied_at", "updated_at"])
    return {"updated_count": len(updated), "companies": updated, "strategy": strategy}


def normalize_profile_value(field: str, value):
    if field in {"target_locations", "preferred_work_modes", "skills"}:
        return coerce_keyword_list(value, field)
    if field in {"proof_points", "skill_inventory", "career_timeline"}:
        return normalize_profile_items(value, field)
    if field == "links":
        if not value:
            return {}
        if isinstance(value, dict):
            return {str(key).strip(): str(item).strip() for key, item in value.items() if str(item).strip()}
        raise ValueError("links must be an object")
    if field == "remote_preference":
        normalized = str(value or "any").strip().lower()
        allowed = {choice[0] for choice in CandidateProfile.REMOTE_CHOICES}
        if normalized not in allowed:
            raise ValueError(f"remote_preference must be one of: {', '.join(sorted(allowed))}")
        return normalized
    return str(value or "").strip()


def infer_role_families(values: list[str]) -> list[str]:
    text = " ".join(str(value or "") for value in values).casefold()
    families = []
    for family, signals in ROLE_FAMILY_RULES.items():
        if any(signal in text for signal in signals):
            families.append(family)
    return families or ["software_engineering"]


def infer_seniority_levels(values: list[str]) -> list[str]:
    text = " ".join(str(value or "") for value in values).casefold()
    levels = []
    if any(term in text for term in ("staff", "principal", "lead")):
        levels.append("senior_plus")
    if any(term in text for term in ("senior", "sr.", "sr ")):
        levels.append("senior")
    if any(term in text for term in ("junior", "entry", "graduate", "fresher")):
        levels.append("junior")
    return levels or ["mid", "senior"]


def dedupe_keywords(values: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for value in values:
        keyword = str(value or "").strip()
        if not keyword:
            continue
        marker = keyword.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(keyword)
    return deduped


def merge_keywords(current: list[str], additions: list[str]) -> list[str]:
    return dedupe_keywords([*(current or []), *(additions or [])])


def build_search_strategy_notes(strategy: SearchStrategy, profile: CandidateProfile) -> str:
    parts = []
    if strategy.role_families:
        parts.append(f"Role families: {', '.join(strategy.role_families)}.")
    if strategy.target_title_keywords:
        parts.append(f"Use {len(strategy.target_title_keywords)} title/skill keywords from accepted titles and profile skills.")
    if strategy.negative_keywords:
        parts.append("Exclude obvious low-signal or misaligned postings before they reach the daily queue.")
    if profile.profile_completeness_score < 60:
        parts.append("Improve profile completeness before relying heavily on automated ranking.")
    return " ".join(parts)


def refresh_profile_completeness(profile: CandidateProfile) -> CandidateProfile:
    score = compute_profile_completeness(profile)
    if profile.profile_completeness_score != score:
        profile.profile_completeness_score = score
        profile.save(update_fields=["profile_completeness_score", "updated_at"])
    return profile


def compute_profile_completeness(profile: CandidateProfile) -> int:
    score = 0
    if profile.full_name:
        score += 5
    if profile.headline:
        score += 5
    if profile.location:
        score += 5
    if len(profile.summary) >= 80:
        score += 15
    elif profile.summary:
        score += 8
    if len(profile.skills) >= 6:
        score += 15
    elif len(profile.skills) >= 3:
        score += 10
    elif profile.skills:
        score += 5
    if profile.target_locations or profile.preferred_work_modes or profile.remote_preference != "any":
        score += 10
    if profile.cv_markdown:
        score += 5
    if profile.profile_markdown:
        score += 5
    if profile.profile_yml:
        score += 5
    if len(profile.proof_points) >= 5:
        score += 15
    elif profile.proof_points:
        score += 8
    if profile.target_titles.filter(status__in=["accepted", "suggested"]).exists():
        score += 10
    if profile.links:
        score += 5
    return min(score, 100)


def normalize_profile_items(value, field_name: str) -> list[dict]:
    if not value:
        return []
    if isinstance(value, str):
        return [{"text": line.strip()} for line in value.splitlines() if line.strip()]
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    normalized = []
    for item in value[:100]:
        if isinstance(item, dict):
            clean_item = {str(key).strip(): primitive_profile_value(val) for key, val in item.items() if str(key).strip()}
            if clean_item:
                normalized.append(clean_item)
        elif str(item).strip():
            normalized.append({"text": str(item).strip()})
    return normalized


def primitive_profile_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [primitive_profile_value(item) for item in value[:20]]
    if isinstance(value, dict):
        return {str(key): primitive_profile_value(item) for key, item in value.items()}
    return str(value)


def build_proof_points(raw_text: str) -> list[dict]:
    points = []
    for line in notable_resume_lines(raw_text)[:20]:
        points.append(
            {
                "text": line,
                "category": classify_claim(line),
                "evidence": extract_metric(line),
                "source": "resume_import",
            }
        )
    return points


def build_skill_inventory(skills: list[str], raw_text: str) -> list[dict]:
    inventory = []
    lowered = raw_text.casefold()
    for skill in skills[:60]:
        mentions = len(re.findall(rf"(?<!\w){re.escape(skill.casefold())}(?!\w)", lowered))
        confidence = min(95, 55 + mentions * 10)
        inventory.append(
            {
                "skill": skill,
                "confidence": confidence,
                "source": "resume_import" if mentions else "manual",
                "evidence": f"{mentions} resume mention{'s' if mentions != 1 else ''}" if mentions else "",
            }
        )
    return inventory


def build_career_timeline(raw_text: str) -> list[dict]:
    timeline = []
    for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip().lstrip("-*• ").strip()
        if not stripped:
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", stripped)
        if not years:
            continue
        timeline.append({"label": stripped[:240], "years": years[:2], "source": "resume_import"})
        if len(timeline) >= 20:
            break
    return timeline


def merge_profile_items(existing: list[dict], generated: list[dict], key: str) -> list[dict]:
    merged = []
    seen = set()
    for item in [*(existing or []), *generated]:
        if not isinstance(item, dict):
            continue
        marker = str(item.get(key) or item.get("text") or item).casefold()
        if marker in seen:
            continue
        seen.add(marker)
        merged.append(item)
    return merged[:100]


def build_profile_yml(profile: CandidateProfile) -> str:
    lines = [
        "profile:",
        f"  name: {yaml_scalar(profile.full_name)}",
        f"  headline: {yaml_scalar(profile.headline)}",
        f"  location: {yaml_scalar(profile.location)}",
        f"  remote_preference: {yaml_scalar(profile.remote_preference)}",
        "  target_locations:",
    ]
    lines.extend(f"    - {yaml_scalar(location)}" for location in profile.target_locations)
    lines.extend(["  preferred_work_modes:"])
    lines.extend(f"    - {yaml_scalar(mode)}" for mode in profile.preferred_work_modes)
    lines.extend(["  skills:"])
    lines.extend(f"    - {yaml_scalar(skill)}" for skill in profile.skills)
    lines.extend(["  links:"])
    for key, value in profile.links.items():
        lines.append(f"    {yaml_key(key)}: {yaml_scalar(value)}")
    lines.extend(["proof_points:"])
    for point in profile.proof_points[:20]:
        lines.append(f"  - text: {yaml_scalar(point.get('text', ''))}")
        if point.get("category"):
            lines.append(f"    category: {yaml_scalar(point.get('category'))}")
        if point.get("evidence"):
            lines.append(f"    evidence: {yaml_scalar(point.get('evidence'))}")
    lines.extend(["skill_inventory:"])
    for item in profile.skill_inventory[:60]:
        lines.append(f"  - skill: {yaml_scalar(item.get('skill', ''))}")
        lines.append(f"    confidence: {int(item.get('confidence') or 0)}")
        if item.get("evidence"):
            lines.append(f"    evidence: {yaml_scalar(item.get('evidence'))}")
    if profile.role_framing:
        lines.extend(["role_framing: |"])
        lines.extend(f"  {line}" for line in profile.role_framing.splitlines())
    return "\n".join(lines).strip() + "\n"


def yaml_scalar(value) -> str:
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def yaml_key(value) -> str:
    key = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_").lower()
    return key or "link"


def extract_metric(line: str) -> str:
    metrics = re.findall(r"(?:\d+(?:\.\d+)?%|\b\d+[xk+]?\b)", line)
    return ", ".join(metrics[:3])


def resume_to_markdown(raw_text: str) -> str:
    lines = [line.rstrip() for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    cleaned = [line for line in lines if line.strip()]
    if any(line.lstrip().startswith("#") for line in cleaned):
        return "\n".join(cleaned)

    markdown = ["# CV", ""]
    for line in cleaned:
        stripped = line.strip()
        if looks_like_heading(stripped):
            markdown.extend(["", f"## {stripped.title()}", ""])
        elif stripped.startswith(("-", "*", "•")):
            markdown.append(f"- {stripped.lstrip('-*• ').strip()}")
        else:
            markdown.append(stripped)
    return "\n".join(markdown).strip()


def build_profile_markdown(profile: CandidateProfile, summary: str, skills: list[str], raw_text: str) -> str:
    sections = ["# Developer Profile", ""]
    if profile.full_name:
        sections.extend([f"## Identity", "", f"- Name: {profile.full_name}"])
    if profile.headline:
        sections.append(f"- Headline: {profile.headline}")
    if profile.location:
        sections.append(f"- Location: {profile.location}")
    sections.extend(["", "## Summary", "", summary or first_nonempty_line(raw_text) or ""])
    if skills:
        sections.extend(["", "## Skills", "", ", ".join(skills)])
    proof_points = notable_resume_lines(raw_text)[:8]
    if proof_points:
        sections.extend(["", "## Proof Points", ""])
        sections.extend(f"- {line}" for line in proof_points)
    return "\n".join(sections).strip()


def extract_skills(text: str) -> list[str]:
    lowered = text.casefold()
    found = []
    for term in sorted(TECH_TERMS):
        if re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", lowered):
            found.append(term)
    return found


def term_in_text(term: str, text: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text))


def notable_resume_lines(text: str) -> list[str]:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip().lstrip("-*• ").strip()
        if len(stripped) < 24:
            continue
        if any(signal in stripped.casefold() for signal in ("built", "led", "created", "designed", "improved", "reduced", "increased", "shipped", "owned", "%")):
            lines.append(stripped)
        if len(lines) >= 20:
            break
    return lines


def classify_claim(line: str) -> str:
    lowered = line.casefold()
    if "%" in line or re.search(r"\b\d+[xk]?\b", lowered):
        return "metric"
    if "project" in lowered or "built" in lowered or "created" in lowered:
        return "project"
    if "led" in lowered or "owned" in lowered or "designed" in lowered:
        return "experience"
    return "other"


def looks_like_heading(line: str) -> bool:
    if len(line) > 60:
        return False
    lowered = line.casefold().strip(":")
    return lowered in {
        "summary",
        "experience",
        "work experience",
        "projects",
        "skills",
        "education",
        "certifications",
        "achievements",
    }


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:500]
    return ""
