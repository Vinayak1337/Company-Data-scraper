from django.contrib import admin

from intelligence.models import CompanyIntelligence, RecruiterContact


@admin.register(CompanyIntelligence)
class CompanyIntelligenceAdmin(admin.ModelAdmin):
    list_display = ("company", "role_legitimacy", "verification_status", "generated_by", "created_at")
    list_filter = ("role_legitimacy", "verification_status", "generated_by")
    search_fields = ("company__name", "summary", "research_notes", "user_notes")


@admin.register(RecruiterContact)
class RecruiterContactAdmin(admin.ModelAdmin):
    list_display = ("company", "name", "title", "status", "public_source_only")
    list_filter = ("status", "public_source_only")
    search_fields = ("company__name", "name", "title", "source_label", "notes")
