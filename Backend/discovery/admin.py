from django.contrib import admin

from discovery.models import ManualUrlInboxItem


@admin.register(ManualUrlInboxItem)
class ManualUrlInboxItemAdmin(admin.ModelAdmin):
    list_display = ("title", "item_type", "status", "inferred_company", "created_at")
    list_filter = ("item_type", "status")
    search_fields = ("url", "title", "inferred_company", "notes")
