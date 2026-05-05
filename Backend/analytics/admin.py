from django.contrib import admin

from .models import AlertFeedback, LearningChange, MatchScoreCorrection, WeeklyReview


@admin.register(AlertFeedback)
class AlertFeedbackAdmin(admin.ModelAdmin):
    list_display = ("alert", "company", "job", "rating", "updated_at")
    list_filter = ("rating", "company")
    search_fields = ("job__title", "company__name", "reason")


@admin.register(WeeklyReview)
class WeeklyReviewAdmin(admin.ModelAdmin):
    list_display = ("period_start", "period_end", "generated_by", "created_at")
    search_fields = ("summary",)


@admin.register(LearningChange)
class LearningChangeAdmin(admin.ModelAdmin):
    list_display = ("change_type", "status", "created_at", "undone_at")
    list_filter = ("change_type", "status")
    search_fields = ("summary",)


@admin.register(MatchScoreCorrection)
class MatchScoreCorrectionAdmin(admin.ModelAdmin):
    list_display = ("job", "profile", "correction", "created_at")
    list_filter = ("correction",)
    search_fields = ("job__title", "job__company__name", "reason")
