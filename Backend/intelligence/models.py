from django.db import models


class CompanyIntelligence(models.Model):
    LEGITIMACY_CHOICES = [
        ("unknown", "Unknown"),
        ("likely_legitimate", "Likely legitimate"),
        ("needs_review", "Needs review"),
        ("high_risk", "High risk"),
    ]

    VERIFICATION_CHOICES = [
        ("unverified", "Unverified"),
        ("deterministic", "Deterministic"),
        ("user_verified", "User verified"),
    ]

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="intelligence_reports")
    summary = models.TextField(blank=True)
    research_notes = models.TextField(blank=True)
    hiring_signals = models.JSONField(default=list, blank=True)
    role_patterns = models.JSONField(default=list, blank=True)
    role_legitimacy = models.CharField(max_length=40, choices=LEGITIMACY_CHOICES, default="unknown")
    caveats = models.JSONField(default=list, blank=True)
    hiring_team_hints = models.JSONField(default=list, blank=True)
    interview_process_notes = models.TextField(blank=True)
    risk_flags = models.JSONField(default=list, blank=True)
    user_notes = models.TextField(blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)
    verification_status = models.CharField(max_length=40, choices=VERIFICATION_CHOICES, default="unverified")
    generated_by = models.CharField(max_length=80, default="deterministic")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "created_at"])]

    def __str__(self) -> str:
        return f"{self.company.name} intelligence"


class RecruiterContact(models.Model):
    STATUS_CHOICES = [
        ("lead", "Lead"),
        ("contacted", "Contacted"),
        ("responded", "Responded"),
        ("not_relevant", "Not relevant"),
    ]

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="recruiter_contacts")
    name = models.CharField(max_length=180, blank=True)
    title = models.CharField(max_length=180, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    source_label = models.CharField(max_length=180, blank=True)
    public_source_only = models.BooleanField(default=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="lead")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company", "name", "id"]

    def __str__(self) -> str:
        return self.name or f"{self.company.name} contact"
