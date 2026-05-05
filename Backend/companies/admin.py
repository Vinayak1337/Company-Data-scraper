from django.contrib import admin

from .models import Company, CompanyJobSource, JobAlert, ScanJob, ScrapeLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "domain",
        "priority_tier",
        "scraper_type",
        "is_active",
        "source_health",
        "source_discovery_status",
        "work_mode_filter",
        "scan_frequency_hours",
        "alert_new_roles",
        "last_scraped_at",
        "last_scrape_status",
        "consecutive_failure_count",
    )
    search_fields = ("name", "domain", "homepage_url", "careers_url")
    list_filter = (
        "priority_tier",
        "scraper_type",
        "is_active",
        "source_health",
        "source_discovery_status",
        "work_mode_filter",
        "alert_new_roles",
        "last_scrape_status",
    )


@admin.register(CompanyJobSource)
class CompanyJobSourceAdmin(admin.ModelAdmin):
    list_display = ("company", "platform", "status", "confidence_score", "is_primary", "discovery_method", "updated_at")
    list_filter = ("platform", "status", "is_primary", "discovery_method")
    search_fields = ("company__name", "url", "notes")


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ("company", "source", "status", "jobs_found", "jobs_created", "started_at", "finished_at")
    list_filter = ("status", "source_platform")
    search_fields = ("company__name", "message")


@admin.register(ScanJob)
class ScanJobAdmin(admin.ModelAdmin):
    list_display = ("company", "source", "status", "trigger", "jobs_found", "jobs_created", "alerts_created", "requested_at", "finished_at")
    list_filter = ("status", "trigger", "source_platform")
    search_fields = ("company__name", "message")


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "status", "alert_type", "created_at")
    list_filter = ("status", "alert_type")
    search_fields = ("title", "company__name", "job__title")
