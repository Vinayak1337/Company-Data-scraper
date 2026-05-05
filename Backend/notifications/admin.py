from django.contrib import admin

from .models import NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "timezone",
        "digest_enabled",
        "digest_frequency",
        "digest_channel",
        "updated_at",
    )
