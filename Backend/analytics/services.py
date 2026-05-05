from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

from analytics.models import AlertFeedback, LearningChange, MatchScoreCorrection, WeeklyReview
from applications.models import Application
from companies.models import Company, JobAlert, ScanJob
from jobs.models import Job
from matching.models import JobMatch
from profiles.services import get_profile, get_search_strategy


RATINGS = {"relevant", "maybe", "irrelevant"}


def record_alert_feedback(alert: JobAlert, rating: str, reason: str = "", tags=None) -> AlertFeedback:
    rating = str(rating or "").strip().lower()
    if rating not in RATINGS:
        raise ValueError("rating must be one of: irrelevant, maybe, relevant")

    feedback, _ = AlertFeedback.objects.update_or_create(
        alert=alert,
        defaults={
            "job": alert.job,
            "company": alert.company,
            "rating": rating,
            "reason": str(reason or "").strip()[:2000],
            "tags": normalize_tags(tags),
        },
    )
    return feedback


def analytics_overview(limit: int = 12) -> dict:
    companies = list(
        Company.objects.prefetch_related(
            "scan_jobs",
            "job_alerts",
            "alert_feedback",
            "jobs",
        ).order_by("name")
    )
    company_metrics = [company_quality(company) for company in companies]
    platform_metrics = platform_quality(company_metrics)
    feedback_counts = feedback_distribution(AlertFeedback.objects.all())
    suggestions = build_filter_suggestions(company_metrics)
    noisy_signals = build_noisy_signals(company_metrics)
    inbox = feedback_inbox(limit)

    return {
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "companies_tracked": len(companies),
            "sources_active": sum(1 for metric in company_metrics if metric["source_health"] == "active"),
            "sources_failing": sum(1 for metric in company_metrics if metric["source_health"] in {"failing", "blocked"}),
            "alerts_total": sum(metric["alerts_total"] for metric in company_metrics),
            "feedback_total": sum(metric["feedback_total"] for metric in company_metrics),
            "feedback_relevant": feedback_counts["relevant"],
            "feedback_maybe": feedback_counts["maybe"],
            "feedback_irrelevant": feedback_counts["irrelevant"],
            "suggestions_total": len(suggestions),
        },
        "company_metrics": company_metrics,
        "platform_metrics": platform_metrics,
        "feedback_inbox": inbox,
        "noisy_signals": noisy_signals,
        "filter_suggestions": suggestions,
        "recent_feedback": [serialize_alert_feedback(feedback) for feedback in recent_feedback(limit)],
        "latest_weekly_review": serialize_weekly_review(WeeklyReview.objects.first()) if WeeklyReview.objects.exists() else None,
        "learning_changes": [serialize_learning_change(change) for change in LearningChange.objects.all()[:limit]],
    }


def record_match_score_correction(job: Job, correction: str, reason: str = "") -> MatchScoreCorrection:
    correction = str(correction or "").strip().lower()
    if correction not in {"too_high", "accurate", "too_low"}:
        raise ValueError("correction must be one of: accurate, too_high, too_low")

    profile = get_profile()
    change = LearningChange.objects.create(
        change_type="match_score_correction",
        summary=f"Match score marked {correction.replace('_', ' ')} for {job.title} at {job.company.name}.",
        evidence=[{"job_id": job.id, "title": job.title, "company": job.company.name}],
        payload={"job_id": job.id, "correction": correction, "reason": str(reason or "").strip()[:2000]},
    )
    score_correction = MatchScoreCorrection.objects.create(
        job=job,
        profile=profile,
        learning_change=change,
        correction=correction,
        reason=str(reason or "").strip()[:2000],
    )
    from matching.services import refresh_job_match

    refresh_job_match(job, profile=profile)
    return score_correction


def undo_learning_change(change: LearningChange) -> LearningChange:
    if change.status == "undone":
        return change
    change.status = "undone"
    change.undone_at = timezone.now()
    change.save(update_fields=["status", "undone_at"])
    if hasattr(change, "match_score_correction"):
        from matching.services import refresh_job_match

        refresh_job_match(change.match_score_correction.job, profile=change.match_score_correction.profile)
    return change


def generate_weekly_review() -> WeeklyReview:
    period_end = timezone.now()
    period_start = period_end - timedelta(days=7)
    overview = analytics_overview(limit=20)
    profile = get_profile()
    strategy = get_search_strategy(profile)
    applications = Application.objects.filter(updated_at__gte=period_start)
    matches = JobMatch.objects.select_related("job", "job__company").order_by("-overall_score")[:25]

    recommendations = weekly_recommendations(overview, strategy, applications, matches)
    risks = weekly_risks(overview, applications)
    summary = weekly_summary(overview, applications, recommendations, risks)
    return WeeklyReview.objects.create(
        period_start=period_start,
        period_end=period_end,
        summary=summary,
        recommendations=recommendations,
        risks=risks,
        metrics_snapshot={
            "summary": overview["summary"],
            "top_match_scores": [
                {
                    "job_id": match.job_id,
                    "title": match.job.title,
                    "company": match.job.company.name,
                    "score": match.overall_score,
                    "priority": match.apply_priority,
                }
                for match in matches[:10]
            ],
            "search_strategy": {
                "role_families": strategy.role_families,
                "target_title_keywords": strategy.target_title_keywords,
                "negative_keywords": strategy.negative_keywords,
            },
        },
    )


