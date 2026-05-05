from django.contrib import admin

from .models import CandidateProfile, ProfileClaim, TargetTitle, UserSearchPreference


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "headline", "location", "remote_preference", "updated_at")
    search_fields = ("full_name", "headline", "location", "summary", "skills")


@admin.register(TargetTitle)
class TargetTitleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "fit_bucket", "confidence_score", "knowledge_accuracy", "updated_at")
    list_filter = ("status", "fit_bucket", "source")
    search_fields = ("title", "evidence")


@admin.register(ProfileClaim)
class ProfileClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_type", "status", "source", "updated_at")
    list_filter = ("claim_type", "status", "source")
    search_fields = ("text", "evidence")


@admin.register(UserSearchPreference)
class UserSearchPreferenceAdmin(admin.ModelAdmin):
    list_display = ("profile", "minimum_match_score", "minimum_confidence_score", "match_strictness", "updated_at")
    list_filter = ("match_strictness",)
