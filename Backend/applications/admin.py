from django.contrib import admin

from .models import Application, TodayAction


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "status", "follow_up_at", "applied_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("job__title", "job__company__name", "notes", "next_action")


@admin.register(TodayAction)
class TodayActionAdmin(admin.ModelAdmin):
    list_display = ("title", "action_type", "status", "due_at", "created_at")
    list_filter = ("action_type", "status")
    search_fields = ("title", "message", "job__title", "job__company__name")