def weekly_recommendations(overview: dict, strategy, applications, matches) -> list[dict]:
    recommendations = []
    if overview["summary"]["suggestions_total"]:
        recommendations.append(
            {
                "kind": "review_filter_suggestions",
                "message": "Review analytics filter suggestions before the next scan cycle.",
                "count": overview["summary"]["suggestions_total"],
            }
        )
    if not strategy.target_title_keywords:
        recommendations.append(
            {
                "kind": "search_strategy",
                "message": "Generate or edit search strategy keywords so tracking has a clearer target.",
                "count": 0,
            }
        )
    apply_now = [match for match in matches if match.apply_priority == "apply_now"]
    if apply_now:
        recommendations.append(
            {
                "kind": "apply_now",
                "message": "Review top apply-now matches and move real opportunities into applications.",
                "count": len(apply_now),
            }
        )
    prep_gap_count = applications.filter(artifacts__isnull=True, status__in=["saved", "applying", "applied", "interviewing"]).distinct().count()
    if prep_gap_count:
        recommendations.append(
            {
                "kind": "application_prep",
                "message": "Generate prep artifacts for active applications without artifacts.",
                "count": prep_gap_count,
            }
        )
    return recommendations or [{"kind": "maintain", "message": "Keep current tracking cadence and review new roles.", "count": 0}]


def weekly_risks(overview: dict, applications) -> list[dict]:
    risks = []
    if overview["summary"]["sources_failing"]:
        risks.append({"kind": "failing_sources", "message": "Some sources are failing or blocked.", "count": overview["summary"]["sources_failing"]})
    if overview["summary"]["feedback_irrelevant"] > overview["summary"]["feedback_relevant"]:
        risks.append({"kind": "low_relevance", "message": "Irrelevant feedback exceeds relevant feedback.", "count": overview["summary"]["feedback_irrelevant"]})
    overdue = applications.filter(follow_up_at__lt=timezone.now(), status__in=["saved", "applying", "applied", "interviewing"]).count()
    if overdue:
        risks.append({"kind": "overdue_followups", "message": "Some application follow-ups need attention.", "count": overdue})
    return risks


def weekly_summary(overview: dict, applications, recommendations: list[dict], risks: list[dict]) -> str:
    summary = overview["summary"]
    return (
        f"{summary['companies_tracked']} companies tracked, {summary['alerts_total']} alerts, "
        f"{applications.count()} application updates this week. "
        f"{len(recommendations)} recommendations and {len(risks)} risks were generated for review."
    )


def company_quality(company: Company) -> dict:
    scan_jobs = list(company.scan_jobs.all())
    alerts = list(company.job_alerts.all())
    feedback = list(company.alert_feedback.all())
    applications_count = Application.objects.filter(job__company=company).count()
    successful_scans = sum(1 for scan in scan_jobs if scan.status in {"success", "partial_success"})
    failed_scans = sum(1 for scan in scan_jobs if scan.status == "failed")
    feedback_counts = feedback_distribution(feedback)
    feedback_total = sum(feedback_counts.values())
    usefulness_score = usefulness_from_feedback(feedback_counts)
    success_rate = round(successful_scans / len(scan_jobs), 3) if scan_jobs else None
    stale = is_stale(company)

    return {
        "company_id": company.id,
        "company_name": company.name,
        "careers_url": company.careers_url,
        "priority_tier": company.priority_tier,
        "source_platform": company.scraper_type,
        "source_health": company.source_health,
        "is_active": company.is_active,
        "last_successful_scan_at": company.last_successful_scan_at.isoformat() if company.last_successful_scan_at else None,
        "last_failed_scan_at": company.last_failed_scan_at.isoformat() if company.last_failed_scan_at else None,
        "last_new_role_at": company.last_new_role_at.isoformat() if company.last_new_role_at else None,
        "scan_frequency_hours": company.scan_frequency_hours,
        "scan_count": len(scan_jobs),
        "successful_scans": successful_scans,
        "failed_scans": failed_scans,
        "success_rate": success_rate,
        "jobs_total": company.jobs.count(),
        "alerts_total": len(alerts),
        "applications_total": applications_count,
        "feedback_total": feedback_total,
        "feedback_relevant": feedback_counts["relevant"],
        "feedback_maybe": feedback_counts["maybe"],
        "feedback_irrelevant": feedback_counts["irrelevant"],
        "usefulness_score": usefulness_score,
        "stale": stale,
        "noisy": is_noisy(feedback_counts, len(alerts), applications_count),
        "title_keywords": company.title_keywords,
        "negative_title_keywords": company.negative_title_keywords,
        "location_keywords": company.location_keywords,
        "work_mode_filter": company.work_mode_filter,
    }


