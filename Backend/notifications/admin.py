from django.contrib import admin

from .models import NotificationEvent, NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "email_address",
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "timezone",
        "digest_enabled",
        "digest_frequency",
        "digest_channel",
        "minimum_match_score",
        "minimum_confidence_score",
        "updated_at",
    )
    list_filter = ("digest_enabled", "digest_frequency", "digest_channel", "quiet_hours_enabled", "immediate_email_enabled")


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("subject", "channel", "status", "score_at_send", "confidence_at_send", "created_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("subject", "body", "job__title", "job__company__name")
