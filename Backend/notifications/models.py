from datetime import time

from django.db import models


class NotificationPreference(models.Model):
    DIGEST_FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekdays", "Weekdays"),
        ("weekly", "Weekly"),
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def __str__(self) -> str:
        return "Notification preferences"
