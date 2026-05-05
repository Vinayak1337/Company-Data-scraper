from django.contrib import admin

from .models import (
    AgentArtifact,
    AgentAuditLog,
    AgentDecision,
    AgentPermission,
    AgentProviderSetting,
    AgentRun,
    AgentStep,
    RuntimeInvocation,
)


@admin.register(AgentProviderSetting)
class AgentProviderSettingAdmin(admin.ModelAdmin):
    list_display = ("provider", "enabled", "worker_only", "model_name", "default_tool_policy", "updated_at")
    list_filter = ("enabled", "worker_only", "default_tool_policy")
    search_fields = ("provider", "label", "model_name", "notes")


class AgentStepInline(admin.TabularInline):
    model = AgentStep
    extra = 0


class AgentArtifactInline(admin.TabularInline):
    model = AgentArtifact
    extra = 0


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("agent_type", "status", "provider", "model_name", "tool_policy", "requested_at", "finished_at")
    list_filter = ("agent_type", "status", "provider", "tool_policy")
    search_fields = ("result_summary", "error", "user_safe_error")
    inlines = [AgentStepInline, AgentArtifactInline]


@admin.register(AgentDecision)
class AgentDecisionAdmin(admin.ModelAdmin):
    list_display = ("run", "decision_type", "status", "created_at", "decided_at")
    list_filter = ("decision_type", "status")


@admin.register(AgentPermission)
class AgentPermissionAdmin(admin.ModelAdmin):
    list_display = ("run", "policy_level", "status", "created_at")
    list_filter = ("policy_level", "status")


@admin.register(RuntimeInvocation)
class RuntimeInvocationAdmin(admin.ModelAdmin):
    list_display = ("run", "provider", "adapter", "model_name", "status", "started_at", "finished_at")
    list_filter = ("provider", "adapter", "status")


@admin.register(AgentAuditLog)
class AgentAuditLogAdmin(admin.ModelAdmin):
    list_display = ("run", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("message",)
