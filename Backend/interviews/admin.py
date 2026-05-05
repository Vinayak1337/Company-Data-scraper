from django.contrib import admin

from interviews.models import InterviewPrep, OfferSupport


@admin.register(InterviewPrep)
class InterviewPrepAdmin(admin.ModelAdmin):
    list_display = ("application", "stage", "generated_by", "updated_at")
    list_filter = ("stage", "generated_by")
    search_fields = ("application__job__title", "application__job__company__name", "notes")


@admin.register(OfferSupport)
class OfferSupportAdmin(admin.ModelAdmin):
    list_display = ("application", "offer_stage", "generated_by", "updated_at")
    list_filter = ("offer_stage", "generated_by")
    search_fields = ("application__job__title", "application__job__company__name", "compensation_notes")
