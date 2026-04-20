from django.contrib import admin

from .models import Company, ScrapeLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "scraper_type", "is_active", "last_scraped_at", "last_scrape_status")
    search_fields = ("name", "careers_url")
    list_filter = ("scraper_type", "is_active", "last_scrape_status")


@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = ("company", "status", "jobs_found", "jobs_created", "started_at", "finished_at")
    list_filter = ("status", "source_platform")
    search_fields = ("company__name", "message")
