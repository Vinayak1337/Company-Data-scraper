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
        ("weighted", "Weighted feature scorer"),
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
    notification_threshold = models.PositiveIntegerField(default=70)
    should_notify = models.BooleanField(default=False)
    feature_snapshot = models.JSONField(default=dict, blank=True)
    agent_summary = models.TextField(blank=True)
    agent_review_status = models.CharField(max_length=40, default="not_requested")
    model_version = models.CharField(max_length=80, default="weighted-v1")
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
            models.Index(fields=["should_notify", "-overall_score"]),
        ]

    def __str__(self) -> str:
        return f"{self.job_id}: {self.overall_score}"


class MatchFeedback(models.Model):
    FEEDBACK_CHOICES = [
        ("good_match", "Good match"),
        ("bad_match", "Bad match"),
        ("too_senior", "Too senior"),
        ("too_junior", "Too junior"),
        ("wrong_location", "Wrong location"),
        ("wrong_role", "Wrong role"),
        ("missing_skill", "Missing skill"),
        ("not_interested_company", "Not interested company"),
        ("too_many_notifications", "Too many notifications"),
        ("want_more_matches", "Want more matches"),
    ]

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="match_feedback")
    match = models.ForeignKey(JobMatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback")
    profile = models.ForeignKey(
        "profiles.CandidateProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_feedback",
    )
    feedback_type = models.CharField(max_length=40, choices=FEEDBACK_CHOICES)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["feedback_type", "created_at"]),
            models.Index(fields=["job", "feedback_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.feedback_type} for {self.job_id}"
