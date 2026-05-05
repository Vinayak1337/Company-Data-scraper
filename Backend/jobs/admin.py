from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "source_platform", "posted_at", "last_seen_at")
    search_fields = ("title", "company__name", "location", "description", "tags")
    list_filter = ("source_platform", "remote_policy")
