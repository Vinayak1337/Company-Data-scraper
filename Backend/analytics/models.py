from django.db import models


class AlertFeedback(models.Model):
    RATING_CHOICES = [
        ("relevant", "Relevant"),
        ("maybe", "Maybe"),
        ("irrelevant", "Irrelevant"),
    ]

    alert = models.OneToOneField(
        "companies.JobAlert",
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="alert_feedback")
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="alert_feedback")
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    reason = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["rating", "updated_at"]),
            models.Index(fields=["company", "rating"]),
        ]

    def __str__(self) -> str:
        return f"{self.alert_id}: {self.rating}"


class WeeklyReview(models.Model):
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    summary = models.TextField(blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    metrics_snapshot = models.JSONField(default=dict, blank=True)
    generated_by = models.CharField(max_length=80, default="deterministic")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end", "-created_at"]

    def __str__(self) -> str:
        return f"Weekly review ending {self.period_end:%Y-%m-%d}"


class LearningChange(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("undone", "Undone"),
    ]

    change_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    summary = models.TextField(blank=True)
    evidence = models.JSONField(default=list, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    undone_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["change_type", "status"]),
        ]

    def __str__(self) -> str:
        return self.summary[:120] or self.change_type


class MatchScoreCorrection(models.Model):
    CORRECTION_CHOICES = [
        ("too_high", "Score too high"),
        ("accurate", "Accurate"),
        ("too_low", "Score too low"),
    ]

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="score_corrections")
    profile = models.ForeignKey(
        "profiles.CandidateProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_score_corrections",
    )
    learning_change = models.OneToOneField(
        LearningChange,
        on_delete=models.CASCADE,
        related_name="match_score_correction",
    )
    correction = models.CharField(max_length=20, choices=CORRECTION_CHOICES)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "created_at"]),
            models.Index(fields=["correction", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.job_id}: {self.correction}"
