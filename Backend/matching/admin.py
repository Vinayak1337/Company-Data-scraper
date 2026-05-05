from django.contrib import admin

from .models import JobMatch, MatchFeedback


@admin.register(JobMatch)
class JobMatchAdmin(admin.ModelAdmin):
    list_display = ("job", "profile", "overall_score", "confidence_score", "notification_threshold", "should_notify", "apply_priority", "generated_at")
    list_filter = ("apply_priority", "source", "should_notify", "agent_review_status")
    search_fields = ("job__title", "job__company__name")


@admin.register(MatchFeedback)
class MatchFeedbackAdmin(admin.ModelAdmin):
    list_display = ("feedback_type", "job", "profile", "created_at")
    list_filter = ("feedback_type",)
    search_fields = ("job__title", "job__company__name", "notes")
