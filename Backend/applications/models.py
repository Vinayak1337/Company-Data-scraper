from django.db import models
from django.utils import timezone


class Application(models.Model):
    STATUS_CHOICES = [
        ("saved", "Saved"),
        ("applying", "Applying"),
        ("applied", "Applied"),
        ("interviewing", "Interviewing"),
        ("offer", "Offer"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("skipped", "Skipped"),
    ]

    job = models.OneToOneField("jobs.Job", on_delete=models.CASCADE, related_name="application")
    source_alert = models.ForeignKey(
        "companies.JobAlert",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="saved")
    notes = models.TextField(blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["follow_up_at", "-updated_at"]
        indexes = [
            models.Index(fields=["status", "follow_up_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.job.title} ({self.status})"


class ApplicationArtifact(models.Model):
    ARTIFACT_TYPE_CHOICES = [
        ("tailoring_plan", "Tailoring plan"),
        ("cv_notes", "CV notes"),
        ("cover_note", "Cover note"),
        ("recruiter_message", "Recruiter message"),
        ("answer_bank", "Answer bank"),
        ("interview_seed", "Interview seed"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=40, choices=ARTIFACT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    metadata = models.JSONField(default=dict, blank=True)
    generated_by = models.CharField(max_length=80, default="deterministic")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["application", "artifact_type", "-created_at"]
        indexes = [
            models.Index(fields=["application", "artifact_type", "status"]),
        ]

    def __str__(self) -> str:
        return self.title


class TodayAction(models.Model):
    ACTION_TYPE_CHOICES = [
        ("review_new_role", "Review new role"),
        ("follow_up", "Follow up"),
        ("application_next_step", "Application next step"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("done", "Done"),
        ("dismissed", "Dismissed"),
    ]

    action_type = models.CharField(max_length=40, choices=ACTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, null=True, blank=True, related_name="today_actions")
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="today_actions",
    )
    source_alert = models.ForeignKey(
        "companies.JobAlert",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="today_actions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["source_alert", "action_type"], name="unique_today_action_per_alert_type"),
            models.UniqueConstraint(fields=["application", "action_type"], name="unique_today_action_per_application_type"),
        ]
        indexes = [
            models.Index(fields=["status", "due_at"]),
            models.Index(fields=["action_type", "status"]),
        ]

    def __str__(self) -> str:
        return self.title

    def mark_done(self) -> None:
        self.status = "done"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def dismiss(self) -> None:
        self.status = "dismissed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])
