from django.db import models
from django.utils import timezone


class JobMatch(models.Model):
    APPLY_PRIORITY_CHOICES = [
        ("apply_now", "Apply now"),
        ("consider", "Consider"),
        ("stretch", "Stretch"),
        ("ignore", "Ignore"),
    ]

    SOURCE_CHOICES = [
        ("deterministic", "Deterministic"),
        ("agent", "Agent"),
    ]

    job = models.OneToOneField("jobs.Job", on_delete=models.CASCADE, related_name="match_report")
    profile = models.ForeignKey(
        "profiles.CandidateProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_matches",
    )
    source = models.CharField(max_length=40, choices=SOURCE_CHOICES, default="deterministic")
    profile_updated_at = models.DateTimeField(null=True, blank=True)
    overall_score = models.PositiveIntegerField(default=0)
    title_score = models.PositiveIntegerField(default=0)
    skill_score = models.PositiveIntegerField(default=0)
    seniority_score = models.PositiveIntegerField(default=0)
    location_score = models.PositiveIntegerField(default=0)
    confidence_score = models.PositiveIntegerField(default=0)
    knowledge_coverage_score = models.PositiveIntegerField(default=0)
    apply_priority = models.CharField(max_length=20, choices=APPLY_PRIORITY_CHOICES, default="ignore")
    reasons_to_apply = models.JSONField(default=list, blank=True)
    reasons_to_skip = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-overall_score", "-confidence_score", "-generated_at"]
        indexes = [
            models.Index(fields=["apply_priority", "-overall_score"]),
            models.Index(fields=["overall_score", "confidence_score"]),
        ]

    def __str__(self) -> str:
        return f"{self.job_id}: {self.overall_score}"
