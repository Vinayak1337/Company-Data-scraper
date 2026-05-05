from datetime import time

from django.db import models


class NotificationPreference(models.Model):
    DIGEST_FREQUENCY_CHOICES = [
        ("immediate", "Immediate"),
        ("daily", "Daily"),
        ("weekdays", "Weekdays"),
        ("weekly", "Weekly"),
        ("disabled", "Disabled"),
    ]

    DIGEST_CHANNEL_CHOICES = [
        ("local", "Local"),
        ("email", "Email"),
    ]

    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default=time(22, 0))
    quiet_hours_end = models.TimeField(default=time(8, 0))
    timezone = models.CharField(max_length=80, default="UTC")
    digest_enabled = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=20, choices=DIGEST_FREQUENCY_CHOICES, default="daily")
    digest_time = models.TimeField(default=time(9, 0))
    digest_channel = models.CharField(max_length=20, choices=DIGEST_CHANNEL_CHOICES, default="local")
    email_address = models.EmailField(blank=True)
    immediate_email_enabled = models.BooleanField(default=False)
    minimum_match_score = models.PositiveIntegerField(default=75)
    minimum_confidence_score = models.PositiveIntegerField(default=55)
    max_digest_items = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def __str__(self) -> str:
        return "Notification preferences"


class NotificationEvent(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("skipped", "Skipped"),
        ("failed", "Failed"),
    ]

    CHANNEL_CHOICES = [
        ("local", "Local"),
        ("email", "Email"),
    ]

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="notification_events")
    match = models.ForeignKey("matching.JobMatch", on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_events")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    score_at_send = models.PositiveIntegerField(default=0)
    confidence_at_send = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(max_length=160, unique=True)
    skipped_reason = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["job", "channel"]),
        ]

    def __str__(self) -> str:
        return self.subject
