from django.db import models
from django.utils import timezone


class Job(models.Model):
    REMOTE_CHOICES = [
        ("unknown", "Unknown"),
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("onsite", "Onsite"),
    ]

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    apply_url = models.URLField(max_length=1000)
    source_url = models.URLField(max_length=1000)
    source_platform = models.CharField(max_length=40)
    external_id = models.CharField(max_length=255, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    remote_policy = models.CharField(max_length=20, choices=REMOTE_CHOICES, default="unknown")
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-posted_at", "-first_seen_at", "title"]
        constraints = [
            models.UniqueConstraint(fields=["company", "apply_url"], name="unique_job_apply_url_per_company"),
        ]

    def __str__(self) -> str:
        return f"{self.title} at {self.company.name}"
