from django.contrib import admin

from .models import Company, JobAlert, ScanJob, ScrapeLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "priority_tier",
        "scraper_type",
        "is_active",
        "source_health",
        "work_mode_filter",
        "scan_frequency_hours",
        "alert_new_roles",
        "last_scraped_at",
        "last_scrape_status",
        "consecutive_failure_count",
    )
    search_fields = ("name", "careers_url")
    list_filter = (
        "priority_tier",
        "scraper_type",
        "is_active",
        "source_health",
        "work_mode_filter",
        "alert_new_roles",
        "last_scrape_status",
    )


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ("company", "status", "jobs_found", "jobs_created", "started_at", "finished_at")
    list_filter = ("status", "source_platform")
    search_fields = ("company__name", "message")


@admin.register(ScanJob)
class ScanJobAdmin(admin.ModelAdmin):
    list_display = ("company", "status", "trigger", "jobs_found", "jobs_created", "alerts_created", "requested_at", "finished_at")
    list_filter = ("status", "trigger", "source_platform")
    search_fields = ("company__name", "message")


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "status", "alert_type", "created_at")
    list_filter = ("status", "alert_type")
    search_fields = ("title", "company__name", "job__title")
