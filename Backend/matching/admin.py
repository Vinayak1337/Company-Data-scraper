from django.contrib import admin

from .models import JobMatch


@admin.register(JobMatch)
class JobMatchAdmin(admin.ModelAdmin):
    list_display = ("job", "profile", "overall_score", "confidence_score", "apply_priority", "generated_at")
    list_filter = ("apply_priority", "source")
    search_fields = ("job__title", "job__company__name")
