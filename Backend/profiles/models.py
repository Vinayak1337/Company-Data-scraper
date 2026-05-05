from django.db import models


class CandidateProfile(models.Model):
    REMOTE_CHOICES = [
        ("any", "Any"),
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("onsite", "Onsite"),
    ]

    full_name = models.CharField(max_length=180, blank=True)
    headline = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=180, blank=True)
    remote_preference = models.CharField(max_length=20, choices=REMOTE_CHOICES, default="any")
    target_locations = models.JSONField(default=list, blank=True)
    preferred_work_modes = models.JSONField(default=list, blank=True)
    links = models.JSONField(default=dict, blank=True)
    skills = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    dealbreakers = models.TextField(blank=True)
    compensation_expectation = models.CharField(max_length=180, blank=True)
    cv_markdown = models.TextField(blank=True)
    profile_markdown = models.TextField(blank=True)
    profile_yml = models.TextField(blank=True)
    proof_points = models.JSONField(default=list, blank=True)
    skill_inventory = models.JSONField(default=list, blank=True)
    career_timeline = models.JSONField(default=list, blank=True)
    role_framing = models.TextField(blank=True)
    profile_completeness_score = models.PositiveIntegerField(default=0)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "candidate profile"
        verbose_name_plural = "candidate profiles"

    def __str__(self) -> str:
        return self.full_name or "Candidate profile"


class TargetTitle(models.Model):
    STATUS_CHOICES = [
        ("suggested", "Suggested"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    FIT_CHOICES = [
        ("core", "Core"),
        ("adjacent", "Adjacent"),
        ("stretch", "Stretch"),
    ]

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="target_titles")
    title = models.CharField(max_length=180)
    fit_bucket = models.CharField(max_length=20, choices=FIT_CHOICES, default="adjacent")
    confidence_score = models.PositiveIntegerField(default=50)
    knowledge_accuracy = models.PositiveIntegerField(default=50)
    evidence = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=40, default="deterministic")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="suggested")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-confidence_score", "title"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "title"], name="unique_target_title_per_profile"),
        ]

    def __str__(self) -> str:
        return self.title


class ProfileClaim(models.Model):
    STATUS_CHOICES = [
        ("unconfirmed", "Unconfirmed"),
        ("confirmed", "Confirmed"),
        ("needs_edit", "Needs edit"),
        ("rejected", "Rejected"),
    ]

    CLAIM_TYPE_CHOICES = [
        ("skill", "Skill"),
        ("experience", "Experience"),
        ("project", "Project"),
        ("metric", "Metric"),
        ("education", "Education"),
        ("other", "Other"),
    ]

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="claims")
    claim_type = models.CharField(max_length=40, choices=CLAIM_TYPE_CHOICES, default="other")
    text = models.TextField()
    evidence = models.TextField(blank=True)
    source = models.CharField(max_length=40, default="resume_import")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unconfirmed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "claim_type", "id"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "text"], name="unique_profile_claim_text"),
        ]

    def __str__(self) -> str:
        return self.text[:120]


class SearchStrategy(models.Model):
    profile = models.OneToOneField(CandidateProfile, on_delete=models.CASCADE, related_name="search_strategy")
    role_families = models.JSONField(default=list, blank=True)
    target_title_keywords = models.JSONField(default=list, blank=True)
    negative_keywords = models.JSONField(default=list, blank=True)
    seniority_levels = models.JSONField(default=list, blank=True)
    location_keywords = models.JSONField(default=list, blank=True)
    work_mode_preferences = models.JSONField(default=list, blank=True)
    generated_from = models.CharField(max_length=80, default="deterministic_profile")
    notes = models.TextField(blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "search strategy"
        verbose_name_plural = "search strategies"

    def __str__(self) -> str:
        return f"Search strategy for {self.profile}"
