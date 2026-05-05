from django.db import models
from django.utils import timezone


class AgentProviderSetting(models.Model):
    PROVIDER_CHOICES = [
        ("direct_api", "Direct API"),
        ("openrouter", "OpenRouter"),
        ("deepseek", "DeepSeek"),
        ("gemini_cli", "Gemini CLI"),
        ("claude_code_cli", "Claude Code CLI"),
        ("opencode", "OpenCode"),
    ]

    TOOL_POLICY_CHOICES = [
        ("read_only", "Read only"),
        ("workspace_write", "Workspace write"),
        ("safe_shell", "Safe shell"),
        ("network_tools", "Network tools"),
        ("external_action", "External action"),
    ]

    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES, unique=True)
    label = models.CharField(max_length=80)
    model_name = models.CharField(max_length=120, blank=True)
    enabled = models.BooleanField(default=False)
    worker_only = models.BooleanField(default=False)
    api_key_env_var = models.CharField(max_length=80, blank=True)
    default_tool_policy = models.CharField(max_length=40, choices=TOOL_POLICY_CHOICES, default="read_only")
    consent_required = models.BooleanField(default=False)
    daily_run_limit = models.PositiveIntegerField(default=25)
    monthly_budget_cents = models.PositiveIntegerField(default=0)
    estimated_cost_per_run_cents = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider"]

    def __str__(self) -> str:
        return self.label


class AgentRun(models.Model):
    AGENT_TYPE_CHOICES = [
        ("profile_builder", "Profile Builder"),
        ("source_discovery", "Source Discovery"),
        ("match_review", "Match Review"),
        ("search_strategy", "Search Strategy"),
        ("notification_review", "Notification Review"),
    ]

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("waiting_approval", "Waiting approval"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    RUNTIME_CHOICES = AgentProviderSetting.PROVIDER_CHOICES
    TOOL_POLICY_CHOICES = AgentProviderSetting.TOOL_POLICY_CHOICES

    agent_type = models.CharField(max_length=40, choices=AGENT_TYPE_CHOICES)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="queued")
    provider = models.CharField(max_length=40, choices=RUNTIME_CHOICES, default="direct_api")
    model_name = models.CharField(max_length=120, blank=True)
    tool_policy = models.CharField(max_length=40, choices=TOOL_POLICY_CHOICES, default="read_only")
    prompt_version = models.CharField(max_length=80, default="local-profile-builder-v1")
    input_snapshot = models.JSONField(default=dict, blank=True)
    output_snapshot = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True)
    error = models.TextField(blank=True)
    user_safe_error = models.TextField(blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at", "-created_at"]
        indexes = [
            models.Index(fields=["agent_type", "status"]),
            models.Index(fields=["provider", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.agent_type} {self.status}"


class AgentStep(models.Model):
    STATUS_CHOICES = AgentRun.STATUS_CHOICES

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=160)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="queued")
    message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name


class AgentArtifact(models.Model):
    ARTIFACT_TYPE_CHOICES = [
        ("markdown", "Markdown"),
        ("json", "JSON"),
        ("text", "Text"),
        ("proposal", "Proposal"),
    ]

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=40, choices=ARTIFACT_TYPE_CHOICES, default="markdown")
    title = models.CharField(max_length=180)
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.title


class AgentDecision(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="decisions")
    decision_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    question = models.TextField()
    proposed_changes = models.JSONField(default=dict, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.decision_type


class AgentPermission(models.Model):
    STATUS_CHOICES = [
        ("granted", "Granted"),
        ("denied", "Denied"),
        ("blocked", "Blocked"),
    ]

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="permissions")
    policy_level = models.CharField(max_length=40, choices=AgentProviderSetting.TOOL_POLICY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="granted")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.policy_level}: {self.status}"


class RuntimeInvocation(models.Model):
    STATUS_CHOICES = [
        ("prepared", "Prepared"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="runtime_invocations")
    provider = models.CharField(max_length=40)
    adapter = models.CharField(max_length=80)
    model_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="prepared")
    input_snapshot = models.JSONField(default=dict, blank=True)
    output_snapshot = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    token_count = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.provider} {self.status}"


class AgentAuditLog(models.Model):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="audit_logs")
    event_type = models.CharField(max_length=80)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.event_type