def platform_quality(company_metrics: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for metric in company_metrics:
        grouped[metric["source_platform"] or "unknown"].append(metric)

    results = []
    for platform, metrics in sorted(grouped.items()):
        scan_count = sum(metric["scan_count"] for metric in metrics)
        successful_scans = sum(metric["successful_scans"] for metric in metrics)
        feedback_total = sum(metric["feedback_total"] for metric in metrics)
        weighted_usefulness = [
            metric["usefulness_score"] * metric["feedback_total"]
            for metric in metrics
            if metric["usefulness_score"] is not None and metric["feedback_total"]
        ]
        results.append(
            {
                "source_platform": platform,
                "companies_total": len(metrics),
                "active_companies": sum(1 for metric in metrics if metric["is_active"]),
                "scan_count": scan_count,
                "success_rate": round(successful_scans / scan_count, 3) if scan_count else None,
                "alerts_total": sum(metric["alerts_total"] for metric in metrics),
                "feedback_total": feedback_total,
                "usefulness_score": round(sum(weighted_usefulness) / feedback_total, 1)
                if feedback_total and weighted_usefulness
                else None,
                "failing_sources": sum(1 for metric in metrics if metric["source_health"] in {"failing", "blocked"}),
                "noisy_companies": sum(1 for metric in metrics if metric["noisy"]),
            }
        )
    return results


def build_filter_suggestions(company_metrics: list[dict]) -> list[dict]:
    suggestions = []
    for metric in company_metrics:
        evidence = []
        if metric["source_health"] in {"failing", "blocked"} or metric["failed_scans"] >= 3:
            evidence.append(f"{metric['failed_scans']} failed scans")
            suggestions.append(
                suggestion(
                    metric,
                    "source_health",
                    "Review source setup before trusting alerts.",
                    evidence,
                    "manual_review",
                )
            )

        if metric["stale"]:
            suggestions.append(
                suggestion(
                    metric,
                    "scan_cadence",
                    "Run a manual scan or revisit cadence because the source is stale.",
                    [f"Frequency: {metric['scan_frequency_hours']}h"],
                    "manual_scan",
                )
            )

        if metric["feedback_irrelevant"] >= 2:
            terms = noisy_terms_for_company(metric["company_id"], rating="irrelevant")
            evidence = [f"{metric['feedback_irrelevant']} irrelevant labels"]
            if terms:
                evidence.append(f"Recurring title terms: {', '.join(terms[:5])}")
            suggestions.append(
                suggestion(
                    metric,
                    "negative_keywords",
                    "Consider adding recurring irrelevant title terms as negative keywords.",
                    evidence,
                    "review_negative_keywords",
                    {"candidate_terms": terms},
                )
            )

        if metric["feedback_relevant"] >= 2 and not metric["title_keywords"]:
            terms = noisy_terms_for_company(metric["company_id"], rating="relevant")
            suggestions.append(
                suggestion(
                    metric,
                    "title_keywords",
                    "Consider promoting recurring relevant title terms into title filters.",
                    [f"{metric['feedback_relevant']} relevant labels"],
                    "review_title_keywords",
                    {"candidate_terms": terms},
                )
            )
    return suggestions


def build_noisy_signals(company_metrics: list[dict]) -> list[dict]:
    signals = []
    for metric in company_metrics:
        if metric["noisy"]:
            signals.append(
                {
                    "kind": "company_noise",
                    "company_id": metric["company_id"],
                    "company_name": metric["company_name"],
                    "message": "This company has more irrelevant feedback than useful outcomes.",
                    "evidence": {
                        "alerts_total": metric["alerts_total"],
                        "applications_total": metric["applications_total"],
                        "feedback_irrelevant": metric["feedback_irrelevant"],
                    },
                }
            )
        if metric["source_health"] in {"failing", "blocked"}:
            signals.append(
                {
                    "kind": "source_health",
                    "company_id": metric["company_id"],
                    "company_name": metric["company_name"],
                    "message": "Source health is blocking reliable tracking.",
                    "evidence": {
                        "source_health": metric["source_health"],
                        "failed_scans": metric["failed_scans"],
                    },
                }
            )
    return signals


def feedback_inbox(limit: int) -> list[dict]:
    alerts = (
        JobAlert.objects.select_related("company", "job")
        .filter(feedback__isnull=True)
        .order_by("-created_at")[:limit]
    )
    return [serialize_feedback_candidate(alert) for alert in alerts]


def recent_feedback(limit: int):
    return AlertFeedback.objects.select_related("alert", "company", "job").order_by("-updated_at")[:limit]


def serialize_feedback_candidate(alert: JobAlert) -> dict:
    return {
        "alert_id": alert.id,
        "job_id": alert.job_id,
        "company_id": alert.company_id,
        "company_name": alert.company.name,
        "job_title": alert.job.title,
        "location": alert.job.location,
        "remote_policy": alert.job.remote_policy,
        "status": alert.status,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "apply_url": alert.job.apply_url,
    }


def serialize_alert_feedback(feedback: AlertFeedback) -> dict:
    return {
        "id": feedback.id,
        "alert_id": feedback.alert_id,
        "job_id": feedback.job_id,
        "job_title": feedback.job.title,
        "company_id": feedback.company_id,
        "company_name": feedback.company.name,
        "rating": feedback.rating,
        "reason": feedback.reason,
        "tags": feedback.tags,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None,
    }


def serialize_weekly_review(review: WeeklyReview | None) -> dict | None:
    if not review:
        return None
    return {
        "id": review.id,
        "period_start": review.period_start.isoformat() if review.period_start else None,
        "period_end": review.period_end.isoformat() if review.period_end else None,
        "summary": review.summary,
        "recommendations": review.recommendations,
        "risks": review.risks,
        "metrics_snapshot": review.metrics_snapshot,
        "generated_by": review.generated_by,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def serialize_learning_change(change: LearningChange) -> dict:
    return {
        "id": change.id,
        "change_type": change.change_type,
        "status": change.status,
        "summary": change.summary,
        "evidence": change.evidence,
        "payload": change.payload,
        "created_at": change.created_at.isoformat() if change.created_at else None,
        "undone_at": change.undone_at.isoformat() if change.undone_at else None,
    }


def serialize_match_score_correction(correction: MatchScoreCorrection) -> dict:
    return {
        "id": correction.id,
        "job_id": correction.job_id,
        "job_title": correction.job.title,
        "company_id": correction.job.company_id,
        "company_name": correction.job.company.name,
        "profile_id": correction.profile_id,
        "learning_change_id": correction.learning_change_id,
        "learning_change_status": correction.learning_change.status,
        "correction": correction.correction,
        "reason": correction.reason,
        "created_at": correction.created_at.isoformat() if correction.created_at else None,
    }


def normalize_tags(tags) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        raw_tags = tags.replace("\n", ",").split(",")
    elif isinstance(tags, list):
        raw_tags = tags
    else:
        raw_tags = []
    return [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()][:20]


def feedback_distribution(feedback_items) -> dict[str, int]:
    counter = Counter()
    for feedback in feedback_items:
        counter[feedback.rating] += 1
    return {rating: counter.get(rating, 0) for rating in sorted(RATINGS)}


def usefulness_from_feedback(feedback_counts: dict[str, int]) -> float | None:
    total = sum(feedback_counts.values())
    if not total:
        return None
    score = feedback_counts["relevant"] * 100 + feedback_counts["maybe"] * 50
    return round(score / total, 1)


def is_stale(company: Company) -> bool:
    if not company.is_active or not company.last_successful_scan_at:
        return False
    stale_after = timedelta(hours=max(company.scan_frequency_hours * 2, 24))
    return company.last_successful_scan_at < timezone.now() - stale_after


def is_noisy(feedback_counts: dict[str, int], alerts_count: int, applications_count: int) -> bool:
    feedback_total = sum(feedback_counts.values())
    if feedback_total >= 2 and feedback_counts["irrelevant"] / feedback_total >= 0.5:
        return True
    return alerts_count >= 5 and applications_count == 0


def noisy_terms_for_company(company_id: int, rating: str) -> list[str]:
    titles = AlertFeedback.objects.filter(company_id=company_id, rating=rating).values_list("job__title", flat=True)
    stopwords = {
        "and",
        "the",
        "for",
        "with",
        "engineer",
        "developer",
        "software",
        "senior",
        "staff",
        "lead",
        "role",
    }
    counter = Counter()
    for title in titles:
        words = [word.strip(".,:/()[]{}").lower() for word in title.split()]
        counter.update(word for word in words if len(word) >= 3 and word not in stopwords)
    return [word for word, _ in counter.most_common(8)]


def suggestion(metric: dict, suggestion_type: str, message: str, evidence: list[str], action: str, payload=None) -> dict:
    return {
        "company_id": metric["company_id"],
        "company_name": metric["company_name"],
        "suggestion_type": suggestion_type,
        "message": message,
        "evidence": evidence,
        "action": action,
        "payload": payload or {},
        "requires_review": True,
    }
